import os
import logging
from typing import List, Optional, Callable
import litellm
from litellm.exceptions import ServiceUnavailableError, APIError, Timeout

# Point to LiteLLM Proxy or directly to Ollama
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://ollama:11434")

logger = logging.getLogger(__name__)

def generate_embeddings(
    texts: List[str], 
    batch_size: int = 32, 
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[List[float]]:
    """
    Generate embeddings for a list of strings using LiteLLM proxy to Ollama.
    Uses 'nomic-embed-text' model.
    Implements batching and error handling.
    """
    if not texts:
        return []

    all_embeddings = []
    total_texts = len(texts)

    for i in range(0, total_texts, batch_size):
        batch = texts[i : i + batch_size]
        try:
            response = litellm.embedding(
                model="ollama/nomic-embed-text",
                input=batch,
                api_base=LITELLM_PROXY_URL,
                api_key="sk-dummy",
                timeout=60
            )
            
            batch_embeddings = [item["embedding"] for item in response.data]
            all_embeddings.extend(batch_embeddings)
            
            if progress_callback:
                progress_callback(len(all_embeddings), total_texts)
                
        except (ServiceUnavailableError, APIError, Timeout) as e:
            logger.error(f"LiteLLM error during embedding: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during embedding: {str(e)}")
            raise e

    return all_embeddings
