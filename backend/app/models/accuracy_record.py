from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AccuracyRecord(Base):
    __tablename__ = "accuracy_records"

    __table_args__ = (
        CheckConstraint(
            "predicted_outcome IN ('home_win', 'draw', 'away_win') "
            "AND actual_outcome IN ('home_win', 'draw', 'away_win')",
            name="chk_outcome",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, unique=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), nullable=False)
    predicted_outcome: Mapped[str] = mapped_column(String(10), nullable=False)
    actual_outcome: Mapped[str] = mapped_column(String(10), nullable=False)
    predicted_confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<AccuracyRecord id={self.id!r} match_id={self.match_id!r} "
            f"predicted={self.predicted_outcome!r} actual={self.actual_outcome!r} "
            f"was_correct={self.was_correct!r}>"
        )
