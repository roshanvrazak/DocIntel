import pytest
import uuid
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
@patch("backend.app.services.retriever.generate_embeddings")
async def test_hybrid_search_rrf(mock_gen_embed, retriever):
    # Mock embedding generation
    mock_gen_embed.return_value = [[0.1]*768]
    
    # Create test chunks
    id1, id2, id3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    chunk1 = Chunk(id=id1, content="chunk 1")
    chunk2 = Chunk(id=id2, content="chunk 2")
    chunk3 = Chunk(id=id3, content="chunk 3")
    
    # Mock dense_search results
    # Rank 1: chunk1, Rank 2: chunk2
    dense_results = [
        {"chunk": chunk1, "score": 0.9},
        {"chunk": chunk2, "score": 0.8}
    ]
    
    # Mock sparse_search results
    # Rank 1: chunk3, Rank 2: chunk1
    sparse_results = [
        {"chunk": chunk3, "score": 0.7},
        {"chunk": chunk1, "score": 0.6}
    ]
    
    with patch.object(retriever, 'dense_search', return_value=dense_results), \
         patch.object(retriever, 'sparse_search', return_value=sparse_results):
        
        results = await retriever.hybrid_search("test query", top_k=3, rrf_k=60)
        
        # RRF Scores calculation:
        # chunk1 (Rank 1 in Dense, Rank 2 in Sparse): 1/(1+60) + 1/(2+60) = 0.01639 + 0.01613 = 0.03252
        # chunk3 (Rank 1 in Sparse): 1/(1+60) = 0.01639
        # chunk2 (Rank 2 in Dense): 1/(2+60) = 0.01613
        
        assert len(results) == 3
        assert results[0]["chunk"].id == id1
        assert results[1]["chunk"].id == id3
        assert results[2]["chunk"].id == id2
        assert results[0]["rrf_score"] > results[1]["rrf_score"]
        assert results[1]["rrf_score"] > results[2]["rrf_score"]

@pytest.mark.anyio
@patch("backend.app.services.retriever.generate_embeddings")
async def test_hybrid_search_empty_results(mock_gen_embed, retriever):
    mock_gen_embed.return_value = [[0.1]*768]
    
    with patch.object(retriever, 'dense_search', return_value=[]), \
         patch.object(retriever, 'sparse_search', return_value=[]):
        
        results = await retriever.hybrid_search("test query")
        assert len(results) == 0
