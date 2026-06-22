"""T076 – REST contract tests.

Verifies that every endpoint returns the correct HTTP status code and that the
response JSON contains the top-level keys specified in the REST API contract at
specs/001-worldcup-ai-predictions/contracts/rest-api.md.

These tests use the ASGI transport so they exercise the full FastAPI request /
response cycle without binding a real network socket.  The database session and
external services are NOT mocked here – the intent is a contract check against
a running app, not unit isolation.  If you need fully-isolated tests see
tests/unit/.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:  # type: ignore[override]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_status_200(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(client: AsyncClient) -> None:
    r = await client.get("/health")
    data = r.json()
    assert "status" in data, "health response must contain 'status'"
    assert "model_loaded" in data, "health response must contain 'model_loaded'"


# ---------------------------------------------------------------------------
# GET /api/v1/matches/
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_matches_list_status_200(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches/")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_matches_list_shape(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches/")
    data = r.json()
    assert "matches" in data, "matches list response must contain 'matches'"
    assert "total" in data, "matches list response must contain 'total'"
    assert "live_count" in data, "matches list response must contain 'live_count'"
    assert isinstance(data["matches"], list), "'matches' must be a list"


@pytest.mark.asyncio
async def test_matches_list_total_is_int(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches/")
    data = r.json()
    assert isinstance(data["total"], int), "'total' must be an integer"
    assert isinstance(data["live_count"], int), "'live_count' must be an integer"


@pytest.mark.asyncio
async def test_matches_list_item_shape(client: AsyncClient) -> None:
    """If any matches are returned, each item must carry the required keys."""
    r = await client.get("/api/v1/matches/")
    data = r.json()
    if not data["matches"]:
        pytest.skip("no matches in DB – shape check skipped")
    first = data["matches"][0]
    required_keys = {
        "id",
        "home_team_id",
        "away_team_id",
        "scheduled_at",
        "stage",
        "status",
    }
    missing = required_keys - first.keys()
    assert not missing, f"match item missing keys: {missing}"


# ---------------------------------------------------------------------------
# GET /api/v1/matches/{match_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_not_found_returns_404(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches/999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_match_not_found_has_detail_key(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches/999999")
    data = r.json()
    assert "detail" in data, "404 response must contain 'detail'"


# ---------------------------------------------------------------------------
# GET /api/v1/accuracy/
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accuracy_status_200(client: AsyncClient) -> None:
    r = await client.get("/api/v1/accuracy/")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_accuracy_shape(client: AsyncClient) -> None:
    r = await client.get("/api/v1/accuracy/")
    data = r.json()
    assert "total_predictions" in data, "accuracy response must contain 'total_predictions'"
    assert "correct_predictions" in data, "accuracy response must contain 'correct_predictions'"
    assert "accuracy_pct" in data, "accuracy response must contain 'accuracy_pct'"
    assert "by_stage" in data, "accuracy response must contain 'by_stage'"


@pytest.mark.asyncio
async def test_accuracy_numeric_fields(client: AsyncClient) -> None:
    r = await client.get("/api/v1/accuracy/")
    data = r.json()
    assert isinstance(data["total_predictions"], int)
    assert isinstance(data["correct_predictions"], int)
    assert isinstance(data["accuracy_pct"], float | int)
    assert data["accuracy_pct"] >= 0.0


# ---------------------------------------------------------------------------
# GET /api/v1/predictions/{match_id}/history  (contract: shape when no data)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prediction_history_not_found(client: AsyncClient) -> None:
    """Unknown match_id must return 404."""
    r = await client.get("/api/v1/predictions/999999/history")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_prediction_latest_not_found(client: AsyncClient) -> None:
    """Unknown match_id must return 404."""
    r = await client.get("/api/v1/predictions/999999/latest")
    assert r.status_code == 404
