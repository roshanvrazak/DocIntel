import asyncio
import json
import os
import redis.asyncio as redis
import logging
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_API_KEY = os.getenv("API_KEY")
MAX_WS_CONNECTIONS_PER_CLIENT = int(os.getenv("MAX_WS_CONNECTIONS_PER_CLIENT", "5"))


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Track connection count per client IP
        self.client_connection_count: Dict[str, int] = {}
        self.redis_client = redis.from_url(REDIS_URL)
        self.listening_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, doc_id: str) -> bool:
        client_ip = websocket.client.host if websocket.client else "unknown"
        current_count = self.client_connection_count.get(client_ip, 0)
        if current_count >= MAX_WS_CONNECTIONS_PER_CLIENT:
            await websocket.close(code=4029)
            logger.warning(
                "WebSocket connection limit reached for client %s (doc_id: %s)", client_ip, doc_id
            )
            return False

        await websocket.accept()
        self.client_connection_count[client_ip] = current_count + 1
        if doc_id not in self.active_connections:
            self.active_connections[doc_id] = []
        self.active_connections[doc_id].append(websocket)
        logger.info("Client %s connected for doc_id: %s", client_ip, doc_id)
        return True

        if doc_id not in self.listening_tasks:
            self.listening_tasks[doc_id] = asyncio.create_task(self.listen_to_redis(doc_id))

    def disconnect(self, websocket: WebSocket, doc_id: str):
        client_ip = websocket.client.host if websocket.client else "unknown"
        if doc_id in self.active_connections and websocket in self.active_connections[doc_id]:
            self.active_connections[doc_id].remove(websocket)
            count = self.client_connection_count.get(client_ip, 1)
            self.client_connection_count[client_ip] = max(0, count - 1)
            logger.info("Client %s disconnected for doc_id: %s", client_ip, doc_id)
            if not self.active_connections[doc_id]:
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
        logger.info("Started listening to Redis for doc_id: %s", doc_id)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self.broadcast(doc_id, data)
        except asyncio.CancelledError:
            logger.info("Stopped listening to Redis for doc_id: %s", doc_id)
            await pubsub.unsubscribe(f"progress:{doc_id}")
        except Exception as e:
            logger.error("Error listening to Redis for doc_id %s: %s", doc_id, str(e))
        finally:
            await pubsub.close()


manager = ConnectionManager()


async def progress_websocket(websocket: WebSocket, doc_id: str):
    # Validate API key from query param (browser WS doesn't support custom headers)
    if _API_KEY:
        provided_key = websocket.query_params.get("api_key")
        if provided_key != _API_KEY:
            await websocket.close(code=4001)
            logger.warning("WebSocket rejected for doc_id %s: invalid API key", doc_id)
            return

    connected = await manager.connect(websocket, doc_id)
    if not connected:
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, doc_id)
    except Exception:
        manager.disconnect(websocket, doc_id)
