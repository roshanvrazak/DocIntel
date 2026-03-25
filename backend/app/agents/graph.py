from typing import Literal
from langgraph.graph import StateGraph, END
from .state import DocIntelState
from .router import router_node
from .rag_agent import rag_node
from .summarise_agent import summarise_node
from .compare_agent import compare_node

async def validator(state: DocIntelState) -> DocIntelState:
    """
    Validates the response for faithfulness and relevance.
    Placeholder implementation.
    """
    retry_count = state.get("retry_count", 0) + 1
    # Mock a high faithfulness score for now to avoid retries in placeholder mode
    return {"faithfulness_score": 0.9, "retry_count": retry_count}

# Initialize the StateGraph with DocIntelState
workflow = StateGraph(DocIntelState)

# Add nodes to the graph
workflow.add_node("router", router_node)
workflow.add_node("rag_agent", rag_node)
workflow.add_node("summarise_agent", summarise_node)
workflow.add_node("compare_agent", compare_node)
workflow.add_node("validator", validator)

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
def should_retry(state: DocIntelState) -> Literal["router", "__end__"]:
    """
    Determines if the flow should retry based on the validation score.
    In the new graph, we retry from the router to allow re-classification or refined queries.
    """
    score = state.get("faithfulness_score", 0)
    retry_count = state.get("retry_count", 0)
    
    # If score is high enough or we reached max retries, end the process
    if (score and score > 0.8) or retry_count >= 3:
        return END
    
    # Otherwise, try from the beginning (could be more sophisticated in future)
    return "router"

workflow.add_conditional_edges(
    "validator",
    should_retry,
    {
        "router": "router",
        END: END
    }
)

# Compile the graph
graph = workflow.compile()
