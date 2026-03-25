import pytest
import uuid
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.services.retriever import HybridRetriever
from backend.app.models.document import Chunk

# Custom mock for result to handle .all()
class MockResult:
    def __init__(self, data):
        self.data = data
    def all(self):
        return self.data

@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session

@pytest.fixture
def retriever(mock_session):
    return HybridRetriever(mock_session)

@pytest.mark.anyio
async def test_dense_search(retriever, mock_session):
    # Mocking Chunk and row result
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    chunk1 = Chunk(id=id1, content="chunk 1")
    chunk2 = Chunk(id=id2, content="chunk 2")
    
    # Result rows are tuples: (Chunk, score)
    mock_session.execute.return_value = MockResult([(chunk1, 0.9), (chunk2, 0.8)])
    
    results = await retriever.dense_search([0.1]*768, top_k=2)
    
    assert len(results) == 2
    assert results[0]["chunk"].id == id1
    assert results[0]["score"] == 0.9
    assert results[1]["chunk"].id == id2
    assert results[1]["score"] == 0.8
    mock_session.execute.assert_called_once()

@pytest.mark.anyio
async def test_sparse_search(retriever, mock_session):
    id1 = uuid.uuid4()
    chunk1 = Chunk(id=id1, content="keyword match")
    
    mock_session.execute.return_value = MockResult([(chunk1, 0.5)])
    
    results = await retriever.sparse_search("keyword", top_k=1)
    
    assert len(results) == 1
    assert results[0]["chunk"].id == id1
    assert results[0]["score"] == 0.5
    mock_session.execute.assert_called_once()

@pytest.mark.anyio
@patch("litellm.completion")
async def test_generate_multi_queries(mock_completion, retriever):
    # Mock LiteLLM response
    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="query variation 1\nquery variation 2\nquery variation 3"))]
    )
    
    queries = await retriever.generate_multi_queries("original query")
    
    assert len(queries) == 4
    assert "original query" in queries
    assert "query variation 1" in queries
    assert "query variation 2" in queries
    assert "query variation 3" in queries

@pytest.mark.anyio
@patch("litellm.completion")
async def test_rerank_results(mock_completion, retriever):
    id1, id2 = uuid.uuid4(), uuid.uuid4()
    chunk1 = Chunk(id=id1, content="relevant content")
    chunk2 = Chunk(id=id2, content="irrelevant content")
    
    results = [
        {"chunk": chunk1, "rrf_score": 0.05},
        {"chunk": chunk2, "rrf_score": 0.06} # Initially higher RRF score
    ]
    
    # Mock LiteLLM re-ranking response
    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps([
            {"id": str(id1), "score": 9.5},
            {"id": str(id2), "score": 2.0}
        ])))]
    )
    
    reranked = await retriever.rerank_results("query", results, top_n=2)
    
    assert len(reranked) == 2
    assert reranked[0]["chunk"].id == id1 # Should be first now
    assert reranked[0]["rerank_score"] == 9.5
    assert reranked[1]["chunk"].id == id2
    assert reranked[1]["rerank_score"] == 2.0

@pytest.mark.anyio
@patch("backend.app.services.retriever.generate_embeddings")
async def test_hybrid_search_integration(mock_gen_embed, retriever):
    # Mock multi-query generation
    with patch.object(retriever, "generate_multi_queries", return_value=["query1", "query2"]):
        # Mock embedding generation for 2 queries
        mock_gen_embed.return_value = [[0.1]*768, [0.2]*768]
        
        id1, id2 = uuid.uuid4(), uuid.uuid4()
        chunk1 = Chunk(id=id1, content="chunk 1")
        chunk2 = Chunk(id=id2, content="chunk 2")
        
        # Mock sparse and dense searches
        # Returning different results for different queries to test merging
        async def mock_sparse(q, top_k=20):
            if q == "query1": return [{"chunk": chunk1, "score": 0.5}]
            return [{"chunk": chunk2, "score": 0.5}]
            
        async def mock_dense(emb, top_k=20):
            if emb[0] == 0.1: return [{"chunk": chunk1, "score": 0.5}]
            return [{"chunk": chunk2, "score": 0.5}]

        with patch.object(retriever, "sparse_search", side_effect=mock_sparse), \
             patch.object(retriever, "dense_search", side_effect=mock_dense):
            
            # Mock reranking to just return results as is
            async def mock_rerank(q, results, top_n=5):
                return results[:top_n]
                
            with patch.object(retriever, "rerank_results", side_effect=mock_rerank):
                results = await retriever.hybrid_search("test query", top_k=2)
                
                assert len(results) == 2
                # Both chunks should be present because they were found by different query variations
                chunk_ids = [r["chunk"].id for r in results]
                assert id1 in chunk_ids
                assert id2 in chunk_ids

@pytest.mark.anyio
@patch("backend.app.services.retriever.generate_embeddings")
async def test_hybrid_search_empty_results(mock_gen_embed, retriever):
    mock_gen_embed.return_value = []
    
    with patch.object(retriever, "generate_multi_queries", return_value=["query"]):
        with patch.object(retriever, 'dense_search', return_value=[]), \
             patch.object(retriever, 'sparse_search', return_value=[]):
            
            results = await retriever.hybrid_search("test query")
            assert len(results) == 0
