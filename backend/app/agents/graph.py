from typing import Literal, Union
from functools import wraps
from opentelemetry import trace
from langgraph.graph import StateGraph, END
from .state import DocIntelState
from .router import router_node
from .rag_agent import rag_node
from .summarise_agent import summarise_node
from .compare_agent import compare_node
from .validator import validator_node

# Initialize OpenTelemetry Tracer
tracer = trace.get_tracer(__name__)

def trace_node(node_name: str):
    """
    Decorator to wrap LangGraph nodes in OpenTelemetry spans.
    """
    def decorator(node_func):
        @wraps(node_func)
        async def wrapper(state: DocIntelState):
            with tracer.start_as_current_span(f"node.{node_name}") as span:
                span.set_attribute("langgraph.node", node_name)
                # If there's a query or intent, add it as attribute
                if "query" in state:
                    span.set_attribute("docintel.query", state["query"])
                if "intent" in state:
                    span.set_attribute("docintel.intent", state["intent"])
                
                result = await node_func(state)
                
                # Check for errors in result (if any)
                if isinstance(result, dict) and "error" in result:
                    span.set_status(trace.status.Status(trace.status.StatusCode.ERROR))
                    span.record_exception(Exception(result["error"]))
                
                return result
        return wrapper
    return decorator

# Initialize the StateGraph with DocIntelState
workflow = StateGraph(DocIntelState)

# Add nodes to the graph with tracing
workflow.add_node("router", trace_node("router")(router_node))
workflow.add_node("rag_agent", trace_node("rag_agent")(rag_node))
workflow.add_node("summarise_agent", trace_node("summarise_agent")(summarise_node))
workflow.add_node("compare_agent", trace_node("compare_agent")(compare_node))
workflow.add_node("validator", trace_node("validator")(validator_node))

# Set the entry point
workflow.set_entry_point("router")

# Define conditional edges from router based on intent
def route_intent(state: DocIntelState) -> Literal["rag_agent", "summarise_agent", "compare_agent"]:
    """
    Routes the workflow to specialized agents based on classified intent.
    """
    intent = state.get("intent", "qa")
    if intent in ["summarise", "summarise_each"]:
        return "summarise_agent"
    elif intent in ["compare", "contradict"]:
        return "compare_agent"
    # Default to RAG for QA, extract, action_items, timeline, etc. for now
    return "rag_agent"

workflow.add_conditional_edges(
    "router",
    route_intent,
    {
        "rag_agent": "rag_agent",
        "summarise_agent": "summarise_agent",
        "compare_agent": "compare_agent"
    }
)

# Connect specialized agents to validator
workflow.add_edge("rag_agent", "validator")
workflow.add_edge("summarise_agent", "validator")
workflow.add_edge("compare_agent", "validator")

# Define conditional edge for self-correction loop from validator
def should_retry(state: DocIntelState) -> bool:
    """
    Determines if the flow should retry based on the validation score.
    Returns True if a retry is needed, False otherwise.
    """
    score = state.get("faithfulness_score")
    retry_count = state.get("retry_count", 0)
    
    # Retry if score is low and we haven't reached max retries
    # Note: score can be 0.0, so we check if it is not None
    if score is not None and score < 0.8 and retry_count < 3:
        return True
    
    return False

workflow.add_conditional_edges(
    "validator",
    should_retry,
    {
        True: "router",
        False: END
    }
)

# Compile the graph
graph = workflow.compile()
