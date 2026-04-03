"""
Prometheus metrics for DocIntel.

Exposes application-level metrics at GET /metrics (text format).

Metrics:
  docintel_documents_processed_total   — counter, labelled by status (success/error)
  docintel_query_duration_seconds      — histogram of end-to-end chat request latency
  docintel_active_ws_connections       — gauge of current WebSocket connections
  docintel_celery_tasks_total          — counter, labelled by task name and state
  docintel_retrieval_chunks_returned   — histogram of chunks returned per hybrid search

Usage (agents/routes call the helpers below):

    from backend.app.services.metrics import (
        inc_documents_processed,
        observe_query_duration,
        inc_celery_task,
        observe_retrieval_chunks,
    )
"""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

# Use a dedicated registry so we don't accidentally expose process/platform
# metrics that can leak host information in multi-tenant deployments.
# Switch to the default registry (prometheus_client.REGISTRY) if you want
# standard process metrics too.
registry = CollectorRegistry(auto_describe=True)

documents_processed = Counter(
    "docintel_documents_processed_total",
    "Total number of documents ingested, labelled by outcome",
    ["status"],   # "success" | "error"
    registry=registry,
)

query_duration = Histogram(
    "docintel_query_duration_seconds",
    "End-to-end latency of /api/chat requests",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
    registry=registry,
)

active_ws_connections = Gauge(
    "docintel_active_ws_connections",
    "Number of currently open WebSocket progress connections",
    registry=registry,
)

celery_tasks = Counter(
    "docintel_celery_tasks_total",
    "Total Celery tasks dispatched, labelled by task name and state",
    ["task", "state"],   # state: "dispatched" | "success" | "failure"
    registry=registry,
)

retrieval_chunks = Histogram(
    "docintel_retrieval_chunks_returned",
    "Number of chunks returned by hybrid_search per query",
    buckets=[1, 2, 3, 5, 8, 10, 15, 20],
    registry=registry,
)


# ---------------------------------------------------------------------------
# Convenience helpers (so callers don't import prometheus_client directly)
# ---------------------------------------------------------------------------

def inc_documents_processed(status: str = "success") -> None:
    documents_processed.labels(status=status).inc()


def observe_query_duration(seconds: float) -> None:
    query_duration.observe(seconds)


def set_active_ws_connections(count: int) -> None:
    active_ws_connections.set(count)


def inc_active_ws_connections() -> None:
    active_ws_connections.inc()


def dec_active_ws_connections() -> None:
    active_ws_connections.dec()


def inc_celery_task(task: str, state: str) -> None:
    celery_tasks.labels(task=task, state=state).inc()


def observe_retrieval_chunks(count: int) -> None:
    retrieval_chunks.observe(count)


def metrics_response() -> tuple[bytes, str]:
    """Return (body_bytes, content_type) suitable for a FastAPI Response."""
    return generate_latest(registry), CONTENT_TYPE_LATEST
