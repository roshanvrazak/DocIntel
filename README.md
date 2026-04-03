# DocIntel

Production-grade agentic RAG platform for multi-document intelligence. Upload PDFs, run them through a parse → chunk → embed → index pipeline, then query them conversationally with citations via a LangGraph-orchestrated agent system.

## Features

- **Multi-document upload** — drag-and-drop up to 20 PDFs with real-time processing progress
- **Hybrid retrieval** — dense (pgvector cosine) + sparse (PostgreSQL full-text) search fused via Reciprocal Rank Fusion, then re-ranked by Gemini 1.5 Flash
- **Agentic pipeline** — LangGraph router dispatches to specialised agents: Q&A, Summarise, Compare, Extract, Contradictions, Action Items, Timeline
- **Self-correction loop** — faithfulness + answer-relevancy scoring with automatic retry (up to 3×)
- **Real citations** — every response includes source chunks with filename and page number
- **Document management** — list, delete, and reprocess documents via API and UI
- **Full observability** — OpenTelemetry traces exported to Arize Phoenix

## Architecture

```
Frontend (React/Vite/Tailwind)
    │
    ├── POST /api/upload        → Celery task → Parse → Chunk → Embed → pgvector
    ├── POST /api/chat          → LangGraph → Router → Agent → Validator → Stream
    ├── GET  /api/documents     → Paginated document library
    ├── WS   /ws/progress/{id}  → Real-time ingestion progress
    └── GET  /health            → DB + Redis liveness check

Backend: FastAPI + SQLAlchemy + Celery
Models:  Gemini 1.5 Pro (synthesis), Gemini 1.5 Flash (routing/scoring), Ollama nomic-embed-text
Storage: PostgreSQL + pgvector, Redis
Tracing: OpenTelemetry → Arize Phoenix (port 6006)
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — set GEMINI_API_KEY and optionally API_KEY
```

### 2. Start all services

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Arize Phoenix | http://localhost:6006 |

### 3. Upload and query

1. Open http://localhost:3000
2. Drag and drop PDF files into the upload zone
3. Wait for the status badge to show **ready**
4. Select documents, choose an action, and start chatting

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | **Required.** Google Gemini API key |
| `API_KEY` | unset | When set, all requests require `X-API-Key` header |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum PDF upload size in MB |
| `MAX_QUERY_LENGTH` | `2000` | Maximum chat query length in characters |
| `CHUNK_SIZE` | `1000` | Text chunk size for ingestion |
| `CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks |
| `RETRIEVER_TOP_K` | `5` | Number of chunks to return per query |
| `FAITHFULNESS_THRESHOLD` | `0.8` | Minimum faithfulness score to pass validation |
| `VALIDATOR_MAX_RETRIES` | `3` | Maximum self-correction retries |
| `RETRIEVAL_CACHE_TTL` | `300` | RAG result cache TTL in seconds |
| `MAX_CONTEXT_CHARS` | `200000` | Max characters sent as LLM context (~50k tokens) |

## API Reference

Full interactive docs at **http://localhost:8000/docs** (Swagger UI).

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload a PDF document |
| `POST` | `/api/chat` | Stream a chat response |
| `GET` | `/api/documents` | List documents (paginated) |
| `DELETE` | `/api/documents/{id}` | Delete a document |
| `POST` | `/api/documents/{id}/reprocess` | Re-trigger ingestion |
| `GET` | `/health` | Liveness check (DB + Redis) |
| `GET` | `/metrics` | Prometheus metrics (scrape endpoint) |

## Development

### Backend

```bash
cd backend
pip install -e .
pytest tests/ -v --asyncio-mode=auto
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # dev server on :3000
npm test          # Vitest unit tests
npm run lint      # ESLint
```

### CI

GitHub Actions runs on every push to `main`:
- Python: `ruff` lint + `pytest`
- Frontend: `eslint` + `vitest`
- Docker: build verification for both images

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy 2.0, Celery |
| Orchestration | LangGraph 0.2, LangChain 0.3 |
| LLM Gateway | LiteLLM → Gemini 1.5 Pro/Flash |
| Embeddings | Ollama (`nomic-embed-text`, 768-dim) |
| Vector DB | PostgreSQL 16 + pgvector (HNSW index) |
| Cache / Queue | Redis 7 |
| Observability | OpenTelemetry + Arize Phoenix |
| Containerisation | Docker Compose |
