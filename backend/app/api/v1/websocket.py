from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.broadcast import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/matches/{match_id}")
async def websocket_endpoint(ws: WebSocket, match_id: str) -> None:
    await ws.accept()
    manager.connect(match_id, ws)
    await ws.send_json({"type": "connected", "match_id": match_id})
    try:
        while True:
            # 30s ping prevents Railway from closing idle WebSocket connections
            await asyncio.sleep(30)
            await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(match_id, ws)
