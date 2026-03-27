import os
from typing import List, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

class ChunkerService:
    _instance: Optional['ChunkerService'] = None
    _text_splitter: Optional[RecursiveCharacterTextSplitter] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChunkerService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self):
        """Initializes the text splitter once."""
        try:
            # Simple recursive character splitting is more robust for a prototype
            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                is_separator_regex=False,
            )
            logger.info("Initialized ChunkerService with RecursiveCharacterTextSplitter")
        except Exception as e:
            logger.error(f"Failed to initialize ChunkerService: {str(e)}")
            self._text_splitter = None

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunks text using RecursiveCharacterTextSplitter.
        """
        if not self._text_splitter:
            self._init_service()
            if not self._text_splitter:
                raise Exception("ChunkerService is not initialized.")

        try:
            chunks = self._text_splitter.split_text(text)
            return chunks
        except Exception as e:
            logger.error(f"Error during chunking: {str(e)}")
            raise Exception(f"Failed to chunk text: {str(e)}")

# For backward compatibility and ease of use
def semantic_chunk(text: str) -> List[str]:
    service = ChunkerService()
    return service.chunk_text(text)
