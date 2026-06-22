from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class PredictionType(str, Enum):
    prematch = "prematch"
    live = "live"


class FactorItem(BaseModel):
    feature: str
    impact_pct: float
    label: str


class PredictionResponse(BaseModel):
    id: int
    match_id: int
    prediction_type: PredictionType
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: float
    expected_away_goals: float
    confidence_low: float
    confidence_high: float
    top_factors: list[FactorItem]
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PredictionHistoryResponse(BaseModel):
    match_id: int
    predictions: list[PredictionResponse]


class AccuracyResponse(BaseModel):
    total_predictions: int
    correct_predictions: int
    accuracy_pct: float
    by_stage: dict[str, float]
