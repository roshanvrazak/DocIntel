"""
Context management utilities for LLM calls.

Gemini 1.5 Pro supports a 1M-token context window, but sending very large
contexts is slow and expensive. This module enforces a configurable character
budget so that the worst-case prompt stays within a safe limit regardless of
how many or how large the uploaded documents are.

Approach: rough heuristic of ~4 characters per token (good enough for English
prose; no external tokenizer dependency required).
"""
import logging
from typing import Any, Dict, List

from backend.app.config import MAX_CONTEXT_CHARS

logger = logging.getLogger(__name__)

_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate token count using the 4 chars/token heuristic."""
    return len(text) // _CHARS_PER_TOKEN


def truncate_context(
    chunks: List[Dict[str, Any]],
    prefix: str = "",
    max_chars: int = MAX_CONTEXT_CHARS,
) -> tuple[List[Dict[str, Any]], bool]:
    """
    Return the largest prefix of *chunks* whose combined character count
    (including *prefix* overhead) fits within *max_chars*.

    Chunks are assumed to be ordered by relevance (highest first). Lower-ranked
    chunks are dropped first.

    Returns:
        (kept_chunks, was_truncated)
    """
    budget = max_chars - len(prefix)
    if budget <= 0:
        logger.warning("Context prefix alone exceeds MAX_CONTEXT_CHARS=%d; returning empty chunks", max_chars)
        return [], True

    kept: List[Dict[str, Any]] = []
    used = 0
    for chunk in chunks:
        content = chunk.get("content", "")
        # +2 for separator overhead ("\n\n" between chunks)
        chunk_chars = len(content) + 2
        if used + chunk_chars > budget:
            break
        kept.append(chunk)
        used += chunk_chars

    was_truncated = len(kept) < len(chunks)
    if was_truncated:
        logger.info(
            "Context truncated: kept %d/%d chunks (%d chars, est. %d tokens) within budget of %d chars",
            len(kept), len(chunks), used, estimate_tokens(prefix) + used // _CHARS_PER_TOKEN, max_chars,
        )
    return kept, was_truncated


def truncate_text(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> tuple[str, bool]:
    """
    Truncate a raw string to *max_chars*. Used for summarise agent where content
    is already joined into a single string.

    Returns:
        (truncated_text, was_truncated)
    """
    if len(text) <= max_chars:
        return text, False
    truncated = text[:max_chars]
    logger.info(
        "Text truncated from %d to %d chars (est. %d tokens)",
        len(text), max_chars, estimate_tokens(truncated),
    )
    return truncated, True
