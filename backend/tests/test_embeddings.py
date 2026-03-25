from unittest.mock import patch, MagicMock
from backend.app.services.embeddings import generate_embeddings

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
    
    # Ensure it's called with the correct model
    mock_embedding.assert_called_once()
    assert mock_embedding.call_args[1]["model"] == "nomic-embed-text"
