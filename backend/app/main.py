import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
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
from backend.app.api.websocket.progress import progress_websocket

# Initialize Arize Phoenix Tracing via OTLP gRPC
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://phoenix:4317")
resource = Resource(attributes={
    "service.name": "docintel-backend"
})

tracer_provider = TracerProvider(resource=resource)
try:
    otlp_exporter = OTLPSpanExporter(endpoint=PHOENIX_ENDPOINT, insecure=True, timeout=10)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    print(f"Tracing initialized pointing to {PHOENIX_ENDPOINT}")
except Exception as e:
    print(f"Warning: Failed to initialize OTLP exporter to {PHOENIX_ENDPOINT}: {e}")
    print("Tracing will be disabled.")

trace.set_tracer_provider(tracer_provider)

# Instrument LangChain/LangGraph and LiteLLM
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
LiteLLMInstrumentor().instrument(tracer_provider=tracer_provider)

app = FastAPI(title="DocIntel API")

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Must be False if origins is ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router)
app.include_router(chat_router)

# WebSocket endpoint
@app.websocket("/ws/progress/{doc_id}")
async def websocket_endpoint(websocket: WebSocket, doc_id: str):
    await progress_websocket(websocket, doc_id)

@app.get("/")
async def root():
    return {"message": "Welcome to DocIntel API"}
