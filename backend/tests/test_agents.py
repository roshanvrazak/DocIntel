import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.agents.state import DocIntelState
from backend.app.agents.graph import graph
from backend.app.agents.router import router_node


def _make_llm_response(content: str) -> MagicMock:
    return MagicMock(choices=[MagicMock(message=MagicMock(content=content))])


def _base_state(query: str = "test query", intent: str | None = None) -> DocIntelState:
    return {
        "query": query,
        "documents": [uuid.uuid4()],
        "intent": intent,
        "retrieved_chunks": [],
        "draft_response": None,
        "faithfulness_score": None,
        "final_response": None,
        "retry_count": 0,
    }


@pytest.mark.asyncio
async def test_graph_initialization():
    """Verify that the LangGraph is correctly compiled."""
    assert graph is not None
    assert graph.nodes is not None
    assert "router" in graph.nodes
    assert "rag_agent" in graph.nodes
    assert "validator" in graph.nodes


# --- Router: exact intent matches ---

@pytest.mark.asyncio
@pytest.mark.parametrize("llm_output,expected_intent", [
    ("summarise", "summarise"),
    ("summarise_each", "summarise_each"),
    ("compare", "compare"),
    ("contradict", "contradict"),
    ("extract", "extract"),
    ("qa", "qa"),
    ("action_items", "action_items"),
    ("timeline", "timeline"),
])
async def test_router_exact_intents(llm_output: str, expected_intent: str):
    with patch("backend.app.agents.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response(llm_output)
        result = await router_node(_base_state("some query"))
        assert result["intent"] == expected_intent


@pytest.mark.asyncio
async def test_router_intent_with_markdown_noise():
    """LLM sometimes returns intent with markdown punctuation."""
    with patch("backend.app.agents.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response('"summarise".')
        result = await router_node(_base_state())
        assert result["intent"] == "summarise"


@pytest.mark.asyncio
async def test_router_partial_match_fallback():
    """Unknown intent containing a valid word should match via partial check."""
    with patch("backend.app.agents.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response("please_summarise_this")
        result = await router_node(_base_state())
        assert result["intent"] == "summarise"


@pytest.mark.asyncio
async def test_router_unknown_intent_defaults_to_qa():
    """Completely unrecognised intent should fall back to 'qa'."""
    with patch("backend.app.agents.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response("dance")
        result = await router_node(_base_state())
        assert result["intent"] == "qa"


@pytest.mark.asyncio
async def test_router_llm_error_defaults_to_qa():
    """When the LLM call raises, router should silently fall back to 'qa'."""
    with patch("backend.app.agents.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("LLM unavailable")
        result = await router_node(_base_state())
        assert result["intent"] == "qa"


@pytest.mark.asyncio
async def test_router_preserves_existing_intent():
    """If intent is already set in state, router should still call LLM and return its result."""
    with patch("backend.app.agents.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response("compare")
        state = _base_state(intent="qa")  # pre-set intent
        result = await router_node(state)
        assert result["intent"] == "compare"


@pytest.mark.asyncio
async def test_router_empty_query_defaults_to_qa():
    """Empty query should not crash and should fall back to 'qa'."""
    with patch("backend.app.agents.router.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response("")
        result = await router_node(_base_state(query=""))
        assert result["intent"] == "qa"


# --- State structure ---

def test_state_structure():
    """Verify the DocIntelState TypedDict accepts the expected keys."""
    state: DocIntelState = {
        "query": "test",
        "documents": [uuid.uuid4()],
        "intent": "qa",
        "retrieved_chunks": [],
        "draft_response": "response",
        "faithfulness_score": 0.9,
        "final_response": "response",
        "retry_count": 0,
    }
    assert state["query"] == "test"
    assert len(state["documents"]) == 1
    assert state["faithfulness_score"] == 0.9
