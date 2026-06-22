from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.prediction import AccuracyResponse
from app.services.accuracy_service import get_accuracy_summary

router = APIRouter(prefix="/accuracy", tags=["accuracy"])


@router.get("/", response_model=AccuracyResponse)
async def get_accuracy(db: AsyncSession = Depends(get_db)) -> AccuracyResponse:
    summary = await get_accuracy_summary(db)
    return AccuracyResponse(**summary)
