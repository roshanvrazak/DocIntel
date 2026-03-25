from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes.upload import router as upload_router
from backend.app.api.websocket.progress import progress_websocket

app = FastAPI(title="DocIntel API")

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
