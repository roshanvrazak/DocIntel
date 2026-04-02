import logging
from .state import DocIntelState
from backend.app.services.retriever import HybridRetriever
from backend.app.models.document import Document
from backend.app.db.session import async_session
from backend.app.config import LITELLM_PROXY_URL, RETRIEVER_TOP_K
from sqlalchemy import select
import litellm

logger = logging.getLogger(__name__)


async def compare_node(state: DocIntelState) -> DocIntelState:
    """
    Cross-document comparison using targeted hybrid retrieval + Gemini 1.5 Pro.
    Replaces the previous full-chunk-fetch approach with per-query retrieval.
    """
    query = state.get("query", "Compare these documents.")
    doc_ids = state.get("documents", [])

    logger.info("Comparison node processing query: %s for %d documents", query[:80], len(doc_ids))

    if not doc_ids:
        return {"draft_response": "No documents provided for comparison."}

    try:
        async with async_session() as session:
            # Use hybrid search to retrieve the most relevant chunks across all docs
            retriever = HybridRetriever(session)
            results = await retriever.hybrid_search(
                query, top_k=RETRIEVER_TOP_K * len(doc_ids), document_ids=doc_ids
            )

            # Fetch document filenames
            doc_ids_set = {r["chunk"].document_id for r in results}
            doc_stmt = select(Document).where(Document.id.in_(doc_ids_set))
            doc_result = await session.execute(doc_stmt)
            doc_map = {doc.id: doc.filename for doc in doc_result.scalars().all()}

        # Group retrieved chunks by document
        doc_chunks: dict = {}
        retrieved_chunks = []
        for res in results:
            chunk = res["chunk"]
            filename = doc_map.get(chunk.document_id, str(chunk.document_id))
            doc_chunks.setdefault(filename, []).append(chunk.content)
            retrieved_chunks.append({
                "content": chunk.content,
                "document_id": str(chunk.document_id),
                "chunk_id": str(chunk.id),
                "filename": filename,
                "page_number": chunk.page_number or 1,
                "score": res.get("rerank_score", res.get("score", 0)),
            })

        combined_docs = "\n\n".join(
            [f"--- Document: {fname} ---\n" + "\n".join(chunks)
             for fname, chunks in doc_chunks.items()]
        )

        system_prompt = (
            "Compare the provided documents: identify key dimensions of comparison, "
            "build a markdown comparison table, highlight contradictions, and synthesize differences."
        )

        response = await litellm.acompletion(
            model="gemini/gemini-1.5-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}\n\nDocuments:\n{combined_docs}"},
            ],
            api_base=LITELLM_PROXY_URL,
            api_key="sk-dummy",
            temperature=0.2,
            max_tokens=3000,
        )

        comparison = response.choices[0].message.content
        if response.choices[0].finish_reason == "length":
            comparison += "\n\n[Comparison truncated due to length constraints.]"

        return {"draft_response": comparison, "retrieved_chunks": retrieved_chunks}

    except Exception as e:
        logger.error("Error in compare_node: %s", str(e), exc_info=True)
        return {"draft_response": "I encountered an error while comparing the documents. Please try again."}
