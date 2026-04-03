import litellm
import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy import select
from .state import DocIntelState
from backend.app.models.document import Chunk, Document
from backend.app.db.session import async_session
from backend.app.services.context_manager import truncate_text
from backend.app.config import LITELLM_PROXY_URL, LITELLM_API_KEY

logger = logging.getLogger(__name__)


async def summarise_node(state: DocIntelState) -> DocIntelState:
    """
    Performs document summarization using Gemini 1.5 Pro.
    Supports combined summary ('summarise') and individual summaries ('summarise_each').
    """
    intent = state.get("intent", "summarise")
    doc_ids = state.get("documents", [])

    logger.info("Summarization node processing intent: %s for %d documents", intent, len(doc_ids))

    if not doc_ids:
        return {"draft_response": "No documents provided for summarization."}

    try:
        all_docs_content: List[Dict[str, Any]] = []
        async with async_session() as session:
            doc_meta_stmt = select(Document).where(Document.id.in_(doc_ids))
            doc_meta_result = await session.execute(doc_meta_stmt)
            doc_metas = {doc.id: doc for doc in doc_meta_result.scalars().all()}

            chunk_stmt = (
                select(Chunk)
                .where(Chunk.document_id.in_(doc_ids))
                .order_by(Chunk.document_id, Chunk.page_number, Chunk.id)
            )
            chunk_result = await session.execute(chunk_stmt)
            all_chunks = chunk_result.scalars().all()

            # Group chunk objects by document_id (preserves originals for citations)
            doc_chunk_objs: Dict = {}
            for chunk in all_chunks:
                doc_chunk_objs.setdefault(chunk.document_id, []).append(chunk)

            for doc_id in doc_ids:
                filename = doc_metas[doc_id].filename if doc_id in doc_metas else str(doc_id)
                content = "\n".join(c.content for c in doc_chunk_objs.get(doc_id, []))
                all_docs_content.append({"id": doc_id, "filename": filename, "content": content})

        # Build retrieved_chunks from actual Chunk objects (avoids splitting multi-line chunks)
        retrieved_chunks: List[Dict[str, Any]] = []
        for chunk in all_chunks[:10 * len(doc_ids)]:
            if chunk.content.strip():
                retrieved_chunks.append({
                    "content": chunk.content,
                    "document_id": str(chunk.document_id),
                    "filename": doc_metas.get(chunk.document_id, type("_", (), {"filename": str(chunk.document_id)})()).filename,
                })

        if intent == "summarise_each":
            async def get_summary(doc: Dict[str, Any]) -> str:
                doc_content, truncated = truncate_text(doc["content"])
                suffix = "\n\n[Content truncated to fit context limit.]" if truncated else ""
                prompt = (
                    f"Summarize this document's purpose, key findings, and takeaways."
                    f"\n\nDocument: {doc['filename']}\n{doc_content}{suffix}"
                )
                response = await litellm.acompletion(
                    model="gemini/gemini-1.5-pro",
                    messages=[{"role": "user", "content": prompt}],
                    api_base=LITELLM_PROXY_URL,
                    api_key=LITELLM_API_KEY,
                    temperature=0.3,
                    max_tokens=2000,
                )
                llm_response = response.choices[0].message.content
                if response.choices[0].finish_reason == "length":
                    llm_response += "\n\n[Summary truncated.]"
                return f"### Summary of {doc['filename']}:\n{llm_response}"

            summaries = await asyncio.gather(*[get_summary(doc) for doc in all_docs_content])
            final_summary = "\n\n---\n\n".join(summaries)

        else:
            combined_raw = "\n\n".join(
                f"--- Document: {d['filename']} ---\n{d['content']}" for d in all_docs_content
            )
            combined_content, truncated = truncate_text(combined_raw)
            suffix = "\n\n[Some document content was omitted to fit the context limit.]" if truncated else ""
            prompt = (
                f"Summarize these documents. Identify key themes, findings, and takeaways."
                f"\n\nDocuments:\n{combined_content}{suffix}"
            )

            response = await litellm.acompletion(
                model="gemini/gemini-1.5-pro",
                messages=[{"role": "user", "content": prompt}],
                api_base=LITELLM_PROXY_URL,
                api_key=LITELLM_API_KEY,
                temperature=0.3,
                max_tokens=3000,
            )
            final_summary = response.choices[0].message.content
            if response.choices[0].finish_reason == "length":
                final_summary += "\n\n[Summary truncated due to length constraints.]"

        return {"draft_response": final_summary, "retrieved_chunks": retrieved_chunks}

    except Exception as e:
        logger.error("Error in summarise_node: %s", e, exc_info=True)
        return {"draft_response": "I encountered an error while summarizing the documents. Please try again."}
