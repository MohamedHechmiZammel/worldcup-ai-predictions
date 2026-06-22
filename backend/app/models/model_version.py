from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    __table_args__ = (
        CheckConstraint(
            "model_type IN ('prematch', 'ingame')",
            name="chk_model_type",
        ),
        Index(
            "uq_model_versions_active_type",
            "model_type",
            unique=True,
            postgresql_where="is_active = TRUE",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    model_type: Mapped[str] = mapped_column(String(20), nullable=False)
    training_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_path: Mapped[str] = mapped_column(String(300), nullable=False)
    accuracy_on_val: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="FALSE")
    created_at: Mapped[datetime | None] = mapped_column(nullable=True, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<ModelVersion id={self.id!r} version={self.version!r} "
            f"model_type={self.model_type!r} is_active={self.is_active!r}>"
        )
