import os
import litellm
import logging
from typing import List, Dict, Any
from sqlalchemy import select
from .state import DocIntelState
from backend.app.models.document import Chunk, Document
from backend.app.db.session import async_session

# Point to LiteLLM Proxy if available
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://litellm:4000")

logger = logging.getLogger(__name__)

async def compare_node(state: DocIntelState) -> DocIntelState:
    """
    Performs cross-document comparison using Gemini 1.5 Pro.
    Identifies dimensions of comparison and builds a structured matrix.
    """
    query = state.get("query", "Compare these documents.")
    doc_ids = state.get("documents", [])
    
    logger.info(f"Comparison node processing query: {query} for documents: {doc_ids}")
    
    if not doc_ids:
        return {"draft_response": "No documents provided for comparison."}
    
    try:
        # Fetch content for the documents in batch
        all_docs_content = []
        async with async_session() as session:
            # Batch fetch document metadata
            doc_meta_stmt = select(Document).where(Document.id.in_(doc_ids))
            doc_meta_result = await session.execute(doc_meta_stmt)
            doc_metas = {doc.id: doc for doc in doc_meta_result.scalars().all()}
            
            # Fetch chunks for all docs (limit to avoid excessive context if many huge docs)
            # Using a simplified batch approach: fetch top 100 chunks for each doc in a more efficient way if possible,
            # but for now, even a single query for all chunks of these docs is better than N queries.
            chunk_stmt = select(Chunk).where(Chunk.document_id.in_(doc_ids)).order_by(Chunk.document_id, Chunk.page_number, Chunk.id)
            chunk_result = await session.execute(chunk_stmt)
            all_chunks = chunk_result.scalars().all()
            
            # Group chunks by document_id and limit to 100 per doc
            doc_chunks = {}
            for chunk in all_chunks:
                if chunk.document_id not in doc_chunks:
                    doc_chunks[chunk.document_id] = []
                if len(doc_chunks[chunk.document_id]) < 100:
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

        combined_docs = "\n\n".join([f"--- Document: {d['filename']} ---\n{d['content']}" for d in all_docs_content])
        
        system_prompt = "Compare documents: identify key dimensions, build a markdown comparison table, highlight contradictions, and synthesize differences."

        response = await litellm.acompletion(
            model="gemini/gemini-1.5-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}\n\nDocuments:\n{combined_docs}"}
            ],
            api_base=LITELLM_PROXY_URL,
            api_key="sk-dummy",
            temperature=0.2,
            max_tokens=3000
        )

        comparison = response.choices[0].message.content
        if response.choices[0].finish_reason == "length":
            comparison += "\n\n[Comparison truncated due to length constraints.]"
        return {
            "draft_response": comparison,
            "retrieved_chunks": retrieved_chunks
        }
        
    except Exception as e:
        logger.error(f"Error in compare_node: {str(e)}")
        return {"draft_response": f"I encountered an error while comparing the documents: {str(e)}"}
