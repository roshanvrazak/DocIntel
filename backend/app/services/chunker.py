import os
from typing import List, Optional
from langchain_experimental.text_splitter import SemanticChunker
from langchain_litellm import LiteLLMEmbeddings
import logging

logger = logging.getLogger(__name__)

class ChunkerService:
    _instance: Optional['ChunkerService'] = None
    _embeddings: Optional[LiteLLMEmbeddings] = None
    _text_splitter: Optional[SemanticChunker] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChunkerService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self):
        """Initializes the embeddings and text splitter once."""
        try:
            # Configurable via environment variables
            self.api_base = os.getenv("LITELLM_PROXY_URL", "http://ollama:11434")
            self.model_name = os.getenv("EMBEDDING_MODEL_NAME", "ollama/nomic-embed-text")
            
            logger.info(f"Initializing ChunkerService with model={self.model_name}, api_base={self.api_base}")
            
            self._embeddings = LiteLLMEmbeddings(
                model=self.model_name,
                api_base=self.api_base
            )
            
            # Initialize the semantic chunker
            self._text_splitter = SemanticChunker(self._embeddings)
        except Exception as e:
            logger.error(f"Failed to initialize ChunkerService: {str(e)}")
            # We don't raise here to allow for lazy re-initialization if needed, 
            # but methods will check if initialized.
            self._embeddings = None
            self._text_splitter = None

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunks text semantically using cached LiteLLM/Ollama embeddings.
        """
        if not self._text_splitter:
            # Try to re-initialize if it failed before
            self._init_service()
            if not self._text_splitter:
                raise Exception("ChunkerService is not initialized. Check LiteLLM proxy connection.")

        try:
            # Split the text into semantic chunks
            chunks = self._text_splitter.split_text(text)
            return chunks
        except Exception as e:
            logger.error(f"Error during semantic chunking: {str(e)}")
            # Handle specific LiteLLM errors if possible (e.g., timeout, connection)
            if "timeout" in str(e).lower():
                raise Exception(f"LiteLLM service timeout: {str(e)}")
            elif "connection" in str(e).lower() or "refused" in str(e).lower():
                raise Exception(f"LiteLLM service connection failure: {str(e)}")
            raise Exception(f"Failed to chunk text: {str(e)}")

# For backward compatibility and ease of use
def semantic_chunk(text: str) -> List[str]:
    service = ChunkerService()
    return service.chunk_text(text)
