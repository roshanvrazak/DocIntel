# DocIntel — Plan 1: Infrastructure & Ingestion Foundation (REVISED)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Setup the core distributed infrastructure and the background PDF ingestion pipeline.

**Architecture:** A FastAPI server orchestrating background tasks via Celery and Redis. Documents are parsed, semantically chunked, and embedded via LiteLLM/Ollama, then stored in PostgreSQL with pgvector.

**Tech Stack:** FastAPI, Celery, Redis, PostgreSQL + pgvector, LiteLLM, Ollama, PyMuPDF, Docker Compose.

---

### Task 1: Docker Compose & Infrastructure

**Files:**
- Create: `docker-compose.yml`
- Create: `.env`
- Create: `litellm/config.yaml`
- Create: `backend/Dockerfile`
- Create: `backend/pyproject.toml`

- [ ] **Step 1: Create `docker-compose.yml` with all services**
```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=docintel
      - POSTGRES_PASSWORD=docintel
      - POSTGRES_DB=docintel
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama

  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    ports:
      - "4000:4000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./litellm/config.yaml:/app/config.yaml
    depends_on:
      - ollama

  phoenix:
    image: arize-phoenix:latest
    ports:
      - "6006:6006"
      - "4317:4317"
      - "4318:4318"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://docintel:docintel@postgres:5432/docintel
      - REDIS_URL=redis://redis:6379/0
      - LITELLM_PROXY_URL=http://litellm:4000
    depends_on:
      - postgres
      - redis
      - litellm

volumes:
  pgdata:
  ollama_models:
```

- [ ] **Step 2: Create `backend/pyproject.toml` with pgvector**
```toml
[project]
name = "docintel-backend"
version = "0.1.0"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]",
    "sqlalchemy>=2.0",
    "asyncpg",
    "psycopg2-binary",
    "pgvector",
    "pydantic-settings",
    "celery[redis]",
    "pymupdf",
    "python-multipart",
    "litellm",
]
```

- [ ] **Step 3: Create `litellm/config.yaml`**
```yaml
model_list:
  - model_name: nomic-embed-text
    litellm_params:
      model: ollama/nomic-embed-text
      api_base: http://ollama:11434
```

- [ ] **Step 4: Verify Docker services start**
Run: `docker-compose up -d`
Expected: All services (including ollama and litellm) start.

- [ ] **Step 5: Commit**

### Task 2: Database Schema (with pgvector)

**Files:**
- Create: `backend/app/models/document.py`
- Create: `backend/app/db/session.py`

- [ ] **Step 1: Define SQLAlchemy models with Vector support**
```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import declarative_base
import uuid
import datetime

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    status = Column(String, default="uploaded")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    content = Column(Text, nullable=False)
    page_number = Column(Integer)
    embedding = Column(Vector(768)) # dimension for nomic-embed-text
```

- [ ] **Step 2: Create initial DB initialization script (setup extensions)**
- [ ] **Step 3: Commit**

### Task 3: Ingestion Logic (Parsing & Semantic Chunking)

**Files:**
- Create: `backend/app/services/parser.py`
- Create: `backend/app/services/chunker.py`

- [ ] **Step 1: Implement PDF parsing with PyMuPDF**
- [ ] **Step 2: Implement Semantic Chunking (using LiteLLM to proxy Ollama embeddings)**
- [ ] **Step 3: Commit**

### Task 4: API & Worker Infrastructure (WebSockets & Celery)

**Files:**
- Create: `backend/app/worker.py`
- Create: `backend/app/api/routes/upload.py`
- Create: `backend/app/api/websocket/progress.py`

- [ ] **Step 1: Setup Celery worker and `process_document` task**
- [ ] **Step 2: Implement WebSocket progress tracking endpoint**
- [ ] **Step 3: Implement POST `/api/upload` endpoint**
- [ ] **Step 4: Commit**
