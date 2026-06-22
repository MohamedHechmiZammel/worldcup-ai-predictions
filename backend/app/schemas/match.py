from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.schemas.prediction import PredictionResponse
from app.schemas.team import TeamResponse


class AccuracyInfo(BaseModel):
    was_correct: bool
    predicted_outcome: str
    actual_outcome: str


class MatchStatus(str, Enum):
    scheduled = "scheduled"
    live = "live"
    halftime = "halftime"
    finished = "finished"
    postponed = "postponed"
    cancelled = "cancelled"


class MatchBase(BaseModel):
    scheduled_at: datetime
    venue: str | None = None
    city: str | None = None
    stage: str
    status: MatchStatus


class MatchResponse(MatchBase):
    id: int
    external_id: str | None = None
    home_team_id: int
    away_team_id: int
    home_score: int | None = None
    away_score: int | None = None
    home_team: TeamResponse | None = None
    away_team: TeamResponse | None = None
    prediction: PredictionResponse | None = None
    accuracy: AccuracyInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class MatchListResponse(BaseModel):
    matches: list[MatchResponse]
    total: int
    live_count: int = 0
