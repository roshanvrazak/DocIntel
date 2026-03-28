import os
import asyncio
from celery import Celery
from sqlalchemy.orm import Session
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.litellm import LiteLLMInstrumentor
from backend.app.db.session import get_sync_session
from backend.app.models.document import Document, Chunk
from backend.app.services.parser import parse_pdf
from backend.app.services.chunker import semantic_chunk
from backend.app.services.embeddings import generate_embeddings
import json
import redis
import logging

logger = logging.getLogger(__name__)

# Initialize OpenTelemetry for Worker
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://phoenix:4317")
resource = Resource(attributes={
    "service.name": "docintel-worker"
})

tracer_provider = TracerProvider(resource=resource)
try:
    otlp_exporter = OTLPSpanExporter(endpoint=PHOENIX_ENDPOINT, insecure=True, timeout=10)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    print(f"Worker tracing initialized pointing to {PHOENIX_ENDPOINT}")
except Exception as e:
    print(f"Warning: Failed to initialize worker OTLP exporter to {PHOENIX_ENDPOINT}: {e}")

trace.set_tracer_provider(tracer_provider)

# Instrument LangChain and LiteLLM
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
LiteLLMInstrumentor().instrument(tracer_provider=tracer_provider)

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
    logger.info(f"Starting to process document: {doc_id}")
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("worker.process_document") as span:
        span.set_attribute("doc_id", doc_id)
        with get_sync_session() as db:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                logger.error(f"Document {doc_id} not found in database")
                return f"Document {doc_id} not found"

            try:
                # 1. Update DB status to parsing
                logger.info(f"Step 1: Parsing document {doc_id}")
                doc.status = "parsing"
                db.commit()
                publish_status(doc_id, "parsing", 10)

                # 2. Call parse_pdf
                safe_filename = os.path.basename(doc.filename)
                file_path = os.path.join(os.getenv("UPLOAD_DIR", "backend/uploads"), f"{doc.id}_{safe_filename}")
                logger.info(f"Reading file from: {file_path}")
                pages = parse_pdf(file_path)
                logger.info(f"Parsed {len(pages)} pages")
                publish_status(doc_id, "parsing", 40)

                # 3. Update DB status to chunking
                logger.info(f"Step 2: Chunking document {doc_id}")
                doc.status = "chunking"
                db.commit()
                publish_status(doc_id, "chunking", 50)

                # 4. Call semantic_chunk
                full_text = "\n".join([p["content"] for p in pages])
                chunk_texts = semantic_chunk(full_text)
                logger.info(f"Created {len(chunk_texts)} chunks")
                publish_status(doc_id, "chunking", 70)

                # 5. Generate Embeddings
                logger.info(f"Step 3: Generating embeddings for document {doc_id}")
                doc.status = "embedding"
                db.commit()
                publish_status(doc_id, "embedding", 75)
                
                def embedding_progress(current, total):
                    progress = 75 + int((current / total) * (90 - 75))
                    publish_status(doc_id, f"embedding: {current}/{total}", progress)

                embeddings = generate_embeddings(chunk_texts, progress_callback=embedding_progress)
                logger.info(f"Generated {len(embeddings)} embeddings")

                # Save chunks to DB
                logger.info(f"Step 4: Saving chunks to database for document {doc_id}")
                db_chunks = [
                    Chunk(document_id=doc.id, content=text, embedding=embedding)
                    for text, embedding in zip(chunk_texts, embeddings)
                ]
                db.add_all(db_chunks)
                
                # 6. Update DB status to ready
                doc.status = "ready"
                db.commit()
                logger.info(f"Document {doc_id} processed successfully")
                publish_status(doc_id, "ready", 100)

                return f"Document {doc_id} processed successfully"

            except Exception as e:
                # Only mark as error if it's the last retry or not retryable
                # For simplicity, we'll mark as error, but Celery will retry if configured
                db.rollback()
                span.record_exception(e)
                span.set_status(trace.status.Status(trace.status.StatusCode.ERROR))
                if self.request.retries >= self.max_retries:
                    doc.status = "error"
                    db.commit()
                    publish_status(doc_id, f"error: {str(e)}", 0)
                
                # Re-raise to trigger Celery retry
                raise e
