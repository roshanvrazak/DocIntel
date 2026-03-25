# DocIntel — Plan 3: Agentic Intelligence & LangGraph

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the LangGraph-based agent state machine and core agentic actions.

**Architecture:** A stateful graph orchestrating query routing, specialized analysis nodes, and a validation/self-correction loop.

**Tech Stack:** LangGraph, Gemini 1.5, LiteLLM.

---

### Task 1: Agent State & Graph Skeleton

**Files:**
- Create: `backend/app/agents/state.py`
- Create: `backend/app/agents/graph.py`

- [ ] **Step 1: Define `DocIntelState` (TypedDict)**
- [ ] **Step 2: Scaffolding the LangGraph state machine**
- [ ] **Step 3: Commit**

### Task 2: Router Agent Node

**Files:**
- Create: `backend/app/agents/router.py`

- [ ] **Step 1: Implement Router Agent node using Gemini 1.5 Flash**
- [ ] **Step 2: Add conditional routing to the graph**
- [ ] **Step 3: Verify routing for various query intents**
- [ ] **Step 4: Commit**

### Task 3: Specialized Agent Nodes (RAG, Summarize, Compare)

**Files:**
- Create: `backend/app/agents/rag_agent.py`
- Create: `backend/app/agents/summarise_agent.py`
- Create: `backend/app/agents/compare_agent.py`

- [ ] **Step 1: Implement RAG node with retrieval integration**
- [ ] **Step 2: Implement Map-Reduce Summarization node**
- [ ] **Step 3: Implement Cross-Document Comparison node**
- [ ] **Step 4: Commit**

### Task 4: Validation & Self-Correction

**Files:**
- Create: `backend/app/agents/validator.py`

- [ ] **Step 1: Implement Validator node for grounding check**
- [ ] **Step 2: Add self-correction loop in the graph**
- [ ] **Step 3: Commit**
