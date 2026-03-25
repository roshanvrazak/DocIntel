# DocIntel — Agentic Document Intelligence Platform: Design Specification

**Date:** 2026-03-25
**Status:** Approved
**Author:** Gemini CLI (Orchestrated by Roshan Razak)

## 1. Executive Summary
DocIntel is an agentic RAG platform designed to process multiple PDF documents and enable intelligent, multi-step conversational interaction. It leverages a distributed architecture to handle heavy ingestion workloads asynchronously while providing deep observability into its decision-making process.

## 2. System Architecture
The system follows a **Distributed Orchestrator** pattern using Docker Compose.

### 2.1 Core Components
*   **API Gateway (FastAPI):** Central hub for file uploads, session management, and WebSocket-based progress streaming.
*   **Asynchronous Worker (Celery + Redis):** Handles PDF parsing, semantic chunking, and embedding generation in the background.
*   **Universal AI Proxy (LiteLLM):** Provides a model-agnostic interface for all LLM calls (Gemini for reasoning, local Ollama for embeddings).
*   **Observability Platform (Arize Phoenix):** OpenTelemetry-based tracing and evaluation for the entire RAG pipeline.
*   **Vector Database (PostgreSQL + pgvector):** Stores chunks and high-dimensional embeddings with HNSW indexing.
*   **Local Inference (Ollama):** Local execution of `nomic-embed-text` for cost-efficient embeddings.
*   **Primary LLM (Gemini API):** High-reasoning tasks including query routing, synthesis, and grounding validation.

## 3. Ingestion Pipeline
1.  **File Intake:** API accepts up to 20 PDFs (max 50MB/file), saves to local volume, and creates a `PENDING` document record.
2.  **Task Dispatch:** A Celery task is enqueued for each document.
3.  **Parsing:** `PyMuPDF` extracts text/layout; metadata is captured.
4.  **Semantic Chunking:** LiteLLM proxies requests to Ollama to split text based on meaning boundaries.
5.  **Embedding & Indexing:** `nomic-embed-text` vectors are stored in `pgvector` alongside a BM25 index for hybrid search.
6.  **Progress Tracking:** Status updates are broadcast via WebSockets (`/ws/progress`).

## 4. Agentic RAG Engine
Built with **LangGraph** for stateful, multi-step orchestration.

### 4.1 Retrieval Strategy
*   **Multi-Query Generation:** Gemini generates 3–5 variations of the user query.
*   **Hybrid Search:** Parallel Dense (pgvector) and Sparse (BM25) search.
*   **RRF Fusion:** Merges results using Reciprocal Rank Fusion.
*   **Re-ranking:** Top candidates are re-ranked to select the final top 5 chunks.

### 4.2 Agent Graph Nodes
*   **Router Agent:** Classifies intent (Summarize, Compare, Fact-Check, Q&A).
*   **Specialized Agents:** Nodes for RAG, Comparison, and Map-Reduce Summarization.
*   **Validator Node:** Self-correction loop using Gemini to check for hallucinations and grounding.

## 5. Data Layer
*   **PostgreSQL:** Stores `documents`, `chunks` (with vectors), `sessions`, and `query_logs`.
*   **Redis:** Message broker for Celery and caching for frequent queries.
*   **Local Volume:** Persistent storage for uploaded PDFs and Ollama models.

## 6. Frontend & UX
*   **Tech Stack:** React (Vite) + TypeScript + Tailwind CSS.
*   **Key Features:**
    *   Drag-and-drop upload with per-file live progress.
    *   Action-oriented panel (Summarize, Compare, etc.).
    *   Streaming chat responses with clickable citations.
    *   In-app trace visibility (simplified Arize Phoenix view).

## 7. Infrastructure
*   **Orchestration:** Docker Compose for multi-container management.
*   **Observability:** Full instrumentation with OpenTelemetry exported to Arize Phoenix.
*   **CI/CD:** Github Actions for linting (Ruff), type-checking (MyPy), and RAGAS evaluation.

## 8. Future Roadmap
*   **OCR Support:** Adding Tesseract or Claude Vision for scanned PDFs.
*   **Multi-modal:** Extracting and analyzing charts/images.
*   **Deployment:** Migration to Proxmox Homelab with Cloudflare Tunnels.
