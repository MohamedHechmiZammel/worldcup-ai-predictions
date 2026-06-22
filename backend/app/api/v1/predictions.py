from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.prediction import Prediction
from app.schemas.prediction import (
    FactorItem,
    PredictionHistoryResponse,
    PredictionResponse,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _prediction_to_schema(p: Prediction) -> PredictionResponse:
    top_factors = [FactorItem(**item) for item in (p.top_factors or [])]
    return PredictionResponse(
        id=p.id,
        match_id=p.match_id,
        prediction_type=p.prediction_type,
        home_win_prob=float(p.home_win_prob),
        draw_prob=float(p.draw_prob),
        away_win_prob=float(p.away_win_prob),
        expected_home_goals=float(p.expected_home_goals),
        expected_away_goals=float(p.expected_away_goals),
        confidence_low=float(p.confidence_low),
        confidence_high=float(p.confidence_high),
        top_factors=top_factors,
        created_at=p.created_at,
    )


@router.get("/{match_id}/latest", response_model=PredictionResponse)
async def get_latest_prediction(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> PredictionResponse:
    stmt = (
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(desc(Prediction.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    pred = result.scalar_one_or_none()
    if pred is None:
        raise HTTPException(status_code=404, detail="No prediction found for this match")
    return _prediction_to_schema(pred)


@router.get("/{match_id}/history", response_model=PredictionHistoryResponse)
async def get_prediction_history(
    match_id: int,
    db: AsyncSession = Depends(get_db),
) -> PredictionHistoryResponse:
    stmt = (
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(asc(Prediction.created_at))
    )
    result = await db.execute(stmt)
    predictions = [_prediction_to_schema(p) for p in result.scalars().all()]
    return PredictionHistoryResponse(match_id=match_id, predictions=predictions)
