import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session
from backend.app.models.document import Document
from backend.app.worker import process_document
from backend.app.api.dependencies.auth import verify_api_key
from backend.app.api.dependencies.limiter import limiter
from backend.app.services.metrics import inc_documents_processed, inc_celery_task

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "backend/uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50")) * 1024 * 1024


@router.post("/api/upload", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_FILE_SIZE // (1024 * 1024)} MB size limit.",
        )

    # Validate PDF magic bytes (%PDF-)
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF files are allowed.")

    doc_id = uuid.uuid4()
    safe_filename = os.path.basename(file.filename)

    db_doc = Document(id=doc_id, filename=safe_filename, status="uploaded")
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{safe_filename}")
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    process_document.delay(str(doc_id))
    inc_documents_processed("success")
    inc_celery_task("process_document", "dispatched")

    return {"id": str(doc_id), "filename": file.filename, "status": "uploaded"}
