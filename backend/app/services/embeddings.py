import os
from typing import List
import litellm

# Point to LiteLLM Proxy
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://litellm:4000")

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of strings using LiteLLM proxy to Ollama.
    Uses 'nomic-embed-text' model.
    """
    if not texts:
        return []

    response = litellm.embedding(
        model="nomic-embed-text",
        input=texts,
        api_base=LITELLM_PROXY_URL,
        # We might need an API key if the proxy requires one, 
        # but usually local proxies don't or use a dummy one.
        api_key="sk-dummy" 
    )

    # litellm.embedding returns an EmbeddingResponse object
    # The embeddings are in response.data which is a list of objects containing 'embedding'
    return [item["embedding"] for item in response.data]
