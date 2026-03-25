from unittest.mock import MagicMock, patch
import pytest
from backend.app.services.chunker import ChunkerService, semantic_chunk

@patch("backend.app.services.chunker.LiteLLMEmbeddings")
@patch("backend.app.services.chunker.SemanticChunker")
def test_semantic_chunk_success(mock_chunker_cls, mock_embeddings_cls):
    # Reset singleton for testing
    ChunkerService._instance = None
    
    # Mocking LiteLLMEmbeddings instance
    mock_embeddings = MagicMock()
    mock_embeddings_cls.return_value = mock_embeddings
    
    # Mocking SemanticChunker instance and its split_text method
    mock_chunker = MagicMock()
    mock_chunker.split_text.return_value = ["Chunk 1", "Chunk 2"]
    mock_chunker_cls.return_value = mock_chunker
    
    # Text to chunk
    text = "This is a long text that needs to be chunked."
    
    # Execute the function
    chunks = semantic_chunk(text)
    
    # Assertions
    assert len(chunks) == 2
    assert chunks[0] == "Chunk 1"
    assert chunks[1] == "Chunk 2"
    
    # Verify mock calls
    mock_embeddings_cls.assert_called_once()
    mock_chunker_cls.assert_called_once_with(mock_embeddings)
    mock_chunker.split_text.assert_called_once_with(text)

@patch("backend.app.services.chunker.LiteLLMEmbeddings")
@patch("backend.app.services.chunker.SemanticChunker")
def test_semantic_chunk_connection_failure(mock_chunker_cls, mock_embeddings_cls):
    # Reset singleton for testing
    ChunkerService._instance = None
    
    # Mocking SemanticChunker split_text to raise connection error
    mock_embeddings = MagicMock()
    mock_embeddings_cls.return_value = mock_embeddings
    
    mock_chunker = MagicMock()
    mock_chunker.split_text.side_effect = Exception("Connection refused")
    mock_chunker_cls.return_value = mock_chunker
    
    with pytest.raises(Exception) as excinfo:
        semantic_chunk("Sample text")
    assert "LiteLLM service connection failure" in str(excinfo.value)

@patch("backend.app.services.chunker.LiteLLMEmbeddings")
@patch("backend.app.services.chunker.SemanticChunker")
def test_semantic_chunk_timeout(mock_chunker_cls, mock_embeddings_cls):
    # Reset singleton for testing
    ChunkerService._instance = None
    
    # Mocking SemanticChunker split_text to raise timeout
    mock_embeddings = MagicMock()
    mock_embeddings_cls.return_value = mock_embeddings
    
    mock_chunker = MagicMock()
    mock_chunker.split_text.side_effect = Exception("Service timeout")
    mock_chunker_cls.return_value = mock_chunker
    
    with pytest.raises(Exception) as excinfo:
        semantic_chunk("Sample text")
    assert "LiteLLM service timeout" in str(excinfo.value)
