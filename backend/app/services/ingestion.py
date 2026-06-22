import asyncio
import logging
import httpx
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.match import Match
from app.models.live_event import LiveEvent
from app.services.provider.base import LiveMatchState
from app.services.provider.espn import ESPNAdapter
from app.services.provider.mock import MockProvider

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 15


def _get_provider():
    """Factory: return ESPN or Mock provider based on config."""
    if settings.football_api_provider == "espn":
        return ESPNAdapter()
    return MockProvider()


async def run_polling_loop() -> None:
    """Poll the live data provider every 15 seconds.

    For each event:
    1. Upsert into live_events with ON CONFLICT (external_event_id) DO NOTHING
    2. Only trigger prediction update if the row was actually inserted (affected_rows > 0)
    3. Broadcast the live_event WS message immediately
    4. Then trigger predict_ingame() (which also broadcasts prediction_update)
    """
    provider = _get_provider()

    while True:
        try:
            await _poll_once(provider)
        except httpx.RequestError as exc:
            # ESPN API unavailable — broadcast feed_status to all rooms
            logger.warning("ESPN API unreachable: %s", exc)
            await _broadcast_feed_status(available=False, reason=str(exc))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Unexpected error in polling loop")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _poll_once(provider) -> None:
    states = await provider.get_all_live_states()

    async with AsyncSessionLocal() as db:
        async with db.begin():
            for state in states:
                await _process_match_state(db, state)


async def _process_match_state(db, state: LiveMatchState) -> None:
    # 1. Look up match by external_id
    match_stmt = select(Match).where(Match.external_id == state.external_match_id)
    result = await db.execute(match_stmt)
    match = result.scalar_one_or_none()

    if match is None:
        return  # unknown match, skip

    previous_status = match.status

    # 2. Update match score and status
    await db.execute(
        update(Match)
        .where(Match.id == match.id)
        .values(
            home_score=state.home_score,
            away_score=state.away_score,
            status=state.status,
        )
    )

    # 3. Trigger accuracy recording when match finishes
    if state.status == "finished" and previous_status != "finished":
        asyncio.create_task(
            _record_accuracy_background(match.id)
        )
        from app.services.broadcast import manager
        asyncio.create_task(manager.broadcast_all({"type": "accuracy_update"}))

    # 4. Process each event with deduplication
    for event in state.events:
        await _upsert_event(db, match.id, event)


async def _upsert_event(db, match_id: int, event) -> None:
    stmt = (
        pg_insert(LiveEvent)
        .values(
            match_id=match_id,
            external_event_id=event.external_event_id,
            event_type=event.event_type,
            player_name=event.player_name,
            minute=event.minute,
            extra_minute=event.extra_minute,
            home_score_after=event.home_score_after,
            away_score_after=event.away_score_after,
            raw_payload=event.raw_payload,
        )
        .on_conflict_do_nothing(index_elements=["external_event_id"])
        .returning(LiveEvent.id)
    )
    result = await db.execute(stmt)
    inserted_id = result.scalar_one_or_none()

    if inserted_id is not None:
        # Event was newly inserted — trigger ingame prediction
        # Import here to avoid circular imports at module level
        from app.services.broadcast import manager
        from app.services.prediction_engine import prediction_engine

        # Broadcast the raw event immediately
        await manager.broadcast_to_match(str(match_id), {
            "type": "live_event",
            "payload": {
                "id": inserted_id,
                "match_id": match_id,
                "event_type": event.event_type,
                "player_name": event.player_name,
                "minute": event.minute,
                "home_score_after": event.home_score_after,
                "away_score_after": event.away_score_after,
            }
        })

        # Trigger ingame prediction in a separate task (don't block the poll loop)
        asyncio.create_task(
            _run_ingame_prediction(match_id, inserted_id)
        )


async def _run_ingame_prediction(match_id: int, triggering_event_id: int) -> None:
    """Run ingame prediction in a separate DB session and broadcast result."""
    from app.services.broadcast import manager
    from app.services.prediction_engine import prediction_engine

    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                result = await prediction_engine.predict_ingame(
                    match_id=match_id,
                    triggering_event_id=triggering_event_id,
                    db=db,
                )

        if result is not None:
            await manager.broadcast_to_match(str(match_id), {
                "type": "prediction_update",
                "payload": {
                    "match_id": match_id,
                    "home_win_prob": result.home_win_prob,
                    "draw_prob": result.draw_prob,
                    "away_win_prob": result.away_win_prob,
                    "expected_home_goals": result.expected_home_goals,
                    "expected_away_goals": result.expected_away_goals,
                    "confidence_low": result.confidence_low,
                    "confidence_high": result.confidence_high,
                    "top_factors": result.top_factors,
                }
            })
    except Exception:
        logger.exception("Ingame prediction failed for match_id=%d", match_id)


async def _record_accuracy_background(match_id: int) -> None:
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                from app.services.accuracy_recorder import record_match_accuracy
                await record_match_accuracy(match_id, db)
    except Exception:
        logger.exception("Failed to record accuracy for match_id=%d", match_id)


async def _broadcast_feed_status(available: bool, reason: str = "") -> None:
    from app.services.broadcast import manager
    # Broadcast to all active rooms
    for match_id in list(manager.rooms.keys()):
        await manager.broadcast_to_match(match_id, {
            "type": "feed_status",
            "payload": {"available": available, "reason": reason}
        })
