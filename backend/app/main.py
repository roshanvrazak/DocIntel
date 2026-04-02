import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.app.api.dependencies.limiter import limiter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.litellm import LiteLLMInstrumentor

from backend.app.api.routes.upload import router as upload_router
from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.documents import router as documents_router
from backend.app.api.websocket.progress import progress_websocket

# --- Tracing ---
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://phoenix:4317")
resource = Resource(attributes={"service.name": "docintel-backend"})
tracer_provider = TracerProvider(resource=resource)
try:
    otlp_exporter = OTLPSpanExporter(endpoint=PHOENIX_ENDPOINT, insecure=True, timeout=10)
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    print(f"Tracing initialized pointing to {PHOENIX_ENDPOINT}")
except Exception as e:
    print(f"Warning: Failed to initialize OTLP exporter to {PHOENIX_ENDPOINT}: {e}")
    print("Tracing will be disabled.")

trace.set_tracer_provider(tracer_provider)
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
LiteLLMInstrumentor().instrument(tracer_provider=tracer_provider)

# --- App ---
app = FastAPI(
    title="DocIntel API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

# --- CORS ---
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# --- Routers ---
app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(documents_router)


@app.websocket("/ws/progress/{doc_id}")
async def websocket_endpoint(websocket: WebSocket, doc_id: str):
    await progress_websocket(websocket, doc_id)


@app.get("/")
async def root():
    return {"message": "Welcome to DocIntel API"}


@app.get("/health")
async def health():
    """Health check — verifies DB and Redis connectivity."""
    import os
    import redis.asyncio as aioredis
    from backend.app.db.session import engine
    from sqlalchemy import text

    checks: dict = {}

    # Database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis
    try:
        r = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, **checks}
