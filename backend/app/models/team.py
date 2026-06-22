from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.match import Match

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    fifa_ranking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_letter: Mapped[str | None] = mapped_column(String(1), nullable=True)
    avg_goals_scored: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    avg_goals_conceded: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    form_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    home_matches: Mapped[List["Match"]] = relationship(
        "Match", foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    away_matches: Mapped[List["Match"]] = relationship(
        "Match", foreign_keys="Match.away_team_id", back_populates="away_team"
    )

    def __repr__(self) -> str:
        return (
            f"<Team id={self.id!r} name={self.name!r} "
            f"country_code={self.country_code!r} group={self.group_letter!r}>"
        )
