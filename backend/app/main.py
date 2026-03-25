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
from backend.app.api.websocket.progress import progress_websocket

# Initialize Arize Phoenix Tracing via OTLP gRPC
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://phoenix:4317")
resource = Resource(attributes={
    "service.name": "docintel-backend"
})

tracer_provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(endpoint=PHOENIX_ENDPOINT, insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router)

# WebSocket endpoint
@app.websocket("/ws/progress/{doc_id}")
async def websocket_endpoint(websocket: WebSocket, doc_id: str):
    await progress_websocket(websocket, doc_id)

@app.get("/")
async def root():
    return {"message": "Welcome to DocIntel API"}
