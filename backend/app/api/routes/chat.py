import os
import re
import logging
import asyncio
import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional
from backend.app.agents.graph import graph
from backend.app.api.dependencies.auth import verify_api_key
from backend.app.api.dependencies.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "2000"))

# Common prompt injection patterns to block
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(previous|all|above|prior)\s+(instructions?|prompts?|context)|"
    r"disregard\s+(previous|all|above|prior)\s+(instructions?|prompts?|context)|"
    r"you\s+are\s+now\s+|new\s+persona|act\s+as\s+(?!an?\s+expert)|"
    r"system\s*:\s*you|<\s*system\s*>)",
    re.IGNORECASE,
)


class ChatRequest(BaseModel):
    query: str
    action: Optional[str] = "qa"
    doc_ids: Optional[List[str]] = []

    @field_validator("query")
    @classmethod
    def query_must_be_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty.")
        if len(v) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query exceeds the maximum length of {MAX_QUERY_LENGTH} characters.")
        if _INJECTION_PATTERNS.search(v):
            raise ValueError("Query contains disallowed content.")
        return v


@router.post("/api/chat", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def chat_endpoint(request: Request, body: ChatRequest):
    """Streams a response from the document intelligence agents."""
    doc_uuids = []
    for d_id in (body.doc_ids or []):
        try:
            doc_uuids.append(uuid.UUID(d_id))
        except ValueError:
            logger.warning("Invalid UUID provided: %s", d_id)

    initial_state = {
        "query": body.query,
        "documents": doc_uuids,
        "intent": body.action if body.action != "qa" else None,
        "retry_count": 0,
    }

    async def generate_response():
        try:
            result = await graph.ainvoke(initial_state)
            final_response = result.get("final_response") or result.get("draft_response")

            if not final_response:
                yield "I'm sorry, I couldn't generate a response for that query."
                return

            words = final_response.split(" ")
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                await asyncio.sleep(0.02)

        except Exception:
            logger.error("Unhandled error in chat_endpoint", exc_info=True)
            yield "An internal error occurred while processing your request."

    return StreamingResponse(generate_response(), media_type="text/plain")
