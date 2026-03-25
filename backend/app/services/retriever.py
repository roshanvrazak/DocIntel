import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.document import Chunk
from backend.app.services.embeddings import generate_embeddings

class HybridRetriever:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def dense_search(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform dense vector search using cosine similarity.
        """
        # cosine_distance is used by pgvector for vector_cosine_ops
        # Similarity = 1 - distance
        stmt = (
            select(
                Chunk, 
                (1 - Chunk.embedding.cosine_distance(query_embedding)).label("score")
            )
            .order_by(Chunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        result = await self.session.execute(stmt)
        return [{"chunk": row[0], "score": float(row[1])} for row in result.all()]

    async def sparse_search(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform sparse keyword search using PostgreSQL full-text search.
        """
        # plainto_tsquery converts query text to a tsquery
        # ts_rank calculates the relevance score
        query = func.plainto_tsquery("english", query_text)
        stmt = (
            select(
                Chunk, 
                func.ts_rank(Chunk.search_vector, query).label("score")
            )
            .where(Chunk.search_vector.op("@@")(query))
            .order_by(desc("score"))
            .limit(top_k)
        )
        result = await self.session.execute(stmt)
        return [{"chunk": row[0], "score": float(row[1])} for row in result.all()]

    async def hybrid_search(
        self, 
        query_text: str, 
        top_k: int = 10, 
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search by combining dense and sparse search results
        using Reciprocal Rank Fusion (RRF).
        """
        # 1. Generate query embedding
        # generate_embeddings is sync, so we wrap it in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, 
            lambda: generate_embeddings([query_text])
        )
        query_embedding = embeddings[0]

        # 2. Execute dense and sparse searches in parallel
        dense_task = self.dense_search(query_embedding, top_k=top_k * 2)
        sparse_task = self.sparse_search(query_text, top_k=top_k * 2)
        
        dense_results, sparse_results = await asyncio.gather(dense_task, sparse_task)

        # 3. Apply RRF Fusion
        # RRF formula: score = sum(1 / (rank + k))
        rrf_scores: Dict[Any, float] = {}
        chunks_map: Dict[Any, Chunk] = {}

        # Process dense results
        for rank, res in enumerate(dense_results, 1):
            chunk = res["chunk"]
            chunk_id = chunk.id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rank + rrf_k)
            chunks_map[chunk_id] = chunk

        # Process sparse results
        for rank, res in enumerate(sparse_results, 1):
            chunk = res["chunk"]
            chunk_id = chunk.id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rank + rrf_k)
            chunks_map[chunk_id] = chunk

        # 4. Sort results by RRF score and return top_k
        sorted_results = sorted(
            rrf_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:top_k]

        return [
            {"chunk": chunks_map[cid], "rrf_score": score} 
            for cid, score in sorted_results
        ]
