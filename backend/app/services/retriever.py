import asyncio
import uuid
import os
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, desc, ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
import litellm
from backend.app.models.document import Chunk
from backend.app.services.embeddings import generate_embeddings

# Point to LiteLLM Proxy
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://litellm:4000")

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_multi_queries(self, query_text: str) -> List[str]:
        """
        Use Gemini 1.5 Flash (via LiteLLM) to generate 3-5 query variations.
        """
        try:
            prompt = f"""
            You are an expert search assistant. Generate 3-5 variations of the following user query 
            to help improve retrieval from a document database. 
            The variations should capture different aspects or synonyms of the original query.
            
            Original query: {query_text}
            
            Return ONLY the variations, one per line, without any numbering or additional text.
            """
            
            response = await asyncio.to_thread(
                litellm.completion,
                model="gemini/gemini-1.5-flash",
                messages=[{"role": "user", "content": prompt}],
                api_base=LITELLM_PROXY_URL,
                api_key="sk-dummy",
                timeout=10
            )
            
            variations = response.choices[0].message.content.strip().split("\n")
            # Clean up and filter variations
            queries = [v.strip() for v in variations if v.strip()]
            # Include original query if not already there
            if query_text not in queries:
                queries.insert(0, query_text)
            
            return queries[:6] # Original + up to 5 variations
            
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
        Use Gemini 1.5 Pro (via LiteLLM) to score and re-rank the top candidates.
        """
        if not results:
            return []

        try:
            # Prepare chunks for re-ranking
            # We'll use the first 20 results for re-ranking
            candidates = results[:20]
            
            chunks_to_rank = []
            for i, res in enumerate(candidates):
                chunks_to_rank.append({
                    "id": str(res["chunk"].id),
                    "content": res["chunk"].content[:1000] # Limit content length
                })

            prompt = f"""
            You are an expert relevance judge. Given the following user query and a list of document chunks, 
            score each chunk on a scale of 0 to 10 based on its relevance to the query.
            A score of 10 means highly relevant, 0 means not relevant at all.
            
            Query: {query_text}
            
            Chunks:
            {json.dumps(chunks_to_rank, indent=2)}
            
            Return ONLY a JSON list of objects, each containing 'id' and 'score'. 
            Example: [{{"id": "uuid-1", "score": 9.5}}, {{"id": "uuid-2", "score": 4.0}}]
            """
            
            response = await asyncio.to_thread(
                litellm.completion,
                model="gemini/gemini-1.5-pro",
                messages=[{"role": "user", "content": prompt}],
                api_base=LITELLM_PROXY_URL,
                api_key="sk-dummy",
                timeout=30,
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
            scores_map = {str(item["id"]): float(item["score"]) for item in scores_list if "id" in item and "score" in item}
            
            for res in candidates:
                res["rerank_score"] = scores_map.get(str(res["chunk"].id), 0.0)
            
            # Sort by rerank score
            reranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            
            return reranked[:top_n]

        except Exception as e:
            logger.error(f"Error during re-ranking: {str(e)}")
            return results[:top_n]

    async def dense_search(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform dense vector search using cosine similarity.
        """
        # Similarity = 1 - cosine_distance
        distance_expr = Chunk.embedding.cosine_distance(query_embedding)
        score_expr = (1 - distance_expr).label("score")
        
        stmt = (
            select(Chunk, score_expr)
            .order_by(distance_expr)
            .limit(top_k)
        )
        result = await self.session.execute(stmt)
        # Using a list comprehension to unpack the Row objects
        return [{"chunk": row[0], "score": float(row[1])} for row in result.all()]

    async def sparse_search(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform sparse keyword search using PostgreSQL full-text search.
        """
        query = func.plainto_tsquery("english", query_text)
        score_expr = func.ts_rank(Chunk.search_vector, query).label("score")
        
        stmt = (
            select(Chunk, score_expr)
            .where(Chunk.search_vector.op("@@")(query))
            .order_by(score_expr.desc())
            .limit(top_k)
        )
        result = await self.session.execute(stmt)
        return [{"chunk": row[0], "score": float(row[1])} for row in result.all()]

    async def hybrid_search(
        self, 
        query_text: str, 
        top_k: int = 5, 
        rrf_k: int = 60
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
        
        # 2. Generate embeddings for all queries at once
        embedding_task = asyncio.to_thread(generate_embeddings, queries)
        
        # 3. Start all sparse searches in parallel
        sparse_tasks = [
            asyncio.create_task(self.sparse_search(q, top_k=20)) 
            for q in queries
        ]
        
        embeddings = await embedding_task
        
        # 4. Start all dense searches in parallel (once embeddings are ready)
        dense_tasks = [
            asyncio.create_task(self.dense_search(emb, top_k=20)) 
            for emb in embeddings
        ]
        
        # 5. Wait for all searches to complete
        sparse_results_list = await asyncio.gather(*sparse_tasks)
        dense_results_list = await asyncio.gather(*dense_tasks)

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
        )[:20]

        candidate_results = [
            {"chunk": chunks_map[cid], "rrf_score": score} 
            for cid, score in sorted_candidates
        ]

        # 8. Re-rank top candidates
        reranked_results = await self.rerank_results(query_text, candidate_results, top_n=top_k)
        
        return reranked_results
