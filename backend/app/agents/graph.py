from typing import Literal
from functools import wraps
from opentelemetry import trace
from langgraph.graph import StateGraph, END

from .state import DocIntelState
from .router import router_node
from .rag_agent import rag_node
from .summarise_agent import summarise_node
from .compare_agent import compare_node
from .extract_agent import extract_node
from .action_items_agent import action_items_node
from .timeline_agent import timeline_node
from .validator import validator_node

tracer = trace.get_tracer(__name__)


def trace_node(node_name: str):
    """Wraps a LangGraph node function in an OpenTelemetry span."""
    def decorator(node_func):
        @wraps(node_func)
        async def wrapper(state: DocIntelState):
            with tracer.start_as_current_span(f"node.{node_name}") as span:
                span.set_attribute("langgraph.node", node_name)
                if "query" in state:
                    span.set_attribute("docintel.query", state["query"])
                if "intent" in state:
                    span.set_attribute("docintel.intent", state["intent"])
                result = await node_func(state)
                if isinstance(result, dict) and "error" in result:
                    span.set_status(trace.status.Status(trace.status.StatusCode.ERROR))
                    span.record_exception(Exception(result["error"]))
                return result
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------

workflow = StateGraph(DocIntelState)

workflow.add_node("router",           trace_node("router")(router_node))
workflow.add_node("rag_agent",        trace_node("rag_agent")(rag_node))
workflow.add_node("summarise_agent",  trace_node("summarise_agent")(summarise_node))
workflow.add_node("compare_agent",    trace_node("compare_agent")(compare_node))
workflow.add_node("extract_agent",    trace_node("extract_agent")(extract_node))
workflow.add_node("action_items_agent", trace_node("action_items_agent")(action_items_node))
workflow.add_node("timeline_agent",   trace_node("timeline_agent")(timeline_node))
workflow.add_node("validator",        trace_node("validator")(validator_node))

workflow.set_entry_point("router")


def route_intent(
    state: DocIntelState,
) -> Literal["rag_agent", "summarise_agent", "compare_agent", "extract_agent", "action_items_agent", "timeline_agent"]:
    """Routes to the appropriate specialised agent based on classified intent."""
    intent = state.get("intent", "qa")
    if intent in ("summarise", "summarise_each"):
        return "summarise_agent"
    if intent in ("compare", "contradict"):
        return "compare_agent"
    if intent == "extract":
        return "extract_agent"
    if intent == "action_items":
        return "action_items_agent"
    if intent == "timeline":
        return "timeline_agent"
    # Default: qa, search, and any unrecognised intent → RAG
    return "rag_agent"


workflow.add_conditional_edges(
    "router",
    route_intent,
    {
        "rag_agent":           "rag_agent",
        "summarise_agent":     "summarise_agent",
        "compare_agent":       "compare_agent",
        "extract_agent":       "extract_agent",
        "action_items_agent":  "action_items_agent",
        "timeline_agent":      "timeline_agent",
    },
)

# All specialised agents feed into the validator
for _agent in ("rag_agent", "summarise_agent", "compare_agent", "extract_agent", "action_items_agent", "timeline_agent"):
    workflow.add_edge(_agent, "validator")


def should_retry(state: DocIntelState) -> bool:
    """Retry if faithfulness score is below threshold and retries remain."""
    score = state.get("faithfulness_score")
    retry_count = state.get("retry_count", 0)
    from backend.app.config import FAITHFULNESS_THRESHOLD, VALIDATOR_MAX_RETRIES
    return score is not None and score < FAITHFULNESS_THRESHOLD and retry_count < VALIDATOR_MAX_RETRIES


workflow.add_conditional_edges(
    "validator",
    should_retry,
    {True: "router", False: END},
)

graph = workflow.compile()
