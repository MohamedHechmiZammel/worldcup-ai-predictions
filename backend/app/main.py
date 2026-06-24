from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import accuracy, admin, matches, predictions, standings, websocket
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.ingestion import run_polling_loop, run_historical_sync
from app.services.prediction_engine import prediction_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Load ML model at startup
    async with AsyncSessionLocal() as db:
        try:
            await prediction_engine.load(db)
        except Exception:
            logger.exception("Failed to load prediction engine at startup")

    # Start live data polling (today's matches every 15 s)
    polling_task = asyncio.create_task(run_polling_loop())
    # Backfill past results on startup, then repeat every 6 h
    sync_task = asyncio.create_task(run_historical_sync())

    yield

    polling_task.cancel()
    sync_task.cancel()
    for task in (polling_task, sync_task):
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="World Cup 2026 AI Predictions",
    description="Live match prediction dashboard with XGBoost + Poisson updates",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matches.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(accuracy.router, prefix="/api/v1")
app.include_router(standings.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(websocket.router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "model_loaded": prediction_engine._artifact is not None,
        "provider": settings.football_api_provider,
    }
