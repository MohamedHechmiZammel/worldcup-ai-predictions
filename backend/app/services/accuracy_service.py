from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accuracy_record import AccuracyRecord


async def get_accuracy_summary(db: AsyncSession) -> dict:
    """Compute accuracy statistics from all completed accuracy_records."""

    # Total and correct
    total_stmt = select(func.count(AccuracyRecord.id))
    correct_stmt = select(func.count(AccuracyRecord.id)).where(AccuracyRecord.was_correct == True)

    total = (await db.execute(total_stmt)).scalar_one() or 0
    correct = (await db.execute(correct_stmt)).scalar_one() or 0

    accuracy_pct = (correct / total * 100.0) if total > 0 else 0.0

    # By stage
    all_records_stmt = select(AccuracyRecord.stage, AccuracyRecord.was_correct)
    all_records = (await db.execute(all_records_stmt)).all()

    by_stage: dict[str, float] = {}
    stage_counts: dict[str, list[int]] = {}
    for record in all_records:
        stage = record.stage
        if stage not in stage_counts:
            stage_counts[stage] = [0, 0]  # [total, correct]
        stage_counts[stage][0] += 1
        if record.was_correct:
            stage_counts[stage][1] += 1

    for stage, (stage_total, stage_correct) in stage_counts.items():
        by_stage[stage] = round(stage_correct / stage_total * 100.0, 1) if stage_total > 0 else 0.0

    return {
        "total_predictions": total,
        "correct_predictions": correct,
        "accuracy_pct": round(accuracy_pct, 1),
        "by_stage": by_stage,
    }
