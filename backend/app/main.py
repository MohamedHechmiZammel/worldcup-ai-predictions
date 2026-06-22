from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import accuracy, admin, matches, predictions, websocket
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.ingestion import run_polling_loop
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

    # Start live data polling
    polling_task = asyncio.create_task(run_polling_loop())

    yield

    # Shutdown: cancel polling
    polling_task.cancel()
    try:
        await polling_task
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


@app.get("/health/debug", tags=["health"])
async def health_debug() -> dict:
    from pathlib import Path
    from sqlalchemy import text
    info: dict = {}
    # DB connectivity
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        info["db"] = "ok"
    except Exception as exc:
        info["db"] = f"ERROR: {exc}"
    # model_versions row
    try:
        from sqlalchemy import select
        from app.models.model_version import ModelVersion
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ModelVersion).where(ModelVersion.model_type == "prematch", ModelVersion.is_active.is_(True))
            )
            mv = result.scalars().first()
        if mv:
            info["model_version"] = {"id": mv.id, "artifact_path": mv.artifact_path, "file_exists": Path(mv.artifact_path).exists()}
        else:
            info["model_version"] = "NOT FOUND"
    except Exception as exc:
        info["model_version"] = f"ERROR: {exc}"
    return info
