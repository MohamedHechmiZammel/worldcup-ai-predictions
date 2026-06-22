from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TeamBase(BaseModel):
    name: str
    country_code: str
    fifa_ranking: int | None = None
    group_letter: str | None = None


class TeamResponse(TeamBase):
    id: int
    avg_goals_scored: float | None = None
    avg_goals_conceded: float | None = None
    form_points: int | None = None

    model_config = ConfigDict(from_attributes=True)
