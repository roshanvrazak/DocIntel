# DocIntel — Agentic Document Intelligence Platform: Master Implementation Prompt

## 1. Project Identity

**Name:** DocIntel
**Tagline:** "Upload many. Understand all. Trace everything."
**Repository:** `docintel`
**Author:** Roshan Razak
**Purpose:** Portfolio project demonstrating production-grade AI engineering for AI Engineer roles.

---

## 2. Product Vision

DocIntel is an **agentic RAG platform** that accepts multiple PDF documents as input and enables intelligent, conversational interaction across all of them simultaneously. It implements a full document intelligence pipeline: advanced chunking, hybrid retrieval, cross-encoder re-ranking, agentic query routing via LangGraph, and end-to-end observability via Arize Phoenix.

### Core User Flow

```
1. User uploads 1–20 PDF documents via drag-and-drop UI
2. System parses, chunks, embeds, and indexes all documents (with live progress)
3. User selects an ACTION or asks a free-form question
4. An agentic router classifies the query and dispatches to the appropriate processing agent
5. The agent executes a multi-step RAG pipeline with retrieval, re-ranking, and synthesis via LiteLLM
6. Output is returned with per-sentence source citations and a faithfulness score
7. Full execution trace is viewable in-app and in Arize Phoenix
```

### Supported Actions

| Action | Description | Output Mode |
|--------|-------------|-------------|
| **Summarise** | Executive summary across all documents | Many-to-One |
| **Summarise Each** | Individual summary per document | Many-to-Many |
| **Compare** | Structured comparison matrix across documents | Many-to-One |
| **Contradictions** | Find where documents disagree | Many-to-One |
| **Extract** | Pull structured data (dates, names, entities, tables) | Many-to-Many |
| **Q&A** | Conversational question answering across all docs | Many-to-One |
| **Action Items** | Extract tasks, deadlines, responsibilities | Both |
| **Timeline** | Build chronological timeline from all documents | Many-to-One |
| **Custom Query** | Free-form natural language question | Many-to-One |

---

## 3. Technical Architecture

### 3.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/Vite/TypeScript/Tailwind)        │
│                                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Drop Zone │  │ Action Panel │  │ Chat / Q&A   │  │ Trace Viewer  │  │
│  │ (PDF      │  │ (Select mode │  │ (Conversatio │  │ (Pipeline     │  │
│  │  Upload)  │  │  & action)   │  │  nal RAG)    │  │  visibility)  │  │
│  └─────┬─────┘  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│        │               │                 │                  │           │
│        └───────────────┴─────────────────┴──────────────────┘           │
│                              │ SSE / WebSocket                          │
└──────────────────────────────┼──────────────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────────────┐
│                        BACKEND (FastAPI / Python 3.11+)                  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     API Layer (FastAPI)                           │   │
│  │  POST /api/upload    POST /api/process    GET /api/trace         │   │
│  │  POST /api/chat      GET  /api/status     GET /api/documents     │   │
│  │  WS   /ws/progress                                               │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────┼───────────────────────────────────┐   │
│  │                    INGESTION PIPELINE                             │   │
│  │                                                                   │   │
│  │  ┌─────────┐  ┌───────────┐  ┌───────────┐  ┌────────────────┐  │   │
│  │  │ PDF     │→ │ Document- │→ │ Semantic  │→ │ Embed + Store  │  │   │
│  │  │ Parser  │  │ Aware     │  │ Chunker   │  │ (pgvector)     │  │   │
│  │  │         │  │ Splitter  │  │ (LiteLLM) │  │                │  │   │
│  │  │ PyMuPDF │  │           │  │           │  │ + BM25 Index   │  │   │
│  │  └─────────┘  └───────────┘  └───────────┘  └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────┼───────────────────────────────────┐   │
│  │                    AGENTIC LAYER (LangGraph)                     │   │
│  │                                                                   │   │
│  │               ┌──────────────────┐                                │   │
│  │               │   Router Agent   │ ← classifies intent            │   │
│  │               └────────┬─────────┘                                │   │
│  │          ┌─────────────┼─────────────────┐                        │   │
│  │          ▼             ▼                  ▼                        │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌───────────────┐               │   │
│  │  │ RAG      │  │ Map-Reduce   │  │ Comparison    │  ...more      │   │
│  │  │ Agent    │  │ Summariser   │  │ Agent         │  agents       │   │
│  │  └──────────┘  └──────────────┘  └───────────────┘               │   │
│  │                                                                   │   │
│  │  Each agent: retrieve → rerank → synthesise → cite → validate    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────┼───────────────────────────────────┐   │
│  │                    RETRIEVAL ENGINE                               │   │
│  │                                                                   │   │
│  │  ┌────────────────┐  ┌─────────────┐  ┌──────────────────────┐  │   │
│  │  │ Multi-Query    │→ │ Hybrid      │→ │ Cross-Encoder        │  │   │
│  │  │ Retriever      │  │ Search      │  │ Re-Ranker            │  │   │
│  │  │ (Gemini via    │  │ (pgvector + │  │ (LiteLLM Proxy)      │  │   │
│  │  │  LiteLLM)      │  │  BM25 +     │  │                      │  │   │
│  │  │                │  │  RRF merge) │  │ Retrieve 20 → Top 5 │  │   │
│  │  └────────────────┘  └─────────────┘  └──────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────┼───────────────────────────────────┐   │
│  │                    OBSERVABILITY (Arize Phoenix)                  │   │
│  │                                                                   │   │
│  │  • Full trace per request (OpenTelemetry instrumentation)        │   │
│  │  • Latency + token usage + cost tracking                         │   │
│  │  • Evaluation datasets + automated scoring (RAGAS)                │   │
│  │  • Real-time visualization of agent decision trees               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────────────┐
│                        DATA LAYER                                       │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ PostgreSQL   │  │ Redis        │  │ File Storage │                  │
│  │ + pgvector   │  │              │  │              │                  │
│  │              │  │ • Query      │  │ • Uploaded   │                  │
│  │ • Chunks     │  │   cache      │  │   PDFs       │                  │
│  │ • Embeddings │  │ • Session    │  │ • Processed  │                  │
│  │ • Documents  │  │   state      │  │   outputs    │                  │
│  │ • Metadata   │  │ • Job queue  │  │              │                  │
│  │ • BM25 index │  │   (Celery)   │  │              │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + Vite + TypeScript + Tailwind CSS | UI with drag-drop upload, action selector, chat, trace viewer |
| **Backend** | FastAPI (Python 3.11+) | Async API server, WebSocket for progress streaming |
| **Proxy** | LiteLLM | Model-agnostic API gateway for Gemini and Ollama |
| **Orchestration** | LangChain 0.3+ | Chains, retrievers, output parsers, text splitters |
| **Agentic** | LangGraph | Stateful agent graph with conditional routing, cycles, retry logic |
| **LLM (Synthesis)** | Gemini 1.5 Pro | Primary LLM for all synthesis, extraction, and reasoning tasks |
| **LLM (Classification)** | Gemini 1.5 Flash | Lightweight tasks: query routing, intent classification |
| **Embeddings** | Ollama (nomic-embed-text) | Local embeddings via LiteLLM proxy |
| **Vector Store** | PostgreSQL + pgvector | Chunk storage with HNSW indexing for ANN search |
| **Sparse Search** | PostgreSQL tsvector | Native BM25-style keyword search |
| **Observability** | Arize Phoenix | Full OpenTelemetry tracing, evaluation datasets, scoring |
| **Evaluation** | RAGAS | Faithfulness, relevancy, context precision, context recall |
| **PDF Parsing** | PyMuPDF (fitz) | Text extraction and layout analysis |
| **Task Queue** | Celery + Redis | Async document processing (parse, chunk, embed) |

---

## 4. Implementation Phases

### Phase 1: Ingestion Pipeline
*   Setup Docker Compose with FastAPI, PostgreSQL+pgvector, Redis, Ollama, LiteLLM, and Arize Phoenix.
*   Implement `process_document` Celery task: Parse (PyMuPDF) -> Chunk (Semantic) -> Embed (LiteLLM/Ollama) -> Index (pgvector).
*   Add WebSocket progress tracking.

### Phase 2: Retrieval Engine
*   Multi-query generation via LiteLLM/Gemini.
*   Hybrid search: `pgvector` dense search + PostgreSQL `tsvector` sparse search.
*   RRF Fusion and Re-ranking.

### Phase 3: Agentic Layer (LangGraph)
*   Define `DocIntelState` and Router node.
*   Implement specialized agent nodes (RAG, Compare, Summarize) using Gemini 1.5 Pro.
*   Add self-correction validator node to verify grounding.

### Phase 4: Observability & Eval
*   Instrument all components with OpenTelemetry for Arize Phoenix.
*   Setup RAGAS evaluation suite to run in CI.
*   Integrate trace IDs into the frontend for debugging.

---

## 5. Docker Compose Configuration (Snippets)

```yaml
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    ports:
      - "4000:4000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./litellm/config.yaml:/app/config.yaml

  phoenix:
    image: arize-phoenix:latest
    ports:
      - "6006:6006" # UI
      - "4317:4317" # OTLP gRPC
      - "4318:4318" # OTLP HTTP

  backend:
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317
      - LITELLM_PROXY_URL=http://litellm:4000
```

---

## 6. Key Python Dependencies

```toml
dependencies = [
    "fastapi>=0.115",
    "litellm>=1.0",
    "langchain>=0.3",
    "langgraph>=0.2",
    "arize-phoenix>=4.0",
    "opentelemetry-sdk>=1.20",
    "opentelemetry-exporter-otlp>=1.20",
    "pymupdf>=1.24",
    "pgvector>=0.3",
    "celery[redis]>=5.4",
    "ragas>=0.2",
]
```
