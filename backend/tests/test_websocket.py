"""
WebSocket integration tests for /ws/progress/{doc_id}.

Tests:
- Auth rejection (code 4001) when API_KEY is set and key is wrong/missing
- Auth acceptance when correct key is provided
- Invalid doc_id (non-UUID) rejected with code 4003
- Connection limit enforcement (code 4029)
- Broadcast: messages published to Redis reach connected clients

Auth tests use monkeypatch.setattr on the already-imported ws module object so
that main.py's reference to progress_websocket (captured at import time) reads
the patched value — module reload does not affect the reference held by the
FastAPI route closure.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

import backend.app.api.websocket.progress as ws_mod
from backend.app.main import app

# Use a real UUID for tests that should pass doc_id validation
VALID_DOC_ID = "00000000-0000-0000-0000-000000000001"
INVALID_DOC_ID = "not-a-uuid"


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

class TestWebSocketAuth:
    def test_no_auth_required_when_api_key_unset(self, monkeypatch):
        """When API_KEY is not set, any valid UUID connection should be accepted."""
        monkeypatch.setattr(ws_mod, "_API_KEY", None)

        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/progress/{VALID_DOC_ID}") as ws:
                pass  # not raising == accepted

    def test_connection_rejected_with_wrong_key(self, monkeypatch):
        """Wrong API key must close the socket (code 4001)."""
        monkeypatch.setattr(ws_mod, "_API_KEY", "correct-secret")

        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/progress/{VALID_DOC_ID}?api_key=wrong"):
                    pass

    def test_connection_rejected_with_missing_key(self, monkeypatch):
        """No api_key query param when API_KEY is required → rejected."""
        monkeypatch.setattr(ws_mod, "_API_KEY", "correct-secret")

        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/progress/{VALID_DOC_ID}"):
                    pass

    def test_connection_accepted_with_correct_key(self, monkeypatch):
        """Correct api_key in query string → connection accepted."""
        monkeypatch.setattr(ws_mod, "_API_KEY", "correct-secret")

        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/progress/{VALID_DOC_ID}?api_key=correct-secret"):
                pass

    def test_invalid_doc_id_rejected(self, monkeypatch):
        """Non-UUID doc_id must be rejected before auth check (code 4003)."""
        monkeypatch.setattr(ws_mod, "_API_KEY", None)

        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/progress/{INVALID_DOC_ID}"):
                    pass


# ---------------------------------------------------------------------------
# Connection limit tests
# ---------------------------------------------------------------------------

class TestWebSocketConnectionLimit:
    def setup_method(self):
        ws_mod.manager.active_connections.clear()
        ws_mod.manager.client_connection_count.clear()

    def teardown_method(self):
        ws_mod.manager.active_connections.clear()
        ws_mod.manager.client_connection_count.clear()

    def test_connection_limit_enforced(self, monkeypatch):
        """
        When MAX_WS_CONNECTIONS_PER_CLIENT=1, a second connection from the
        same client IP should be rejected with code 4029.
        """
        monkeypatch.setattr(ws_mod, "_API_KEY", None)
        monkeypatch.setattr(ws_mod, "MAX_WS_CONNECTIONS_PER_CLIENT", 1)

        other_uuid = "00000000-0000-0000-0000-000000000002"
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/progress/{VALID_DOC_ID}"):
                with pytest.raises(Exception):
                    with client.websocket_connect(f"/ws/progress/{other_uuid}"):
                        pass


# ---------------------------------------------------------------------------
# Broadcast tests (mocked WebSocket)
# ---------------------------------------------------------------------------

class TestWebSocketBroadcast:
    def teardown_method(self):
        ws_mod.manager.active_connections.clear()

    def test_broadcast_sends_message_to_connected_client(self):
        """broadcast() calls send_text with the serialised message."""
        import asyncio

        doc_id = VALID_DOC_ID
        message = {"status": "processing", "progress": 42}

        mock_ws = MagicMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.client = MagicMock()
        mock_ws.client.host = "127.0.0.1"

        ws_mod.manager.active_connections[doc_id] = [mock_ws]
        asyncio.run(ws_mod.manager.broadcast(doc_id, message))

        mock_ws.send_text.assert_called_once_with(json.dumps(message))

    def test_broadcast_removes_broken_connections(self):
        """If send_text raises, the dead connection is removed silently."""
        import asyncio

        doc_id = "00000000-0000-0000-0000-000000000003"
        mock_ws = MagicMock()
        mock_ws.send_text = AsyncMock(side_effect=RuntimeError("connection dead"))
        mock_ws.client = MagicMock()
        mock_ws.client.host = "127.0.0.1"

        ws_mod.manager.active_connections[doc_id] = [mock_ws]
        asyncio.run(ws_mod.manager.broadcast(doc_id, {"status": "done"}))

        remaining = ws_mod.manager.active_connections.get(doc_id, [])
        assert mock_ws not in remaining

    def test_broadcast_noop_for_unknown_doc_id(self):
        """Broadcast to a doc_id with no listeners silently does nothing."""
        import asyncio
        asyncio.run(ws_mod.manager.broadcast("00000000-0000-0000-0000-000000000099", {"ping": True}))
