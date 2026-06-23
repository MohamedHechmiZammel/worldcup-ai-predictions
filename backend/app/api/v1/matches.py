from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.accuracy_record import AccuracyRecord
from app.models.match import Match
from app.models.prediction import Prediction
from app.schemas.match import AccuracyInfo, MatchListResponse, MatchResponse
from app.schemas.prediction import FactorItem, PredictionResponse

STAGE_PRIORITY = {
    **{f"Group {letter}": i for i, letter in enumerate("ABCDEFGHIJKL")},
    "Round of 32": 12,
    "Round of 16": 13,
    "Quarter-finals": 14,
    "Semi-finals": 15,
    "Third place": 16,
    "Final": 17,
}


def _stage_sort_key(stage: str) -> int:
    return STAGE_PRIORITY.get(stage, 99)

router = APIRouter(prefix="/matches", tags=["matches"])


def _build_prediction_response(pred: Prediction) -> PredictionResponse:
    """Map a Prediction ORM object to PredictionResponse, converting Decimals to float."""
    raw_factors = pred.top_factors or []
    top_factors = [
        FactorItem(
            feature=f.get("feature", ""),
            impact_pct=float(f.get("impact_pct", 0.0)),
            label=f.get("label", ""),
        )
        for f in raw_factors
    ]
    return PredictionResponse(
        id=pred.id,
        match_id=pred.match_id,
        prediction_type=pred.prediction_type,
        home_win_prob=float(pred.home_win_prob),
        draw_prob=float(pred.draw_prob),
        away_win_prob=float(pred.away_win_prob),
        expected_home_goals=float(pred.expected_home_goals),
        expected_away_goals=float(pred.expected_away_goals),
        confidence_low=float(pred.confidence_low),
        confidence_high=float(pred.confidence_high),
        top_factors=top_factors,
        created_at=pred.created_at,
    )


def _build_match_response(
    match: Match,
    prediction: Prediction | None,
    accuracy_record: AccuracyRecord | None = None,
) -> MatchResponse:
    """Map a Match ORM object (with loaded relationships) to MatchResponse."""
    pred_response = _build_prediction_response(prediction) if prediction is not None else None
    accuracy_info: AccuracyInfo | None = None
    if accuracy_record is not None:
        accuracy_info = AccuracyInfo(
            was_correct=accuracy_record.was_correct,
            predicted_outcome=accuracy_record.predicted_outcome,
            actual_outcome=accuracy_record.actual_outcome,
        )
    return MatchResponse(
        id=match.id,
        external_id=match.external_id,
        home_team_id=match.home_team_id,
        away_team_id=match.away_team_id,
        scheduled_at=match.scheduled_at,
        venue=match.venue,
        city=match.city,
        stage=match.stage,
        status=match.status,
        home_score=match.home_score,
        away_score=match.away_score,
        home_team=match.home_team,
        away_team=match.away_team,
        prediction=pred_response,
        accuracy=accuracy_info,
    )


@router.get("/", response_model=MatchListResponse)
async def get_matches(
    status: str | None = None,
    stage: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> MatchListResponse:
    stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
        )
        .order_by(Match.scheduled_at)
    )
    if status and status != "all":
        stmt = stmt.where(Match.status == status)
    if stage:
        stmt = stmt.where(Match.stage == stage)

    result = await db.execute(stmt)
    matches = result.scalars().all()

    # Count live matches in the full result set (before status filter would reduce it)
    live_count_stmt = select(func.count()).select_from(Match).where(Match.status == "live")
    live_count_result = await db.execute(live_count_stmt)
    live_count = live_count_result.scalar_one()

    # For each match, fetch the latest prediction and accuracy record (for finished matches)
    match_responses: list[MatchResponse] = []
    for m in matches:
        pred_stmt = (
            select(Prediction)
            .where(Prediction.match_id == m.id)
            .order_by(desc(Prediction.created_at))
            .limit(1)
        )
        pred_result = await db.execute(pred_stmt)
        latest_pred = pred_result.scalar_one_or_none()

        accuracy_record: AccuracyRecord | None = None
        if m.status == "finished":
            acc_stmt = select(AccuracyRecord).where(AccuracyRecord.match_id == m.id)
            acc_result = await db.execute(acc_stmt)
            accuracy_record = acc_result.scalar_one_or_none()

        match_responses.append(_build_match_response(m, latest_pred, accuracy_record))

    match_responses.sort(key=lambda mr: (_stage_sort_key(mr.stage), str(mr.scheduled_at)))

    return MatchListResponse(
        matches=match_responses,
        total=len(match_responses),
        live_count=live_count,
    )


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
        )
        .where(Match.id == match_id)
    )
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()

    if match is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    pred_stmt = (
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(desc(Prediction.created_at))
        .limit(1)
    )
    pred_result = await db.execute(pred_stmt)
    latest_pred = pred_result.scalar_one_or_none()

    accuracy_record: AccuracyRecord | None = None
    if match.status == "finished":
        acc_stmt = select(AccuracyRecord).where(AccuracyRecord.match_id == match_id)
        acc_result = await db.execute(acc_stmt)
        accuracy_record = acc_result.scalar_one_or_none()

    return _build_match_response(match, latest_pred, accuracy_record)
