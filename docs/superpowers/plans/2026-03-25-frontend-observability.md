# DocIntel — Plan 4: Frontend & Observability

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React frontend with live progress tracking and integrate deep observability via Arize Phoenix.

**Architecture:** A Vite-powered React SPA using Tailwind CSS for styling and WebSockets for real-time background status updates. All AI interactions are instrumented with OpenTelemetry.

**Tech Stack:** React 18, Vite, TypeScript, Tailwind CSS, Arize Phoenix, OpenTelemetry.

---

### Task 1: Frontend Scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`

- [ ] **Step 1: Scaffold Vite + React + TS app**
- [ ] **Step 2: Setup Tailwind CSS**
- [ ] **Step 3: Setup basic API and WebSocket service clients**
- [ ] **Step 4: Commit**

### Task 2: Upload Zone & Progress Tracking

**Files:**
- Create: `frontend/src/components/UploadZone.tsx`
- Create: `frontend/src/hooks/useWebSocket.ts`

- [ ] **Step 1: Implement drag-and-drop upload**
- [ ] **Step 2: Connect WebSocket for live ingestion status updates**
- [ ] **Step 3: Commit**

### Task 3: Chat Interface & Agent Actions

**Files:**
- Create: `frontend/src/components/ChatInterface.tsx`
- Create: `frontend/src/components/ActionPanel.tsx`

- [ ] **Step 1: Build the action selection panel**
- [ ] **Step 2: Implement streaming chat interface with citation display**
- [ ] **Step 3: Commit**

### Task 4: Observability Integration (Arize Phoenix)

**Files:**
- Modify: `backend/app/main.py`
- Create: `frontend/src/components/TraceViewer.tsx`

- [ ] **Step 1: Instrument Backend with OpenTelemetry (OTLP)**
- [ ] **Step 2: Export spans to Arize Phoenix**
- [ ] **Step 3: Embed simplified trace view in the frontend**
- [ ] **Step 4: Verify full end-to-end tracing in Phoenix UI**
- [ ] **Step 5: Commit**
