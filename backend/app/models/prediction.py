from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    __table_args__ = (
        CheckConstraint(
            "ABS(home_win_prob + draw_prob + away_win_prob - 1.0) < 0.001",
            name="chk_probs_sum",
        ),
        CheckConstraint(
            "prediction_type IN ('prematch', 'live')",
            name="chk_prediction_type",
        ),
        Index("idx_predictions_match_created_at", "match_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id"), nullable=False
    )
    model_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_versions.id"), nullable=False
    )
    prediction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    home_win_prob: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    draw_prob: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    away_win_prob: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    expected_home_goals: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    expected_away_goals: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    confidence_low: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    confidence_high: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    top_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    triggering_event_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("live_events.id"), nullable=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=True
    )

    # Relationships
    match: Mapped["Match"] = relationship("Match", foreign_keys=[match_id])
    model_version: Mapped["ModelVersion"] = relationship(
        "ModelVersion", foreign_keys=[model_version_id]
    )
    triggering_event: Mapped[Optional["LiveEvent"]] = relationship(
        "LiveEvent", foreign_keys=[triggering_event_id]
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction(id={self.id!r}, match_id={self.match_id!r}, "
            f"prediction_type={self.prediction_type!r}, "
            f"home_win_prob={self.home_win_prob!r}, draw_prob={self.draw_prob!r}, "
            f"away_win_prob={self.away_win_prob!r}, "
            f"created_at={self.created_at!r})>"
        )
