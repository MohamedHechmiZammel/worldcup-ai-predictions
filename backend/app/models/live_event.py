from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LiveEvent(Base):
    __tablename__ = "live_events"

    __table_args__ = (
        UniqueConstraint("external_event_id", name="uq_live_events_external_event_id"),
        CheckConstraint(
            "event_type IN ('goal','yellow_card','red_card','substitution','halftime','fulltime')",
            name="chk_event_type",
        ),
        Index("ix_live_events_match_id", "match_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id"), nullable=False
    )
    external_event_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    player_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    home_score_after: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score_after: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None, server_default="NOW()"
    )

    def __repr__(self) -> str:
        return (
            f"<LiveEvent id={self.id!r} match_id={self.match_id!r} "
            f"event_type={self.event_type!r} minute={self.minute!r}>"
        )
