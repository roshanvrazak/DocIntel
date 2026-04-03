import os
import json
import hashlib
import logging
import redis.asyncio as aioredis
from sqlalchemy import select
from .state import DocIntelState
from backend.app.services.retriever import HybridRetriever
from backend.app.models.document import Document
from backend.app.db.session import async_session
from backend.app.config import LITELLM_PROXY_URL, REDIS_URL, RETRIEVAL_CACHE_TTL, RETRIEVER_TOP_K
from backend.app.services.context_manager import truncate_context
from backend.app.services.metrics import observe_retrieval_chunks
import litellm

logger = logging.getLogger(__name__)

_cache: aioredis.Redis | None = None


def _get_cache() -> aioredis.Redis:
    global _cache
    if _cache is None:
        _cache = aioredis.from_url(REDIS_URL)
    return _cache


async def rag_node(state: DocIntelState) -> DocIntelState:
    """RAG-based QA using hybrid retrieval + Gemini 1.5 Pro."""
    query = state.get("query")
    doc_ids = state.get("documents", [])

    logger.info("RAG node processing query: %s for %d documents", query[:80], len(doc_ids))

    # --- Cache lookup ---
    doc_ids_key = ":".join(sorted(str(d) for d in doc_ids))
    cache_key = f"rag:{hashlib.md5(f'{query}|{doc_ids_key}'.encode()).hexdigest()}"
    try:
        cached = await _get_cache().get(cache_key)
        if cached:
            logger.info("RAG cache hit for query: %s", query[:50])
            return json.loads(cached)
    except Exception as e:
        logger.warning("Cache read failed: %s", e)

    try:
        async with async_session() as session:
            retriever = HybridRetriever(session)
            results = await retriever.hybrid_search(query, top_k=RETRIEVER_TOP_K, document_ids=doc_ids)

            # Enrich with document filenames for citations
            doc_ids_set = {r["chunk"].document_id for r in results}
            doc_stmt = select(Document).where(Document.id.in_(doc_ids_set))
            doc_result = await session.execute(doc_stmt)
            doc_map = {doc.id: doc.filename for doc in doc_result.scalars().all()}

        # Build chunk metadata list for truncation (ordered by relevance)
        all_chunks_meta = []
        for res in results:
            chunk = res["chunk"]
            filename = doc_map.get(chunk.document_id, "Unknown")
            all_chunks_meta.append({
                "content": chunk.content,
                "document_id": str(chunk.document_id),
                "chunk_id": str(chunk.id),
                "filename": filename,
                "page_number": chunk.page_number or 1,
                "score": res.get("rerank_score", res.get("score", 0)),
            })

        system_prompt = (
            "Answer ONLY from the provided context. Use inline citations [1], [2], etc. "
            "If the answer is not supported by the context, say so."
        )

        # Enforce context budget before sending to LLM
        prefix_overhead = len(system_prompt) + len(query) + 50  # prompt scaffolding chars
        retrieved_chunks, was_truncated = truncate_context(all_chunks_meta, prefix=" " * prefix_overhead)
        observe_retrieval_chunks(len(retrieved_chunks))

        context_parts = [
            f"[{i+1}] Source: {c['filename']} (page {c['page_number']})\nContent: {c['content']}"
            for i, c in enumerate(retrieved_chunks)
        ]
        context_text = "\n\n".join(context_parts)
        if was_truncated:
            context_text += "\n\n[Note: some source chunks were omitted to fit the context limit.]"

        response = await litellm.acompletion(
            model="gemini/gemini-1.5-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"},
            ],
            api_base=LITELLM_PROXY_URL,
            api_key="sk-dummy",
            temperature=0.2,
            max_tokens=2000,
        )

        draft_response = response.choices[0].message.content
        if response.choices[0].finish_reason == "length":
            draft_response += "\n\n[Response truncated. Try asking a more specific question.]"

    except Exception as e:
        logger.error("Error in rag_node: %s", str(e), exc_info=True)
        draft_response = "I encountered an error while analyzing the documents. Please try again."
        retrieved_chunks = []

    result = {"retrieved_chunks": retrieved_chunks, "draft_response": draft_response}

    # --- Cache store ---
    try:
        await _get_cache().setex(cache_key, RETRIEVAL_CACHE_TTL, json.dumps(result))
    except Exception as e:
        logger.warning("Cache write failed: %s", e)

    return result
