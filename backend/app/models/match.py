from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.core.database import Base


class Match(Base):
    __tablename__ = "matches"

    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled','live','halftime','finished','postponed','cancelled')",
            name="chk_status",
        ),
        Index("idx_matches_status", "status"),
        Index("idx_matches_scheduled_at", "scheduled_at"),
        Index("idx_matches_stage", "stage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    venue: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    # Relationships
    home_team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[home_team_id],
        back_populates="home_matches",
    )
    away_team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[away_team_id],
        back_populates="away_matches",
    )

    def __repr__(self) -> str:
        return (
            f"<Match(id={self.id!r}, home_team_id={self.home_team_id!r}, "
            f"away_team_id={self.away_team_id!r}, stage={self.stage!r}, "
            f"status={self.status!r}, scheduled_at={self.scheduled_at!r})>"
        )
