from __future__ import annotations

import logging
from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accuracy_record import AccuracyRecord
from app.models.match import Match
from app.models.prediction import Prediction

logger = logging.getLogger(__name__)


def _determine_outcome(home_score: int, away_score: int) -> str:
    """Convert final score to outcome string."""
    if home_score > away_score:
        return "home_win"
    elif home_score == away_score:
        return "draw"
    else:
        return "away_win"


async def record_match_accuracy(match_id: int, db: AsyncSession) -> AccuracyRecord | None:
    """Record the accuracy of the pre-match prediction for a finished match.

    Uses the most recent prematch prediction (not live) to compare against actual result.
    Idempotent via ON CONFLICT DO NOTHING (UNIQUE on match_id).
    """
    # Load finished match
    match_stmt = select(Match).where(Match.id == match_id)
    match = (await db.execute(match_stmt)).scalar_one_or_none()

    if match is None or match.status != "finished":
        return None
    if match.home_score is None or match.away_score is None:
        logger.warning("Match %d has no final score", match_id)
        return None

    # Get most recent prematch prediction
    pred_stmt = (
        select(Prediction)
        .where(Prediction.match_id == match_id, Prediction.prediction_type == "prematch")
        .order_by(desc(Prediction.created_at))
        .limit(1)
    )
    pred = (await db.execute(pred_stmt)).scalar_one_or_none()

    if pred is None:
        logger.info("No prematch prediction found for match %d", match_id)
        return None

    actual_outcome = _determine_outcome(match.home_score, match.away_score)
    probs = {
        "home_win": float(pred.home_win_prob),
        "draw": float(pred.draw_prob),
        "away_win": float(pred.away_win_prob),
    }
    predicted_outcome = max(probs, key=probs.__getitem__)
    was_correct = predicted_outcome == actual_outcome

    # Idempotent upsert
    stmt = (
        pg_insert(AccuracyRecord)
        .values(
            match_id=match_id,
            prediction_id=pred.id,
            predicted_outcome=predicted_outcome,
            actual_outcome=actual_outcome,
            predicted_confidence=float(max(probs.values())),
            was_correct=was_correct,
            stage=match.stage,
        )
        .on_conflict_do_nothing(index_elements=["match_id"])
        .returning(AccuracyRecord.id)
    )
    result = await db.execute(stmt)
    inserted_id = result.scalar_one_or_none()

    if inserted_id:
        logger.info(
            "Recorded accuracy for match %d: predicted=%s actual=%s correct=%s",
            match_id, predicted_outcome, actual_outcome, was_correct,
        )

    return await db.get(AccuracyRecord, inserted_id) if inserted_id else None
