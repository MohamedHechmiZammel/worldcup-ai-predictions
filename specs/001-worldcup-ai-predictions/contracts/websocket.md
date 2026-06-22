# WebSocket Contract

**Endpoint**: `wss://{railway-host}/ws/matches/{match_id}`
**Protocol**: JSON messages over WebSocket (RFC 6455)
**Auth**: None (same policy as REST API)

---

## Connection Lifecycle

```
Client                              Server (Railway FastAPI)
  │                                       │
  │── WS handshake: GET /ws/matches/1 ──→ │  accept()
  │                                       │  register in ConnectionManager
  │ ←──── {"type": "connected", ...} ──── │
  │                                       │
  │  [match event arrives from API]        │
  │ ←── {"type": "prediction_update"} ─── │  broadcast to all match subscribers
  │ ←── {"type": "live_event"} ────────── │
  │                                       │
  │   [every 30 seconds]                  │
  │ ←──── {"type": "ping"} ────────────── │  keep-alive (Railway ~60s idle timeout)
  │───── {"type": "pong"} ─────────────→  │
  │                                       │
  │  [client navigates away]              │
  │── WS close frame ──────────────────→  │  WebSocketDisconnect → unregister
  │                                       │
```

---

## Message Envelope (all messages)

Every message — both directions — uses this envelope:

```json
{
  "type": "<message_type>",
  "match_id": "1",
  "payload": { ... },
  "timestamp": "2026-06-21T14:00:00Z"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | ✅ | Identifies message purpose; drives client dispatch |
| `match_id` | ✅ (server→client) | Which match this message concerns |
| `payload` | ✅ | Message-specific data (may be `{}` for ping/pong) |
| `timestamp` | ✅ | ISO-8601 UTC — use to detect stale messages |

---

## Server → Client Message Types

### `connected`

Sent immediately after the WebSocket is accepted.

```json
{
  "type": "connected",
  "match_id": "1",
  "payload": {
    "status": "live",
    "current_prediction": {
      "home_win_prob": 0.51,
      "draw_prob": 0.28,
      "away_win_prob": 0.21
    }
  },
  "timestamp": "2026-06-21T14:00:00Z"
}
```

Purpose: Client immediately renders a prediction without waiting for the next poll cycle.

---

### `prediction_update`

Sent whenever the prediction engine produces a new prediction for this match.
Triggered by: a new live event, the half-time whistle, or the opening whistle.

```json
{
  "type": "prediction_update",
  "match_id": "1",
  "payload": {
    "prediction_id": 204,
    "home_win_prob": 0.62,
    "draw_prob": 0.20,
    "away_win_prob": 0.18,
    "expected_home_goals": 1.8,
    "expected_away_goals": 1.0,
    "confidence_low": 0.54,
    "confidence_high": 0.70,
    "top_factors": [
      { "feature": "current_score_diff", "impact_pct": 22.1, "label": "France leads 2-0 at minute 58" },
      { "feature": "red_cards_away",     "impact_pct": 9.4,  "label": "Argentina down to 10 men since minute 52" },
      { "feature": "fifa_ranking_diff",  "impact_pct": 4.8,  "label": "Argentina ranked #1 globally" }
    ],
    "model_version": "1.0.0",
    "prediction_type": "live"
  },
  "timestamp": "2026-06-21T14:32:10Z"
}
```

Client behavior: Animate the probability bars to the new values.

---

### `live_event`

Sent immediately when a new event is ingested — before the prediction is recomputed.
Lets the client show the event in the live log with zero latency.

```json
{
  "type": "live_event",
  "match_id": "1",
  "payload": {
    "event_id": 45,
    "event_type": "red_card",
    "team": "Argentina",
    "player_name": "Rodrigo De Paul",
    "minute": 52,
    "home_score": 1,
    "away_score": 0
  },
  "timestamp": "2026-06-21T14:30:05Z"
}
```

Client behavior: Append to the live event log. Show toast notification.
A `prediction_update` follows within a few seconds.

---

### `match_status_change`

Sent when match status transitions (kickoff, halftime, fulltime, postponed).

```json
{
  "type": "match_status_change",
  "match_id": "1",
  "payload": {
    "previous_status": "live",
    "new_status": "halftime",
    "home_score": 1,
    "away_score": 0
  },
  "timestamp": "2026-06-21T14:45:00Z"
}
```

Client behavior: Update the status badge; freeze probability bars during halftime.
On `finished`, replace prediction with actual result.

---

### `feed_status`

Sent when the live data feed becomes unavailable or recovers.

```json
{
  "type": "feed_status",
  "match_id": "1",
  "payload": {
    "available": false,
    "last_event_at": "2026-06-21T14:32:10Z",
    "reason": "API rate limit exceeded"
  },
  "timestamp": "2026-06-21T14:34:00Z"
}
```

Client behavior: Show/hide the "Live data unavailable" badge (FR-008).

---

### `ping`

Keep-alive heartbeat sent by the server every 30 seconds.

```json
{ "type": "ping", "match_id": "1", "payload": {}, "timestamp": "..." }
```

---

## Client → Server Message Types

### `pong`

Response to server `ping`. Required to keep Railway connection alive.

```json
{ "type": "pong", "match_id": "1", "payload": {}, "timestamp": "..." }
```

---

## Error Handling

If the server sends an unexpected message type, the client MUST ignore it (forward
compatibility — new message types may be added in future versions).

If the WebSocket connection drops, the client MUST reconnect with exponential backoff:
- Attempt 1: 1 second delay
- Attempt 2: 2 seconds
- Attempt 3: 4 seconds
- Max: 30 seconds
- After 5 failed reconnects: show "Reconnecting..." banner and continue trying.

The server cleans up the connection from `ConnectionManager` on `WebSocketDisconnect`.
No explicit unsubscribe message is needed.

---

## Concurrency Note

A single client connecting to `/ws/matches/1` subscribes to match 1 only.
If the user wants live updates for the full tournament overview (multiple live matches),
the frontend opens one WebSocket connection per live match.

Maximum concurrent WebSocket connections per Railway instance:
- Default Railway process: ~512 open file descriptors
- At <50 users × 4 simultaneous live matches = <200 connections: comfortably within limits.
