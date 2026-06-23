from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import settings
from app.core.database import get_db
from app.models.live_event import LiveEvent
from app.models.match import Match
from app.models.team import Team
from app.schemas.prediction import PredictionResponse, FactorItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Auth guard — set ADMIN_KEY env var to allow admin endpoints in production
# ---------------------------------------------------------------------------

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
WC2026_START = date(2026, 6, 11)

# ESPN abbreviation → our country_code (add entries when ESPN diverges from FIFA codes)
ESPN_TO_CODE: dict[str, str] = {
    "USA": "USA", "MEX": "MEX", "CAN": "CAN", "GER": "GER", "FRA": "FRA",
    "BRA": "BRA", "ARG": "ARG", "ENG": "ENG", "ESP": "ESP", "NED": "NED",
    "POR": "POR", "BEL": "BEL", "URU": "URU", "JPN": "JPN", "SWE": "SWE",
    "AUS": "AUS", "TUR": "TUR", "KOR": "KOR", "MAR": "MAR", "SEN": "SEN",
    "EGY": "EGY", "GHA": "GHA", "CRO": "CRO", "SUI": "SUI", "NOR": "NOR",
    "AUT": "AUT", "COL": "COL", "ECU": "ECU", "PAR": "PAR", "JOR": "JOR",
    "ALG": "ALG", "IRN": "IRN", "IRQ": "IRQ", "KSA": "KSA", "QAT": "QAT",
    "NZL": "NZL", "SCO": "SCO", "HAI": "HAI", "PAN": "PAN", "CUW": "CUW",
    "CIV": "CIV", "TUN": "TUN", "BIH": "BIH", "CZE": "CZE", "RSA": "RSA",
    "CPV": "CPV", "COD": "COD", "UZB": "UZB",
    # Alternate ESPN abbreviations
    "ZAF": "RSA", "HTI": "HAI", "DRC": "COD", "CRC": "CRC",
    "WAL": "WAL", "BAH": "BIH",
}


async def _require_admin(x_admin_key: str = Header(default="")) -> None:
    """Default-deny admin gate: blocks unless ADMIN_KEY is configured AND matches."""
    if not settings.admin_key:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoints are disabled: set the ADMIN_KEY environment variable.",
        )
    if not secrets.compare_digest(x_admin_key, settings.admin_key):
        raise HTTPException(status_code=401, detail="Invalid X-Admin-Key header")


# ---------------------------------------------------------------------------
# Manual result update
# ---------------------------------------------------------------------------

class MatchResultRequest(BaseModel):
    home_score: int
    away_score: int
    status: str = "finished"


@router.patch("/matches/{match_id}", dependencies=[Depends(_require_admin)])
async def update_match_result(
    match_id: int,
    body: MatchResultRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually set a match result and trigger Elo learning pipeline."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    previous_status = match.status
    await db.execute(
        update(Match)
        .where(Match.id == match_id)
        .values(home_score=body.home_score, away_score=body.away_score, status=body.status)
    )
    await db.commit()

    if body.status == "finished" and previous_status != "finished":
        from app.services.ingestion import _record_accuracy_and_learn
        asyncio.create_task(_record_accuracy_and_learn(match_id, body.home_score, body.away_score))
        from app.services.broadcast import manager
        asyncio.create_task(manager.broadcast_all({"type": "accuracy_update"}))

    return {"ok": True, "match_id": match_id, "home_score": body.home_score, "away_score": body.away_score}


# ---------------------------------------------------------------------------
# ESPN historical sync
# ---------------------------------------------------------------------------

class ESPNSyncRequest(BaseModel):
    start_date: str | None = None  # YYYY-MM-DD, defaults to WC kickoff date
    end_date: str | None = None    # YYYY-MM-DD, defaults to today


@router.post("/sync-espn", dependencies=[Depends(_require_admin)])
async def sync_espn_results(
    body: ESPNSyncRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fetch finished match results from ESPN and update the database.

    Iterates over each day in the date range, fetches the ESPN scoreboard,
    and for each finished match tries to find and update the corresponding
    row in our matches table by home/away country code.

    Set ADMIN_KEY env var on Render, then call:
      curl -X POST https://<backend>/api/v1/admin/sync-espn \\
           -H 'X-Admin-Key: <your-key>'
    """
    body = body or ESPNSyncRequest()

    start = date.fromisoformat(body.start_date) if body.start_date else WC2026_START
    end = date.fromisoformat(body.end_date) if body.end_date else date.today()

    updated: list[dict] = []
    skipped: list[str] = []
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        current = start
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            try:
                resp = await client.get(ESPN_SCOREBOARD, params={"dates": date_str})
                resp.raise_for_status()
                events = resp.json().get("events", [])
            except Exception as exc:
                errors.append(f"{date_str}: fetch failed — {exc}")
                current += timedelta(days=1)
                continue

            for event in events:
                try:
                    result = await _process_espn_event(event, db)
                    if result == "updated":
                        comp = event.get("competitions", [{}])[0]
                        teams = {c.get("homeAway"): c.get("team", {}).get("abbreviation", "?")
                                 for c in comp.get("competitors", [])}
                        updated.append({
                            "date": date_str,
                            "home": ESPN_TO_CODE.get(teams.get("home", ""), teams.get("home", "?")),
                            "away": ESPN_TO_CODE.get(teams.get("away", ""), teams.get("away", "?")),
                        })
                    elif result:
                        skipped.append(f"{date_str}:{result}")
                except Exception as exc:
                    errors.append(f"{date_str}: event error — {exc}")

            await db.commit()
            current += timedelta(days=1)

    return {
        "ok": True,
        "updated_count": len(updated),
        "updated": updated,
        "skipped_count": len(skipped),
        "skipped_samples": skipped[:20],
        "errors": errors,
    }


async def _process_espn_event(event: dict, db: AsyncSession) -> str:
    """Process one ESPN event and update our DB. Returns 'updated', 'skipped:<reason>', or ''."""
    status_state = event.get("status", {}).get("type", {}).get("state", "pre")
    if status_state != "post":
        return "skipped:not_finished"

    competitions = event.get("competitions", [{}])
    if not competitions:
        return "skipped:no_competitions"
    comp = competitions[0]

    home_code = ""
    away_code = ""
    home_score = 0
    away_score = 0

    for competitor in comp.get("competitors", []):
        abbr = competitor.get("team", {}).get("abbreviation", "")
        our_code = ESPN_TO_CODE.get(abbr, abbr)
        score = int(competitor.get("score", "0") or 0)
        if competitor.get("homeAway") == "home":
            home_code = our_code
            home_score = score
        else:
            away_code = our_code
            away_score = score

    if not home_code or not away_code:
        return "skipped:missing_team_codes"

    # Find the match in our DB by team country codes + not-yet-finished status
    HomeTeam = aliased(Team)
    AwayTeam = aliased(Team)
    stmt = (
        select(Match)
        .join(HomeTeam, Match.home_team_id == HomeTeam.id)
        .join(AwayTeam, Match.away_team_id == AwayTeam.id)
        .where(
            HomeTeam.country_code == home_code,
            AwayTeam.country_code == away_code,
        )
    )
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()

    if match is None:
        logger.warning("ESPN sync: no match found for %s vs %s", home_code, away_code)
        return f"skipped:no_match_{home_code}_vs_{away_code}"

    if match.status == "finished" and match.home_score == home_score and match.away_score == away_score:
        return "skipped:already_up_to_date"

    previous_status = match.status
    await db.execute(
        update(Match)
        .where(Match.id == match.id)
        .values(home_score=home_score, away_score=away_score, status="finished",
                external_id=f"espn_{event.get('id', '')}")
    )

    if previous_status != "finished":
        asyncio.create_task(
            _record_accuracy_and_learn_bg(match.id, home_score, away_score)
        )

    return "updated"


async def _record_accuracy_and_learn_bg(match_id: int, home_score: int, away_score: int) -> None:
    """Fire-and-forget wrapper so the sync endpoint doesn't block on Elo recalc."""
    from app.services.ingestion import _record_accuracy_and_learn
    await _record_accuracy_and_learn(match_id, home_score, away_score)


# ---------------------------------------------------------------------------
# Event simulation (dev only)
# ---------------------------------------------------------------------------

class SimulateEventRequest(BaseModel):
    match_id: int
    event_type: str = "goal"
    minute: int = 45
    home_score_after: int = 1
    away_score_after: int = 0
    player_name: str | None = None
    team_code: str | None = None


@router.post("/events/simulate", response_model=PredictionResponse | None)
async def simulate_event(
    body: SimulateEventRequest,
    db: AsyncSession = Depends(get_db),
) -> PredictionResponse | None:
    if settings.environment not in ("development", "test"):
        raise HTTPException(status_code=403, detail="Simulation only available in development")

    from app.services.prediction_engine import prediction_engine
    from app.services.broadcast import manager
    import uuid

    fake_id = f"sim_{uuid.uuid4().hex[:8]}"
    event = LiveEvent(
        match_id=body.match_id,
        external_event_id=fake_id,
        event_type=body.event_type,
        player_name=body.player_name,
        minute=body.minute,
        extra_minute=None,
        home_score_after=body.home_score_after,
        away_score_after=body.away_score_after,
        raw_payload={"simulated": True},
    )
    db.add(event)
    await db.flush()

    await manager.broadcast_to_match(str(body.match_id), {
        "type": "live_event",
        "payload": {
            "id": event.id,
            "match_id": body.match_id,
            "event_type": body.event_type,
            "player_name": body.player_name,
            "minute": body.minute,
            "home_score_after": body.home_score_after,
            "away_score_after": body.away_score_after,
        }
    })

    result = await prediction_engine.predict_ingame(
        match_id=body.match_id,
        triggering_event_id=event.id,
        db=db,
    )

    if result is None:
        return None

    return PredictionResponse(
        id=0,
        match_id=body.match_id,
        prediction_type="live",
        home_win_prob=result.home_win_prob,
        draw_prob=result.draw_prob,
        away_win_prob=result.away_win_prob,
        expected_home_goals=result.expected_home_goals,
        expected_away_goals=result.expected_away_goals,
        confidence_low=result.confidence_low,
        confidence_high=result.confidence_high,
        top_factors=[FactorItem(**f) for f in result.top_factors],
    )
