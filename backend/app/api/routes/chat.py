from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import logging
import asyncio
import uuid
from backend.app.agents.graph import graph

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    query: str
    action: Optional[str] = "qa"
    doc_ids: Optional[List[str]] = []

@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to interact with the document intelligence agents via LangGraph.
    Streams the final response.
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="Query is required.")

    # Convert string IDs to UUIDs to match DocIntelState and database models
    doc_uuids = []
    for d_id in (request.doc_ids or []):
        try:
            doc_uuids.append(uuid.UUID(d_id))
        except ValueError:
            logger.warning(f"Invalid UUID provided: {d_id}")
            continue

    # Prepare the initial state
    initial_state = {
        "query": request.query,
        "documents": doc_uuids,
        "intent": request.action if request.action != "qa" else None,
        "retry_count": 0
    }

    async def generate_response():
        try:
            # We use astream to get updates from the graph
            # For this simple prototype, we'll stream the final response after completion
            # In a more advanced version, we could stream partial results from nodes
            
            result = await graph.ainvoke(initial_state)
            
            final_response = result.get("final_response") or result.get("draft_response")
            
            if not final_response:
                yield "I'm sorry, I couldn't generate a response for that query."
                return

            # Stream the response word by word to simulate "typing"
            # In a real app, you might stream tokens directly from the LLM
            words = final_response.split(" ")
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                await asyncio.sleep(0.02) # Small delay for smooth streaming

        except Exception as e:
            logger.error(f"Error in chat_endpoint: {str(e)}", exc_info=True)
            yield f"**Error:** An internal error occurred while processing your request: {str(e)}"

    return StreamingResponse(generate_response(), media_type="text/plain")
