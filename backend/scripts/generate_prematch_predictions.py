import asyncio
import sys
from pathlib import Path

# Allow running from backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.match import Match
from app.services.prediction_engine import prediction_engine


async def main() -> None:
    print("Loading prediction engine...")
    async with AsyncSessionLocal() as db:
        await prediction_engine.load(db)

    if prediction_engine._artifact is None:
        print("ERROR: No active prematch model found. Run ml/train_prematch.py and ml/register_model.py first.")
        sys.exit(1)

    print("Fetching scheduled matches...")
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Match)
            .options(selectinload(Match.home_team), selectinload(Match.away_team))
            .where(Match.status == "scheduled")
            .order_by(Match.scheduled_at)
        )
        result = await db.execute(stmt)
        matches = result.scalars().all()

    print(f"Found {len(matches)} scheduled matches")

    success = 0
    errors = 0

    for i, match in enumerate(matches, 1):
        home = match.home_team.name if match.home_team else f"Team#{match.home_team_id}"
        away = match.away_team.name if match.away_team else f"Team#{match.away_team_id}"

        try:
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    result = await prediction_engine.predict_and_save(match.id, db)

            if result:
                print(f"[{i}/{len(matches)}] {home} vs {away} → home={result.home_win_prob:.1%} draw={result.draw_prob:.1%} away={result.away_win_prob:.1%}")
                success += 1
            else:
                print(f"[{i}/{len(matches)}] {home} vs {away} → SKIPPED (no result)")
        except Exception as e:
            print(f"[{i}/{len(matches)}] {home} vs {away} → ERROR: {e}")
            errors += 1

    print(f"\nDone: {success} predictions generated, {errors} errors")


if __name__ == "__main__":
    asyncio.run(main())
