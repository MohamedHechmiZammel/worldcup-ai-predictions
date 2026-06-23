from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.live_event import LiveEvent
from app.models.match import Match
from app.schemas.prediction import PredictionResponse, FactorItem

router = APIRouter(prefix="/admin", tags=["admin"])


class MatchResultRequest(BaseModel):
    home_score: int
    away_score: int
    status: str = "finished"


@router.patch("/matches/{match_id}")
async def update_match_result(
    match_id: int,
    body: MatchResultRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually set a match result (for testing or manual data entry).

    Updates the score and status, then triggers accuracy recording,
    Elo update, and re-prediction for remaining matches — the same
    pipeline as the automated ESPN ingestion.
    """
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
        import asyncio
        from app.services.ingestion import _record_accuracy_and_learn
        asyncio.create_task(_record_accuracy_and_learn(match_id, body.home_score, body.away_score))
        from app.services.broadcast import manager
        asyncio.create_task(manager.broadcast_all({"type": "accuracy_update"}))

    return {"ok": True, "match_id": match_id, "home_score": body.home_score, "away_score": body.away_score}


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

    # Insert fake LiveEvent
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

    # Broadcast the event
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

    # Trigger ingame prediction
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
