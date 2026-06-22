from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by match_id.

    Thread-safety note: asyncio is single-threaded; all operations run
    in the same event loop so no locking is needed. The broadcast method
    collects dead sockets before removal to avoid mutating the set during
    iteration.
    """

    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)

    def connect(self, match_id: str, ws: WebSocket) -> None:
        self.rooms[match_id].add(ws)
        logger.debug("WS connect: match_id=%s total=%d", match_id, len(self.rooms[match_id]))

    def disconnect(self, match_id: str, ws: WebSocket) -> None:
        self.rooms[match_id].discard(ws)
        if not self.rooms[match_id]:
            del self.rooms[match_id]
        logger.debug("WS disconnect: match_id=%s", match_id)

    async def broadcast_to_match(self, match_id: str, data: dict) -> None:
        """Send JSON data to all connections for a match.

        Collects dead sockets first, then removes them — never modifies
        the set during iteration to avoid RuntimeError.
        """
        dead: set[WebSocket] = set()
        for ws in self.rooms.get(match_id, set()):
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(match_id, ws)

    def room_count(self, match_id: str) -> int:
        return len(self.rooms.get(match_id, set()))

    def total_connections(self) -> int:
        return sum(len(conns) for conns in self.rooms.values())

    async def broadcast_all(self, data: dict) -> None:
        """Send JSON data to all connected clients in all rooms."""
        dead_by_room: dict[str, set[WebSocket]] = {}
        for room_id, sockets in list(self.rooms.items()):
            dead: set[WebSocket] = set()
            for ws in sockets:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.add(ws)
            if dead:
                dead_by_room[room_id] = dead
        for room_id, dead in dead_by_room.items():
            for ws in dead:
                self.disconnect(room_id, ws)


# Module-level singleton shared across the application
manager = ConnectionManager()
