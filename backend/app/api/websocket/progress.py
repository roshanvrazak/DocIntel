import asyncio
import json
import os
import redis.asyncio as redis
import logging
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

class ConnectionManager:
    def __init__(self):
        # Map of doc_id to list of WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis_client = redis.from_url(REDIS_URL)
        self.listening_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, doc_id: str):
        await websocket.accept()
        if doc_id not in self.active_connections:
            self.active_connections[doc_id] = []
        self.active_connections[doc_id].append(websocket)
        logger.info(f"Client connected for doc_id: {doc_id}")
        
        # Start listening to Redis if not already doing so
        if doc_id not in self.listening_tasks:
            self.listening_tasks[doc_id] = asyncio.create_task(self.listen_to_redis(doc_id))

    def disconnect(self, websocket: WebSocket, doc_id: str):
        if doc_id in self.active_connections:
            self.active_connections[doc_id].remove(websocket)
            logger.info(f"Client disconnected for doc_id: {doc_id}")
            if not self.active_connections[doc_id]:
                # Stop listening to Redis if no more clients for this doc_id
                if doc_id in self.listening_tasks:
                    self.listening_tasks[doc_id].cancel()
                    del self.listening_tasks[doc_id]
                del self.active_connections[doc_id]

    async def broadcast(self, doc_id: str, message: dict):
        if doc_id in self.active_connections:
            to_remove = []
            for connection in self.active_connections[doc_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    to_remove.append(connection)
            
            for connection in to_remove:
                self.disconnect(connection, doc_id)

    async def listen_to_redis(self, doc_id: str):
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"progress:{doc_id}")
        logger.info(f"Started listening to Redis for doc_id: {doc_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self.broadcast(doc_id, data)
        except asyncio.CancelledError:
            logger.info(f"Stopped listening to Redis for doc_id: {doc_id}")
            await pubsub.unsubscribe(f"progress:{doc_id}")
        except Exception as e:
            logger.error(f"Error listening to Redis for doc_id {doc_id}: {str(e)}")
        finally:
            await pubsub.close()

manager = ConnectionManager()

async def progress_websocket(websocket: WebSocket, doc_id: str):
    await manager.connect(websocket, doc_id)
    try:
        while True:
            # We don't expect messages from clients, but we keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, doc_id)
    except Exception:
        manager.disconnect(websocket, doc_id)
