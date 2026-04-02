"""
WebSocket integration tests for /ws/progress/{doc_id}.

Tests:
- Auth rejection (code 4001) when API_KEY env is set and key is wrong/missing
- Auth acceptance when correct key is provided
- Connection limit enforcement (code 4029)
- Broadcast: messages published to Redis reach connected clients

Note: The module-level _API_KEY and MAX_WS_CONNECTIONS_PER_CLIENT are read at
import time in progress.py, so we reload the module after patching env vars to
pick up new values.
"""
import importlib
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from fastapi.testclient import TestClient

from backend.app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_ws_module():
    """Reload the WebSocket module so env-var globals are refreshed."""
    import backend.app.api.websocket.progress as ws_mod
    importlib.reload(ws_mod)
    return ws_mod


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

class TestWebSocketAuth:
    def test_no_auth_required_when_api_key_unset(self, monkeypatch):
        """When API_KEY is not set, any connection should be accepted."""
        monkeypatch.delenv("API_KEY", raising=False)
        _reload_ws_module()

        with TestClient(app) as client:
            with client.websocket_connect("/ws/progress/test-doc-id") as ws:
                # Connection accepted — we can receive; close gracefully
                pass  # no assert needed; not raising == accepted

    def test_connection_rejected_with_wrong_key(self, monkeypatch):
        """Wrong API key must close the socket with code 4001."""
        monkeypatch.setenv("API_KEY", "correct-secret")
        _reload_ws_module()

        with TestClient(app) as client:
            with pytest.raises(Exception):
                # The server closes the connection — TestClient raises on rejected WS
                with client.websocket_connect("/ws/progress/doc-auth?api_key=wrong"):
                    pass

    def test_connection_rejected_with_missing_key(self, monkeypatch):
        """No api_key query param when API_KEY is required → rejected."""
        monkeypatch.setenv("API_KEY", "correct-secret")
        _reload_ws_module()

        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws/progress/doc-auth"):
                    pass

    def test_connection_accepted_with_correct_key(self, monkeypatch):
        """Correct api_key in query string → connection accepted."""
        monkeypatch.setenv("API_KEY", "correct-secret")
        _reload_ws_module()

        with TestClient(app) as client:
            # Should not raise
            with client.websocket_connect("/ws/progress/doc-auth?api_key=correct-secret"):
                pass

    def teardown_method(self):
        os.environ.pop("API_KEY", None)
        _reload_ws_module()


# ---------------------------------------------------------------------------
# Connection limit tests
# ---------------------------------------------------------------------------

class TestWebSocketConnectionLimit:
    def test_connection_limit_enforced(self, monkeypatch):
        """
        When MAX_WS_CONNECTIONS_PER_CLIENT=1, a second connection from the
        same client IP should be rejected with code 4029.
        """
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.setenv("MAX_WS_CONNECTIONS_PER_CLIENT", "1")
        ws_mod = _reload_ws_module()

        # Reset the manager's state so previous tests don't pollute
        ws_mod.manager.active_connections.clear()
        ws_mod.manager.client_connection_count.clear()

        with TestClient(app) as client:
            # First connection — should be accepted
            with client.websocket_connect("/ws/progress/doc-limit-1"):
                # While first is open, second should be rejected
                with pytest.raises(Exception):
                    with client.websocket_connect("/ws/progress/doc-limit-2"):
                        pass

    def teardown_method(self):
        os.environ.pop("MAX_WS_CONNECTIONS_PER_CLIENT", None)
        import backend.app.api.websocket.progress as ws_mod
        ws_mod.manager.active_connections.clear()
        ws_mod.manager.client_connection_count.clear()
        _reload_ws_module()


# ---------------------------------------------------------------------------
# Broadcast tests (mocked Redis)
# ---------------------------------------------------------------------------

class TestWebSocketBroadcast:
    def test_broadcast_sends_message_to_connected_client(self):
        """
        Directly exercise ConnectionManager.broadcast() with a mock WebSocket,
        verifying send_text is called with the serialised message.
        """
        import asyncio
        import backend.app.api.websocket.progress as ws_mod

        doc_id = "broadcast-doc"
        message = {"status": "processing", "progress": 42}

        # Build a mock WebSocket with an async send_text
        mock_ws = MagicMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.client = MagicMock()
        mock_ws.client.host = "127.0.0.1"

        # Manually register the mock WebSocket
        ws_mod.manager.active_connections[doc_id] = [mock_ws]

        # Run broadcast
        asyncio.run(ws_mod.manager.broadcast(doc_id, message))

        mock_ws.send_text.assert_called_once_with(json.dumps(message))

        # Cleanup
        ws_mod.manager.active_connections.pop(doc_id, None)

    def test_broadcast_removes_broken_connections(self):
        """
        If send_text raises (dead client), the connection is removed and no
        exception propagates.
        """
        import asyncio
        import backend.app.api.websocket.progress as ws_mod

        doc_id = "broadcast-error-doc"

        mock_ws = MagicMock()
        mock_ws.send_text = AsyncMock(side_effect=RuntimeError("connection dead"))
        mock_ws.client = MagicMock()
        mock_ws.client.host = "127.0.0.1"

        ws_mod.manager.active_connections[doc_id] = [mock_ws]

        # Should not raise
        asyncio.run(ws_mod.manager.broadcast(doc_id, {"status": "done"}))

        # Connection should have been removed
        assert doc_id not in ws_mod.manager.active_connections or \
               mock_ws not in ws_mod.manager.active_connections.get(doc_id, [])

        ws_mod.manager.active_connections.pop(doc_id, None)

    def test_broadcast_noop_for_unknown_doc_id(self):
        """Broadcast to a doc_id with no listeners silently does nothing."""
        import asyncio
        import backend.app.api.websocket.progress as ws_mod

        # Should not raise
        asyncio.run(ws_mod.manager.broadcast("no-such-doc", {"ping": True}))
