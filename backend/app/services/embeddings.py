import os
import logging
import requests
from typing import List, Optional, Callable

# Point to Ollama directly
OLLAMA_URL = os.getenv("LITELLM_PROXY_URL", "http://ollama:11434")

logger = logging.getLogger(__name__)

def generate_embeddings(
    texts: List[str], 
    batch_size: int = 32, 
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[List[float]]:
    """
    Generate embeddings for a list of strings using direct Ollama API.
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
            # Call Ollama /api/embed directly
            response = requests.post(
                f"{OLLAMA_URL}/api/embed",
                json={
                    "model": "nomic-embed-text",
                    "input": batch
                },
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                response.raise_for_status()
                
            data = response.json()
            batch_embeddings = data.get("embeddings", [])
            
            if not batch_embeddings:
                logger.error(f"Ollama returned no embeddings: {data}")
                raise Exception("Ollama returned no embeddings")
                
            all_embeddings.extend(batch_embeddings)
            
            if progress_callback:
                progress_callback(len(all_embeddings), total_texts)
                
        except Exception as e:
            logger.error(f"Error during embedding: {str(e)}")
            raise e

    return all_embeddings
