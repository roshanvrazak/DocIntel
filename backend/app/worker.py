import os
import asyncio
from celery import Celery
from sqlalchemy.orm import Session
from backend.app.db.session import get_sync_session
from backend.app.models.document import Document, Chunk
from backend.app.services.parser import parse_pdf
from backend.app.services.chunker import semantic_chunk
import json
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)

# Redis client for publishing updates
redis_client = redis.from_url(REDIS_URL)

def publish_status(doc_id: str, status: str, progress: int = 0):
    message = {
        "doc_id": doc_id,
        "status": status,
        "progress": progress
    }
    redis_client.publish(f"progress:{doc_id}", json.dumps(message))

@celery_app.task(
    name="process_document",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5}
)
def process_document(self, doc_id: str):
    with get_sync_session() as db:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return f"Document {doc_id} not found"

        try:
            # 1. Update DB status to parsing
            doc.status = "parsing"
            db.commit()
            publish_status(doc_id, "parsing", 10)

            # 2. Call parse_pdf
            # Ensure we use basename to be safe
            safe_filename = os.path.basename(doc.filename)
            file_path = os.path.join(os.getenv("UPLOAD_DIR", "backend/uploads"), f"{doc.id}_{safe_filename}")
            pages = parse_pdf(file_path)
            publish_status(doc_id, "parsing", 40)

            # 3. Update DB status to chunking
            doc.status = "chunking"
            db.commit()
            publish_status(doc_id, "chunking", 50)

            # 4. Call semantic_chunk
            full_text = "\n".join([p["content"] for p in pages])
            chunks = semantic_chunk(full_text)
            publish_status(doc_id, "chunking", 80)

            # Save chunks to DB (using bulk add for performance)
            db_chunks = [
                Chunk(document_id=doc.id, content=chunk_text)
                for chunk_text in chunks
            ]
            db.add_all(db_chunks)
            
            # 5. Update DB status to ready
            doc.status = "ready"
            db.commit()
            publish_status(doc_id, "ready", 100)

            return f"Document {doc_id} processed successfully"

        except Exception as e:
            # Only mark as error if it's the last retry or not retryable
            # For simplicity, we'll mark as error, but Celery will retry if configured
            db.rollback()
            if self.request.retries >= self.max_retries:
                doc.status = "error"
                db.commit()
                publish_status(doc_id, f"error: {str(e)}", 0)
            
            # Re-raise to trigger Celery retry
            raise e
