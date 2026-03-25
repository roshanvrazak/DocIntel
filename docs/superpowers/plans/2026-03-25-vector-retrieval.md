# DocIntel — Plan 2: Vector Search & Hybrid Retrieval

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement semantic and keyword search with re-ranking.

**Architecture:** Hybrid search (Dense via pgvector + Sparse via PostgreSQL FTS) with LiteLLM proxy for embeddings and LLM-based re-ranking.

**Tech Stack:** pgvector, LiteLLM, Ollama (nomic-embed-text), Gemini 1.5.

---

### Task 1: Vector Storage Setup (pgvector)

**Files:**
- Modify: `backend/app/models/document.py`
- Modify: `backend/app/db/session.py`

- [ ] **Step 1: Update Chunk model with vector and FTS columns**
```python
from pgvector.sqlalchemy import Vector

class Chunk(Base):
    # ... previous fields
    embedding = Column(Vector(768)) # dimension for nomic-embed-text
    # ...
```
- [ ] **Step 2: Initialize pgvector extension in DB**
- [ ] **Step 3: Commit**

### Task 2: Local Embeddings (Ollama + LiteLLM)

**Files:**
- Create: `backend/app/services/embeddings.py`
- Create: `litellm/config.yaml`

- [ ] **Step 1: Setup LiteLLM config to proxy Ollama**
- [ ] **Step 2: Implement embedding generation using LiteLLM SDK**
- [ ] **Step 3: Update `process_document` worker task to include embedding generation**
- [ ] **Step 4: Verify embeddings are stored in pgvector**
- [ ] **Step 5: Commit**

### Task 3: Hybrid Search Engine

**Files:**
- Create: `backend/app/services/retriever.py`

- [ ] **Step 1: Implement Dense Search (Vector Similarity)**
- [ ] **Step 2: Implement Sparse Search (PostgreSQL tsvector)**
- [ ] **Step 3: Implement RRF (Reciprocal Rank Fusion) to merge results**
- [ ] **Step 4: Verify search quality with sample queries**
- [ ] **Step 5: Commit**

### Task 4: Multi-Query & Re-ranking

**Files:**
- Modify: `backend/app/services/retriever.py`

- [ ] **Step 1: Use Gemini (via LiteLLM) to generate query variations**
- [ ] **Step 2: Implement LLM-based re-ranking for top N results**
- [ ] **Step 3: Commit**
