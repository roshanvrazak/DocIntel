from typing import Literal
from langgraph.graph import StateGraph, END
from .state import DocIntelState

async def router(state: DocIntelState) -> DocIntelState:
    """
    Classifies the user's intent (e.g., summarise, compare, qa).
    Placeholder implementation.
    """
    return state

async def retriever(state: DocIntelState) -> DocIntelState:
    """
    Retrieves relevant document chunks based on the query and intent.
    Placeholder implementation.
    """
    return state

async def generator(state: DocIntelState) -> DocIntelState:
    """
    Generates a draft response using the retrieved chunks.
    Placeholder implementation.
    """
    return state

async def validator(state: DocIntelState) -> DocIntelState:
    """
    Validates the draft response for faithfulness and relevance.
    Placeholder implementation.
    """
    return state

# Initialize the StateGraph with DocIntelState
workflow = StateGraph(DocIntelState)

# Add nodes to the graph
workflow.add_node("router", router)
workflow.add_node("retriever", retriever)
workflow.add_node("generator", generator)
workflow.add_node("validator", validator)

# Set the entry point
workflow.set_entry_point("router")

# Define simple linear edges
workflow.add_edge("router", "retriever")
workflow.add_edge("retriever", "generator")
workflow.add_edge("generator", "validator")

# Define conditional edge for self-correction loop
def should_retry(state: DocIntelState) -> Literal["retriever", "__end__"]:
    """
    Determines if the generator should retry based on the validation score.
    """
    score = state.get("faithfulness_score", 0)
    retry_count = state.get("retry_count", 0)
    
    # If score is high enough or we reached max retries, end the process
    if (score and score > 0.8) or retry_count >= 3:
        return END
    
    # Otherwise, try retrieving again (perhaps with refined query in future)
    return "retriever"

workflow.add_conditional_edges(
    "validator",
    should_retry,
    {
        "retriever": "retriever",
        END: END
    }
)

# Compile the graph
graph = workflow.compile()
