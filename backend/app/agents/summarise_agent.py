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
        # Fetch content for the documents
        all_docs_content = []
        async with async_session() as session:
            for doc_id in doc_ids:
                # Fetch filename for better identification
                doc_meta = await session.get(Document, doc_id)
                filename = doc_meta.filename if doc_meta else str(doc_id)
                
                # Fetch all chunks
                stmt = select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.page_number, Chunk.id)
                result = await session.execute(stmt)
                chunks = result.scalars().all()
                doc_content = "\n".join([c.content for c in chunks])
                all_docs_content.append({"id": doc_id, "filename": filename, "content": doc_content})
        
        if intent == "summarise_each":
            # Summarize each document individually
            summaries = []
            for doc in all_docs_content:
                prompt = f"Provide a detailed and concise summary of the following document:\n\nDocument Name: {doc['filename']}\nContent: {doc['content']}"
                response = await litellm.acompletion(
                    model="gemini/gemini-1.5-pro",
                    messages=[{"role": "user", "content": prompt}],
                    api_base=LITELLM_PROXY_URL,
                    temperature=0.3
                )
                summaries.append(f"### Summary of {doc['filename']}:\n{response.choices[0].message.content}")
            
            final_summary = "\n\n---\n\n".join(summaries)
            
        else:
            # Combined summary (Simplified Map-Reduce)
            # For Gemini 1.5 Pro, we can often send quite a lot. 
            # If documents are huge, we'd need a more complex recursive map-reduce.
            combined_content = "\n\n".join([f"--- Document: {d['filename']} ---\n{d['content']}" for d in all_docs_content])
            
            prompt = f"""
            Provide a comprehensive summary of the following documents. 
            Identify key themes, major findings, and important takeaways across all provided materials.
            
            Documents:
            {combined_content}
            """
            
            response = await litellm.acompletion(
                model="gemini/gemini-1.5-pro",
                messages=[{"role": "user", "content": prompt}],
                api_base=LITELLM_PROXY_URL,
                temperature=0.3
            )
            final_summary = response.choices[0].message.content
            
        return {"draft_response": final_summary}
        
    except Exception as e:
        logger.error(f"Error in summarise_node: {str(e)}")
        return {"draft_response": f"I encountered an error while summarizing the documents: {str(e)}"}
