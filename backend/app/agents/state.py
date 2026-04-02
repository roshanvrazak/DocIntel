from typing import List, Dict, Any, Optional, TypedDict
from uuid import UUID


class DocIntelState(TypedDict):
    """Represents the state of the DocIntel agentic graph."""
    query: str
    documents: List[UUID]
    intent: Optional[str]
    retrieved_chunks: List[Dict[str, Any]]
    draft_response: Optional[str]
    faithfulness_score: Optional[float]
    answer_relevancy_score: Optional[float]
    final_response: Optional[str]
    retry_count: int
