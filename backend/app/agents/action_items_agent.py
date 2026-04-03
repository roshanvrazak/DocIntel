"""
Action Items agent — extracts tasks, decisions, and commitments from documents.

Identifies:
  - Explicit action items and tasks
  - Owners / responsible parties
  - Deadlines and due dates
  - Decisions made
  - Follow-up items and open questions

Useful for meeting notes, project briefs, reports, and proposal documents.
"""
import litellm
import logging
from typing import Any, Dict, List
from sqlalchemy import select

from .state import DocIntelState
from backend.app.models.document import Chunk, Document
from backend.app.db.session import async_session
from backend.app.services.retriever import HybridRetriever
from backend.app.services.context_manager import truncate_context
from backend.app.config import LITELLM_PROXY_URL, LITELLM_API_KEY, RETRIEVER_TOP_K

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert at extracting action items and decisions from documents.
Given document context, identify and structure all actionable content.
Return a well-formatted markdown report with these sections (omit sections with no data):

## Action Items
| # | Task | Owner | Deadline | Priority |
|---|------|-------|----------|----------|
List every concrete task. Use "Unassigned" if no owner is specified and "TBD" if no deadline.

## Decisions Made
- Bullet list of decisions or agreements reached in the documents.

## Open Questions
- Unresolved questions or items requiring further discussion.

## Follow-ups
- Items that require a future check-in or dependency resolution.

Be precise and comprehensive. Extract ONLY content present in the provided context.
If a section has no relevant content, omit it."""


async def action_items_node(state: DocIntelState) -> DocIntelState:
    """Extracts action items, decisions, and follow-ups from document chunks."""
    query = state.get("query", "")
    doc_ids = state.get("documents", [])

    logger.info("Action items node processing query: %s for %d documents", query[:80], len(doc_ids))

    draft_response: str = "I encountered an error while extracting action items. Please try again."
    retrieved_chunks: List[Dict[str, Any]] = []

    try:
        search_query = query or "action items tasks decisions assignments deadlines follow-up"
        async with async_session() as session:
            retriever = HybridRetriever(session)
            results = await retriever.hybrid_search(search_query, top_k=RETRIEVER_TOP_K * 2, document_ids=doc_ids)

            doc_ids_set = {r["chunk"].document_id for r in results}
            doc_stmt = select(Document).where(Document.id.in_(doc_ids_set))
            doc_result = await session.execute(doc_stmt)
            doc_map = {doc.id: doc.filename for doc in doc_result.scalars().all()}

        all_chunks_meta: List[Dict[str, Any]] = []
        for res in results:
            chunk = res["chunk"]
            filename = doc_map.get(chunk.document_id, "Unknown")
            all_chunks_meta.append({
                "content": chunk.content,
                "document_id": str(chunk.document_id),
                "chunk_id": str(chunk.id),
                "filename": filename,
                "page_number": chunk.page_number or 1,
                "score": res.get("rerank_score", res.get("score", 0)),
            })

        prefix_chars = len(_SYSTEM_PROMPT) + len(search_query) + 50
        retrieved_chunks, was_truncated = truncate_context(all_chunks_meta, prefix_chars=prefix_chars)

        context_parts = [
            f"[{i+1}] Source: {c['filename']} (page {c['page_number']})\n{c['content']}"
            for i, c in enumerate(retrieved_chunks)
        ]
        context_text = "\n\n".join(context_parts)
        if was_truncated:
            context_text += "\n\n[Note: some chunks omitted to fit context limit.]"

        user_content = f"Documents to analyse:\n\n{context_text}"
        if query:
            user_content += f"\n\nAdditional focus: {query}"

        response = await litellm.acompletion(
            model="gemini/gemini-1.5-pro",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            api_base=LITELLM_PROXY_URL,
            api_key=LITELLM_API_KEY,
            temperature=0.1,
            max_tokens=3000,
        )
        draft_response = response.choices[0].message.content
        if response.choices[0].finish_reason == "length":
            draft_response += "\n\n[Output truncated due to length constraints.]"

    except Exception as e:
        logger.error("Error in action_items_node: %s", e, exc_info=True)

    return {"draft_response": draft_response, "retrieved_chunks": retrieved_chunks}
