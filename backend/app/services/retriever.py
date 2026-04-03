import asyncio
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import litellm
from backend.app.models.document import Chunk
from backend.app.services.embeddings import generate_embeddings
from backend.app.db.session import async_session as _session_factory
from backend.app.config import LITELLM_PROXY_URL, LITELLM_API_KEY

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_multi_queries(self, query_text: str) -> List[str]:
        """
        Use Gemini 1.5 Flash (via LiteLLM) to generate 3 query variations.
        """
        try:
            prompt = f"Generate 3 search query variations for: {query_text}\nReturn ONLY variations, one per line."

            response = await asyncio.to_thread(
                litellm.completion,
                model="gemini/gemini-1.5-flash",
                messages=[{"role": "user", "content": prompt}],
                api_base=LITELLM_PROXY_URL,
                api_key=LITELLM_API_KEY,
                timeout=10,
                max_tokens=150
            )

            variations = response.choices[0].message.content.strip().split("\n")
            queries = [v.strip() for v in variations if v.strip()]
            if query_text not in queries:
                queries.insert(0, query_text)

            return queries[:4] # Original + up to 3 variations
            
        except Exception as e:
            logger.error(f"Error generating multi-queries: {str(e)}")
            return [query_text]

    async def rerank_results(
        self, 
        query_text: str, 
        results: List[Dict[str, Any]], 
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Use Gemini 1.5 Flash (via LiteLLM) to score and re-rank the top candidates.
        """
        if not results:
            return []

        try:
            # Re-rank top 10 candidates (reduced from 20 to save tokens)
            candidates = results[:10]

            chunks_to_rank = []
            for i, res in enumerate(candidates):
                chunks_to_rank.append({
                    "id": str(res["chunk"].id),
                    "content": res["chunk"].content[:500]  # Truncate to 500 chars
                })

            prompt = f"Score each chunk's relevance (0-10) to the query.\nQuery: {query_text}\nChunks:\n{json.dumps(chunks_to_rank)}\nReturn JSON: [{{\"id\": \"...\", \"score\": N}}]"

            response = await asyncio.to_thread(
                litellm.completion,
                model="gemini/gemini-1.5-flash",  # Downgraded from Pro — scoring doesn't need Pro
                messages=[{"role": "user", "content": prompt}],
                api_base=LITELLM_PROXY_URL,
                api_key=LITELLM_API_KEY,
                timeout=30,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            # Some LLMs might wrap JSON in backticks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            scores_list = json.loads(content)
            # If the LLM returns an object with a list inside, handle it
            if isinstance(scores_list, dict):
                for key in ["scores", "results", "chunks"]:
                    if key in scores_list and isinstance(scores_list[key], list):
                        scores_list = scores_list[key]
                        break
            
            if not isinstance(scores_list, list):
                logger.warning(f"Unexpected rerank output format: {content}")
                return results[:top_n]

            # Map scores back to results
            scores_map: Dict[str, float] = {}
            for item in scores_list:
                if "id" not in item or "score" not in item:
                    continue
                try:
                    scores_map[str(item["id"])] = float(item["score"])
                except (ValueError, TypeError):
                    logger.warning("Rerank: non-numeric score for chunk %s: %r", item.get("id"), item.get("score"))
            
            for res in candidates:
                res["rerank_score"] = scores_map.get(str(res["chunk"].id), 0.0)
            
            # Sort by rerank score
            reranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            
            return reranked[:top_n]

        except Exception as e:
            logger.error(f"Error during re-ranking: {str(e)}")
            return results[:top_n]

    async def dense_search(self, query_embedding: List[float], top_k: int = 10, document_ids: Optional[List[uuid.UUID]] = None) -> List[Dict[str, Any]]:
        """
        Perform dense vector search using cosine similarity.
        """
        # Similarity = 1 - cosine_distance
        distance_expr = Chunk.embedding.cosine_distance(query_embedding)
        score_expr = (1 - distance_expr).label("score")

        stmt = select(Chunk, score_expr)
        if document_ids:
            stmt = stmt.where(Chunk.document_id.in_(document_ids))
        stmt = stmt.order_by(distance_expr).limit(top_k)
            
        result = await self.session.execute(stmt)
        # Using a list comprehension to unpack the Row objects
        return [{"chunk": row[0], "score": float(row[1])} for row in result.all()]

    async def sparse_search(self, query_text: str, top_k: int = 10, document_ids: Optional[List[uuid.UUID]] = None) -> List[Dict[str, Any]]:
        """
        Perform sparse keyword search using PostgreSQL full-text search.
        """
        query = func.plainto_tsquery("english", query_text)
        score_expr = func.ts_rank(Chunk.search_vector, query).label("score")

        stmt = select(Chunk, score_expr).where(Chunk.search_vector.op("@@")(query))
        if document_ids:
            stmt = stmt.where(Chunk.document_id.in_(document_ids))
        stmt = stmt.order_by(score_expr.desc()).limit(top_k)
            
        result = await self.session.execute(stmt)
        return [{"chunk": row[0], "score": float(row[1])} for row in result.all()]

    async def hybrid_search(
        self, 
        query_text: str, 
        top_k: int = 5, 
        rrf_k: int = 60,
        document_ids: Optional[List[uuid.UUID]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform multi-query hybrid search:
        1. Generate query variations.
        2. Perform dense and sparse search for each variation.
        3. Merge results using Reciprocal Rank Fusion (RRF).
        4. Re-rank top results using a stronger LLM.
        """
        # 1. Generate multi-queries
        queries = await self.generate_multi_queries(query_text)

        # 2. Start embedding all query variations in a background thread immediately
        #    so the DB work below overlaps with the Ollama HTTP call.
        embedding_task = asyncio.to_thread(generate_embeddings, queries)

        # 3. Sparse searches run on self.session (sequential — session not concurrent-safe)
        sparse_results_list = []
        for q in queries:
            res = await self.sparse_search(q, top_k=20, document_ids=document_ids)
            sparse_results_list.append(res)

        # 4. Wait for embeddings (likely already done while sparse searches ran)
        embeddings = await embedding_task

        # 5. Dense searches: each needs its own session so they can run concurrently
        async def _dense_with_session(emb: List[float]) -> List[Dict[str, Any]]:
            async with _session_factory() as session:
                retriever = HybridRetriever(session)
                return await retriever.dense_search(emb, top_k=20, document_ids=document_ids)

        dense_results_list = await asyncio.gather(*[_dense_with_session(emb) for emb in embeddings])

        # 6. Apply RRF Fusion
        rrf_scores: Dict[uuid.UUID, float] = {}
        chunks_map: Dict[uuid.UUID, Chunk] = {}

        # Combine all results (dense and sparse)
        for results_list in [dense_results_list, sparse_results_list]:
            for results in results_list:
                for rank, res in enumerate(results, 1):
                    chunk = res["chunk"]
                    chunk_id = chunk.id
                    rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rank + rrf_k)
                    chunks_map[chunk_id] = chunk

        # 7. Sort by RRF score to get top candidates for re-ranking
        sorted_candidates = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        candidate_results = [
            {"chunk": chunks_map[cid], "rrf_score": score} 
            for cid, score in sorted_candidates
        ]

        # 8. Re-rank top candidates
        reranked_results = await self.rerank_results(query_text, candidate_results, top_n=top_k)
        
        return reranked_results
