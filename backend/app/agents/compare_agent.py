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
        # Fetch content for the documents
        all_docs_content = []
        async with async_session() as session:
            for doc_id in doc_ids:
                doc_meta = await session.get(Document, doc_id)
                filename = doc_meta.filename if doc_meta else str(doc_id)
                
                # Fetch all chunks (limit slightly if many)
                stmt = select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.page_number, Chunk.id).limit(100)
                result = await session.execute(stmt)
                chunks = result.scalars().all()
                doc_content = "\n".join([c.content for c in chunks])
                all_docs_content.append({"id": doc_id, "filename": filename, "content": doc_content})
        
        combined_docs = "\n\n".join([f"--- Document: {d['filename']} ---\n{d['content']}" for d in all_docs_content])
        
        system_prompt = """
        You are an expert document analyst specializing in cross-document comparisons. 
        Given a set of documents and a user query, your task is to:
        1. Identify the key dimensions or categories for comparison relevant to the query.
        2. Create a structured comparison matrix (using markdown tables where appropriate).
        3. Highlight any contradictions or conflicting information between documents.
        4. Provide a balanced synthesis of the similarities and differences.
        
        Use clear headings and concise bullet points.
        """
        
        response = await litellm.acompletion(
            model="gemini/gemini-1.5-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}\n\nDocuments:\n{combined_docs}"}
            ],
            api_base=LITELLM_PROXY_URL,
            temperature=0.2
        )
        
        comparison = response.choices[0].message.content
        return {"draft_response": comparison}
        
    except Exception as e:
        logger.error(f"Error in compare_node: {str(e)}")
        return {"draft_response": f"I encountered an error while comparing the documents: {str(e)}"}
