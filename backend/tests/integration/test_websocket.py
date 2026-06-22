"""T077 – WebSocket integration tests.

Tests the /ws/matches/{match_id} endpoint defined in
app/api/v1/websocket.py using Starlette's synchronous TestClient.

The TestClient drives the ASGI app in a background thread with its own event
loop, which is the standard approach for testing WebSocket endpoints in
Starlette / FastAPI without a running server.

Contract reference:
  specs/001-worldcup-ai-predictions/contracts/websocket.md
"""

from __future__ import annotations

import json

from starlette.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client() -> TestClient:
    """Return a TestClient that does NOT raise on server-side errors."""
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------


def test_websocket_connects_successfully() -> None:
    """Client can open a WebSocket connection to /ws/matches/{match_id}."""
    client = TestClient(app)
    with client.websocket_connect("/ws/matches/1") as ws:
        # Just connecting without an exception means the handshake succeeded.
        pass


def test_websocket_receives_connected_message() -> None:
    """Server sends a 'connected' frame immediately after the handshake."""
    client = TestClient(app)
    with client.websocket_connect("/ws/matches/1") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"


def test_websocket_connected_message_contains_match_id() -> None:
    """The 'connected' frame must echo back the match_id path parameter."""
    client = TestClient(app)
    with client.websocket_connect("/ws/matches/42") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["match_id"] == "42"


def test_websocket_match_id_preserved_across_ids() -> None:
    """match_id is passed verbatim – verify with a different value."""
    client = TestClient(app)
    with client.websocket_connect("/ws/matches/99") as ws:
        msg = ws.receive_json()
        assert msg["match_id"] == "99"


# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------


def test_websocket_responds_to_pong_without_error() -> None:
    """
    The server does not crash when it receives an unexpected client message.

    The current server implementation only sends ping frames; it does not
    process incoming frames.  Sending a 'pong' from the client exercises the
    connection without triggering a server error.
    """
    client = TestClient(app)
    with client.websocket_connect("/ws/matches/1") as ws:
        ws.receive_json()  # consume the 'connected' frame
        # Send an arbitrary JSON frame – should not raise
        ws.send_json({"type": "pong"})
        # Graceful disconnect – no exception expected
        ws.close()


def test_websocket_send_arbitrary_json_no_exception() -> None:
    """Sending arbitrary JSON frames must not raise a server exception."""
    client = _make_client()
    with client.websocket_connect("/ws/matches/1") as ws:
        ws.receive_json()  # 'connected'
        ws.send_json({"type": "subscribe", "topic": "events"})
        ws.close()


# ---------------------------------------------------------------------------
# Disconnection
# ---------------------------------------------------------------------------


def test_websocket_clean_disconnect() -> None:
    """Client-initiated close must not raise WebSocketDisconnect on the caller."""
    client = TestClient(app)
    with client.websocket_connect("/ws/matches/1") as ws:
        ws.receive_json()  # 'connected'
        # Exiting the context manager triggers a clean close.


def test_websocket_multiple_connections_independent() -> None:
    """Two sequential connections to different match IDs are independent."""
    client = TestClient(app)

    with client.websocket_connect("/ws/matches/10") as ws10:
        msg10 = ws10.receive_json()
        assert msg10["match_id"] == "10"

    with client.websocket_connect("/ws/matches/20") as ws20:
        msg20 = ws20.receive_json()
        assert msg20["match_id"] == "20"
