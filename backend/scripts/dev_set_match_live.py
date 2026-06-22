"""Dev helper: set a match status for local testing.

Usage:
  python -m scripts.dev_set_match_live --match-id 1 --status live
  python -m scripts.dev_set_match_live --match-id 1 --status finished --home-score 2 --away-score 1
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import update

from app.core.database import AsyncSessionLocal
from app.models.match import Match


async def set_match_status(
    match_id: int,
    status: str,
    home_score: int | None,
    away_score: int | None,
) -> None:
    async with AsyncSessionLocal() as db:
        values: dict = {"status": status}
        if home_score is not None:
            values["home_score"] = home_score
        if away_score is not None:
            values["away_score"] = away_score
        await db.execute(update(Match).where(Match.id == match_id).values(**values))
        await db.commit()
        print(f"Match {match_id} → status={status}" +
              (f", score={home_score}-{away_score}" if home_score is not None else ""))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", type=int, required=True)
    parser.add_argument("--status", choices=["scheduled", "live", "halftime", "finished"], required=True)
    parser.add_argument("--home-score", type=int, default=None)
    parser.add_argument("--away-score", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(set_match_status(args.match_id, args.status, args.home_score, args.away_score))


if __name__ == "__main__":
    main()
