import os
import litellm
import logging
from typing import List, Dict, Any
from .state import DocIntelState
from backend.app.services.retriever import HybridRetriever
from backend.app.db.session import async_session

# Point to LiteLLM Proxy if available
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://litellm:4000")

logger = logging.getLogger(__name__)

async def rag_node(state: DocIntelState) -> DocIntelState:
    """
    Performs RAG-based Question Answering using Gemini 1.5 Pro.
    """
    query = state.get("query")
    doc_ids = state.get("documents", [])
    
    logger.info(f"RAG node processing query: {query} for documents: {doc_ids}")
    
    try:
        async with async_session() as session:
            retriever = HybridRetriever(session)
            results = await retriever.hybrid_search(query, top_k=5, document_ids=doc_ids)
            
        # Format context and citations
        context_parts = []
        retrieved_chunks = []
        for i, res in enumerate(results):
            chunk = res["chunk"]
            context_parts.append(f"[{i+1}] Source Document ID: {chunk.document_id}\nContent: {chunk.content}")
            retrieved_chunks.append({
                "content": chunk.content,
                "document_id": str(chunk.document_id),
                "chunk_id": str(chunk.id),
                "score": res.get("rerank_score", res.get("score", 0))
            })
            
        context_text = "\n\n".join(context_parts)
        
        system_prompt = f"""
        You are an expert document analysis assistant. Answer the user's question based ONLY on the provided document segments.
        Use the numeric citations [1], [2], etc., when referring to information from a specific segment.
        If the answer is not in the context, state that you don't have enough information to answer definitively.
        
        Context:
        {context_text}
        """
        
        response = await litellm.acompletion(
            model="gemini/gemini-1.5-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {query}"}
            ],
            api_base=LITELLM_PROXY_URL,
            temperature=0.2
        )
        
        draft_response = response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error in rag_node: {str(e)}")
        draft_response = f"I encountered an error while analyzing the documents: {str(e)}"
        retrieved_chunks = []
        
    return {
        "retrieved_chunks": retrieved_chunks,
        "draft_response": draft_response
    }
