import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session
from backend.app.models.document import Document
from backend.app.worker import process_document

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "backend/uploads")

@router.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Create DB record
    doc_id = uuid.uuid4()
    safe_filename = os.path.basename(file.filename)
    db_doc = Document(
        id=doc_id,
        filename=safe_filename,
        status="uploaded"
    )
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)

    # Save file locally
    # We prefix with doc_id to avoid filename collisions
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{safe_filename}")
    
    # Ensure directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Trigger Celery task
    process_document.delay(str(doc_id))

    return {
        "id": str(doc_id),
        "filename": file.filename,
        "status": "uploaded"
    }
