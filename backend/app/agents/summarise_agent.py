import os
import litellm
import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy import select
from .state import DocIntelState
from backend.app.models.document import Chunk, Document
from backend.app.db.session import async_session

# Point to LiteLLM Proxy if available
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://litellm:4000")

logger = logging.getLogger(__name__)

async def summarise_node(state: DocIntelState) -> DocIntelState:
    """
    Performs document summarization using Gemini 1.5 Pro.
    Supports combined summary ('summarise') and individual summaries ('summarise_each').
    """
    intent = state.get("intent", "summarise")
    doc_ids = state.get("documents", [])
    
    logger.info(f"Summarization node processing intent: {intent} for documents: {doc_ids}")
    
    if not doc_ids:
        return {"draft_response": "No documents provided for summarization."}
    
    try:
        # Fetch content for the documents in batch
        all_docs_content = []
        async with async_session() as session:
            # Batch fetch document metadata
            doc_meta_stmt = select(Document).where(Document.id.in_(doc_ids))
            doc_meta_result = await session.execute(doc_meta_stmt)
            doc_metas = {doc.id: doc for doc in doc_meta_result.scalars().all()}
            
            # Batch fetch all chunks for all documents
            chunk_stmt = select(Chunk).where(Chunk.document_id.in_(doc_ids)).order_by(Chunk.document_id, Chunk.page_number, Chunk.id)
            chunk_result = await session.execute(chunk_stmt)
            all_chunks = chunk_result.scalars().all()
            
            # Group chunks by document_id
            doc_chunks = {}
            for chunk in all_chunks:
                if chunk.document_id not in doc_chunks:
                    doc_chunks[chunk.document_id] = []
                doc_chunks[chunk.document_id].append(chunk.content)
            
            for doc_id in doc_ids:
                filename = doc_metas[doc_id].filename if doc_id in doc_metas else str(doc_id)
                content = "\n".join(doc_chunks.get(doc_id, []))
                all_docs_content.append({"id": doc_id, "filename": filename, "content": content})
        
        # Populate retrieved_chunks for validation (take a sample to avoid overloading)
        retrieved_chunks = []
        for doc in all_docs_content:
            # Add up to 10 chunks per document to retrieved_chunks for the validator
            chunks = doc["content"].split("\n")[:10]
            for i, c in enumerate(chunks):
                if c.strip():
                    retrieved_chunks.append({
                        "content": c,
                        "document_id": str(doc["id"]),
                        "filename": doc["filename"]
                    })

        if intent == "summarise_each":
            # Summarize each document individually in parallel
            async def get_summary(doc):
                prompt = f"Summarize this document's purpose, key findings, and takeaways.\n\nDocument: {doc['filename']}\n{doc['content']}"
                response = await litellm.acompletion(
                    model="gemini/gemini-1.5-pro",
                    messages=[{"role": "user", "content": prompt}],
                    api_base=LITELLM_PROXY_URL,
                    api_key="sk-dummy",
                    temperature=0.3,
                    max_tokens=2000
                )
                content = response.choices[0].message.content
                if response.choices[0].finish_reason == "length":
                    content += "\n\n[Summary truncated.]"
                return f"### Summary of {doc['filename']}:\n{content}"
            
            tasks = [get_summary(doc) for doc in all_docs_content]
            summaries = await asyncio.gather(*tasks)
            final_summary = "\n\n---\n\n".join(summaries)
            
        else:
            # Combined summary (Simplified Map-Reduce)
            combined_content = "\n\n".join([f"--- Document: {d['filename']} ---\n{d['content']}" for d in all_docs_content])
            
            prompt = f"Summarize these documents. Identify key themes, findings, and takeaways.\n\nDocuments:\n{combined_content}"

            response = await litellm.acompletion(
                model="gemini/gemini-1.5-pro",
                messages=[{"role": "user", "content": prompt}],
                api_base=LITELLM_PROXY_URL,
                api_key="sk-dummy",
                temperature=0.3,
                max_tokens=3000
            )
            final_summary = response.choices[0].message.content
            if response.choices[0].finish_reason == "length":
                final_summary += "\n\n[Summary truncated due to length constraints.]"
            
        return {
            "draft_response": final_summary,
            "retrieved_chunks": retrieved_chunks
        }
        
    except Exception as e:
        logger.error(f"Error in summarise_node: {str(e)}", exc_info=True)
        return {"draft_response": f"I encountered an error while summarizing the documents: {str(e)}"}
