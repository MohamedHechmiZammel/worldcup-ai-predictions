from __future__ import annotations

import datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HeadToHead(Base):
    __tablename__ = "head_to_head"

    __table_args__ = (
        CheckConstraint("team_a_id < team_b_id", name="h2h_team_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_a_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )
    team_b_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )
    match_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    team_a_score: Mapped[int] = mapped_column(Integer, nullable=False)
    team_b_score: Mapped[int] = mapped_column(Integer, nullable=False)
    competition: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<HeadToHead id={self.id!r} "
            f"team_a_id={self.team_a_id!r} team_b_id={self.team_b_id!r} "
            f"date={self.match_date!r} score={self.team_a_score}-{self.team_b_score}>"
        )
