# REST API Contract

**Base URL**: `https://{railway-host}/api/v1`
**Format**: JSON — `Content-Type: application/json`
**Auth**: None (internal tool; add bearer token if exposing publicly)
**Versioning**: URL path (`/api/v1/`)

---

## Endpoints

### GET /matches

Returns all 64 World Cup matches with their current state and latest prediction.

**Query parameters**:
| Param | Type | Values | Default |
|-------|------|--------|---------|
| `status` | string | `scheduled\|live\|finished\|all` | `all` |
| `stage` | string | `"Group A"`, `"Round of 16"`, etc. | (all stages) |

**Response `200 OK`**:
```json
{
  "matches": [
    {
      "id": 1,
      "home_team": {
        "id": 5,
        "name": "France",
        "country_code": "FRA",
        "fifa_ranking": 2
      },
      "away_team": {
        "id": 12,
        "name": "Argentina",
        "country_code": "ARG",
        "fifa_ranking": 1
      },
      "scheduled_at": "2026-06-15T18:00:00Z",
      "venue": "MetLife Stadium",
      "stage": "Group D",
      "status": "live",
      "home_score": 1,
      "away_score": 0,
      "latest_prediction": {
        "home_win_prob": 0.58,
        "draw_prob": 0.22,
        "away_win_prob": 0.20,
        "expected_home_goals": 1.6,
        "expected_away_goals": 1.1,
        "confidence_low": 0.50,
        "confidence_high": 0.66,
        "model_version": "1.0.0",
        "prediction_type": "live",
        "updated_at": "2026-06-15T18:32:10Z"
      }
    }
  ],
  "total": 64,
  "live_count": 2
}
```

---

### GET /matches/{match_id}

Full match detail: team info, live event log, current prediction with factors.

**Path params**: `match_id` — integer

**Response `200 OK`**:
```json
{
  "id": 1,
  "home_team": { "id": 5, "name": "France", "country_code": "FRA", "fifa_ranking": 2, "form_points": 12 },
  "away_team": { "id": 12, "name": "Argentina", "country_code": "ARG", "fifa_ranking": 1, "form_points": 13 },
  "scheduled_at": "2026-06-15T18:00:00Z",
  "venue": "MetLife Stadium",
  "city": "East Rutherford, NJ",
  "stage": "Group D",
  "status": "live",
  "home_score": 1,
  "away_score": 0,
  "prediction": {
    "id": 203,
    "home_win_prob": 0.58,
    "draw_prob": 0.22,
    "away_win_prob": 0.20,
    "expected_home_goals": 1.6,
    "expected_away_goals": 1.1,
    "confidence_low": 0.50,
    "confidence_high": 0.66,
    "top_factors": [
      { "feature": "current_score_diff", "impact_pct": 18.5, "label": "France leads 1-0 at minute 34" },
      { "feature": "fifa_ranking_diff",  "impact_pct": 5.2,  "label": "Argentina ranked #1 globally" },
      { "feature": "h2h_home_win_rate",  "impact_pct": 3.1,  "label": "France won 4 of last 10 H2H meetings" }
    ],
    "model_version": "1.0.0",
    "prediction_type": "live",
    "updated_at": "2026-06-15T18:32:10Z"
  },
  "live_events": [
    {
      "id": 45,
      "event_type": "goal",
      "team": "France",
      "player_name": "Kylian Mbappé",
      "minute": 34,
      "extra_minute": null,
      "home_score_after": 1,
      "away_score_after": 0
    }
  ]
}
```

**Response `404 Not Found`**:
```json
{ "detail": "Match 999 not found" }
```

---

### GET /predictions/{match_id}/latest

Latest prediction only — lightweight, used by the WebSocket fallback.

**Response `200 OK`**: Same as the `prediction` object in `/matches/{id}` above.

**Response `404`**: `{ "detail": "No prediction found for match {match_id}" }`

---

### GET /predictions/{match_id}/history

Time series of all predictions for a match — used to render the probability drift chart.

**Response `200 OK`**:
```json
{
  "match_id": 1,
  "predictions": [
    {
      "id": 200,
      "home_win_prob": 0.51,
      "draw_prob": 0.28,
      "away_win_prob": 0.21,
      "prediction_type": "prematch",
      "triggering_event": null,
      "created_at": "2026-06-15T17:00:00Z"
    },
    {
      "id": 203,
      "home_win_prob": 0.58,
      "draw_prob": 0.22,
      "away_win_prob": 0.20,
      "prediction_type": "live",
      "triggering_event": { "event_type": "goal", "minute": 34, "team": "France" },
      "created_at": "2026-06-15T18:32:10Z"
    }
  ]
}
```

---

### GET /accuracy

Tournament-wide prediction accuracy summary for the accuracy panel.

**Response `200 OK`**:
```json
{
  "overall": {
    "correct": 18,
    "total": 26,
    "accuracy_pct": 69.2
  },
  "by_stage": [
    { "stage": "Group A", "correct": 3, "total": 4, "accuracy_pct": 75.0 },
    { "stage": "Group B", "correct": 2, "total": 3, "accuracy_pct": 66.7 },
    { "stage": "Round of 16", "correct": 5, "total": 8, "accuracy_pct": 62.5 }
  ],
  "notable_misses": [
    {
      "match_id": 7,
      "predicted": "home_win",
      "actual": "away_win",
      "home_team": "Germany",
      "away_team": "Japan",
      "confidence": 0.78
    }
  ],
  "last_updated": "2026-06-21T10:00:00Z"
}
```

---

### GET /health

Health check — used by Railway's health probe.

**Response `200 OK`**:
```json
{
  "status": "ok",
  "db": "connected",
  "active_model": "1.0.0",
  "live_matches": 2,
  "timestamp": "2026-06-21T14:00:00Z"
}
```

---

### POST /admin/events/simulate *(development only, disabled in production)*

Inject a fake live event for testing the prediction pipeline without a live match.

**Request body**:
```json
{
  "match_id": 1,
  "event_type": "goal",
  "team_id": 5,
  "player_name": "Test Player",
  "minute": 45,
  "home_score_after": 2,
  "away_score_after": 0
}
```

**Response `200 OK`**: Returns the newly computed prediction object.
**Disabled check**: Returns `403 Forbidden` with `{"detail": "Simulation disabled in production"}` if `ENVIRONMENT != 'development'`.

---

## Error Schema (all endpoints)

```json
{
  "detail": "Human-readable error message",
  "code": "OPTIONAL_ERROR_CODE"
}
```

Standard HTTP status codes:
- `400` — Bad request (invalid query params, failed validation)
- `404` — Resource not found
- `422` — Pydantic validation error (FastAPI default)
- `500` — Internal server error (logged, never exposes stack traces)
- `503` — Service unavailable (DB unreachable, model not loaded)
