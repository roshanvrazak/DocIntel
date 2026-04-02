import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from backend.app.db.session import get_session
from backend.app.models.document import Document, Chunk
from backend.app.worker import process_document
from backend.app.api.dependencies.auth import verify_api_key
from backend.app.api.dependencies.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "backend/uploads")


@router.get("/api/documents", dependencies=[Depends(verify_api_key)])
async def list_documents(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_session),
):
    """List all documents with pagination."""
    limit = min(limit, 100)
    offset = (page - 1) * limit

    total: int = await db.scalar(select(func.count(Document.id))) or 0

    stmt = select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return {
        "documents": [
            {
                "id": str(doc.id),
                "filename": doc.filename,
                "status": doc.status,
                "created_at": doc.created_at.isoformat(),
            }
            for doc in docs
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),  # ceiling division
    }


@router.delete("/api/documents/{doc_id}", dependencies=[Depends(verify_api_key)])
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Delete a document and all its associated chunks."""
    try:
        import uuid
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    doc = await db.get(Document, uid)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove file from disk (best-effort)
    import glob as glob_mod
    pattern = os.path.join(UPLOAD_DIR, f"{doc_id}_*")
    for path in glob_mod.glob(pattern):
        try:
            os.remove(path)
            logger.info("Deleted file: %s", path)
        except OSError as e:
            logger.warning("Could not delete file %s: %s", path, e)

    await db.delete(doc)
    await db.commit()
    logger.info("Deleted document %s", doc_id)
    return {"deleted": doc_id}


@router.post("/api/documents/{doc_id}/reprocess", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def reprocess_document(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Re-trigger the ingestion pipeline for an existing document."""
    try:
        import uuid
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    doc = await db.get(Document, uid)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Verify the source file still exists
    import glob as glob_mod
    pattern = os.path.join(UPLOAD_DIR, f"{doc_id}_*")
    files = glob_mod.glob(pattern)
    if not files:
        raise HTTPException(
            status_code=409,
            detail="Source file not found on disk. Please re-upload the document.",
        )

    # Delete stale chunks, reset status
    await db.execute(delete(Chunk).where(Chunk.document_id == uid))
    doc.status = "uploaded"
    await db.commit()

    process_document.delay(doc_id)
    logger.info("Reprocessing triggered for document %s", doc_id)
    return {"reprocessing": doc_id, "status": "uploaded"}
