import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.embeddings import generate_embeddings
from litellm.exceptions import ServiceUnavailableError, Timeout

@patch("litellm.embedding")
def test_generate_embeddings(mock_embedding):
    # Mock return value
    mock_response = MagicMock()
    mock_response.data = [
        {"embedding": [0.1, 0.2, 0.3]},
        {"embedding": [0.4, 0.5, 0.6]}
    ]
    mock_embedding.return_value = mock_response

    texts = ["hello", "world"]
    embeddings = generate_embeddings(texts)

    assert len(embeddings) == 2
    assert embeddings[0] == [0.1, 0.2, 0.3]
    assert embeddings[1] == [0.4, 0.5, 0.6]
    
    # Ensure it's called with the correct model and timeout
    mock_embedding.assert_called_once()
    assert mock_embedding.call_args[1]["model"] == "nomic-embed-text"
    assert mock_embedding.call_args[1]["timeout"] == 60

def test_generate_embeddings_empty():
    assert generate_embeddings([]) == []

@patch("litellm.embedding")
def test_generate_embeddings_timeout(mock_embedding):
    mock_embedding.side_effect = Timeout("Service timeout", model="nomic-embed-text", llm_provider="ollama")
    
    with pytest.raises(Timeout):
        generate_embeddings(["test"])

@patch("litellm.embedding")
def test_generate_embeddings_service_unavailable(mock_embedding):
    mock_embedding.side_effect = ServiceUnavailableError("Service unavailable", model="nomic-embed-text", llm_provider="ollama")
    
    with pytest.raises(ServiceUnavailableError):
        generate_embeddings(["test"])

@patch("litellm.embedding")
def test_generate_embeddings_batching(mock_embedding):
    # Mock return value for two batches
    mock_response1 = MagicMock()
    mock_response1.data = [{"embedding": [0.1]} for _ in range(32)]
    
    mock_response2 = MagicMock()
    mock_response2.data = [{"embedding": [0.2]} for _ in range(8)]
    
    mock_embedding.side_effect = [mock_response1, mock_response2]

    texts = ["text"] * 40
    embeddings = generate_embeddings(texts, batch_size=32)

    assert len(embeddings) == 40
    assert mock_embedding.call_count == 2
    assert len(embeddings[0]) == 1
    assert embeddings[0] == [0.1]
    assert embeddings[39] == [0.2]

@patch("litellm.embedding")
def test_generate_embeddings_progress_callback(mock_embedding):
    def side_effect(*args, **kwargs):
        input_texts = kwargs.get('input', [])
        m = MagicMock()
        m.data = [{"embedding": [0.1]} for _ in range(len(input_texts))]
        return m
    mock_embedding.side_effect = side_effect
    
    callback = MagicMock()
    generate_embeddings(["text"] * 10, batch_size=5, progress_callback=callback)
    
    assert callback.call_count == 2
    callback.assert_any_call(5, 10)
    callback.assert_any_call(10, 10)
