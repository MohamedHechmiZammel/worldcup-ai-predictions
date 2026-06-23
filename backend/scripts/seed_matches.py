"""
Seed all World Cup 2026 group-stage fixtures (72 matches) into the database.

Run AFTER seed_teams.py so that team rows already exist.

Usage (from the backend/ directory):
    python -m scripts.seed_matches
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure the app package is importable when running as a script
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.models.match import Match
from app.models.team import Team

# ---------------------------------------------------------------------------
# Tournament configuration
# ---------------------------------------------------------------------------

# Official 2026 World Cup group draw (held 2025-12-05). Codes must match
# seed_teams.py. Order within each group = draw positions 1-4 (e.g. A1..A4).
GROUPS: dict[str, list[str]] = {
    "A": ["MEX", "RSA", "KOR", "CZE"],
    "B": ["CAN", "BIH", "QAT", "SUI"],
    "C": ["BRA", "MAR", "HAI", "SCO"],
    "D": ["USA", "PAR", "AUS", "TUR"],
    "E": ["GER", "CUW", "CIV", "ECU"],
    "F": ["NED", "JPN", "SWE", "TUN"],
    "G": ["BEL", "EGY", "IRN", "NZL"],
    "H": ["ESP", "CPV", "KSA", "URU"],
    "I": ["FRA", "SEN", "IRQ", "NOR"],
    "J": ["ARG", "ALG", "AUT", "JOR"],
    "K": ["POR", "COD", "UZB", "COL"],
    "L": ["ENG", "CRO", "GHA", "PAN"],
}

# Venue pool — rotated round-robin across all 72 matches
VENUES: list[tuple[str, str]] = [
    ("MetLife Stadium", "East Rutherford, NJ"),
    ("AT&T Stadium", "Arlington, TX"),
    ("SoFi Stadium", "Inglewood, CA"),
    ("Levi's Stadium", "Santa Clara, CA"),
    ("Rose Bowl", "Pasadena, CA"),
    ("Hard Rock Stadium", "Miami Gardens, FL"),
    ("Lincoln Financial Field", "Philadelphia, PA"),
    ("Arrowhead Stadium", "Kansas City, MO"),
    ("Gillette Stadium", "Foxborough, MA"),
    ("Lumen Field", "Seattle, WA"),
    ("BC Place", "Vancouver, BC"),
    ("BMO Field", "Toronto, ON"),
    ("Estadio Azteca", "Mexico City, MX"),
    ("Estadio BBVA", "Guadalupe, MX"),
]

# Tournament kick-off: June 11, 2026 15:00 UTC
_KICKOFF_BASE = datetime(2026, 6, 11, 15, 0, 0, tzinfo=timezone.utc)
# Gap between consecutive matches on the same logical "slot"
_MATCH_INTERVAL = timedelta(hours=3)


def _build_fixtures() -> list[dict]:
    """
    Return a list of fixture dicts ready for upsert.

    Each group plays a full round-robin (C(4,2) = 6 matches).
    Match-day pairings follow the standard FIFA ordering:
        MD1: (0v1, 2v3)
        MD2: (0v2, 1v3)
        MD3: (0v3, 1v2)
    """
    matchday_pairs = [
        (0, 1), (2, 3),  # Matchday 1
        (0, 2), (1, 3),  # Matchday 2
        (0, 3), (1, 2),  # Matchday 3
    ]

    # Each matchday spans 4 calendar days; groups are spread across them.
    # MD1: Jun 11-14  MD2: Jun 15-18  MD3: Jun 19-22
    matchday_start_offsets = {
        0: timedelta(days=0),   # MD1 pair 1
        1: timedelta(days=0),   # MD1 pair 2
        2: timedelta(days=4),   # MD2 pair 1
        3: timedelta(days=4),   # MD2 pair 2
        4: timedelta(days=8),   # MD3 pair 1
        5: timedelta(days=8),   # MD3 pair 2
    }

    fixtures: list[dict] = []
    venue_idx = 0

    for group_idx, (group_letter, codes) in enumerate(GROUPS.items()):
        for pair_idx, (hi, ai) in enumerate(matchday_pairs):
            home_code = codes[hi]
            away_code = codes[ai]
            external_id = f"wc2026_{home_code}_{away_code}"

            # Stagger each group by (group_idx * 3h) within its matchday window
            day_offset = matchday_start_offsets[pair_idx]
            group_offset = timedelta(hours=group_idx)  # one group per hour slot
            scheduled_at = _KICKOFF_BASE + day_offset + group_offset

            venue, city = VENUES[venue_idx % len(VENUES)]
            venue_idx += 1

            fixtures.append(
                {
                    "external_id": external_id,
                    "home_code": home_code,
                    "away_code": away_code,
                    "scheduled_at": scheduled_at,
                    "venue": venue,
                    "city": city,
                    "stage": f"Group {group_letter}",
                    "status": "scheduled",
                }
            )

    return fixtures


async def main() -> None:
    fixtures = _build_fixtures()
    print(f"Built {len(fixtures)} group-stage fixtures.")

    async with AsyncSessionLocal() as session:
        # ------------------------------------------------------------------
        # 1. Load all teams indexed by country_code
        # ------------------------------------------------------------------
        result = await session.execute(select(Team))
        teams_by_code: dict[str, int] = {
            t.country_code: t.id for t in result.scalars().all()
        }

        missing = (
            {f["home_code"] for f in fixtures} | {f["away_code"] for f in fixtures}
        ) - set(teams_by_code.keys())

        if missing:
            print(
                f"ERROR: The following country codes are not in the teams table: {sorted(missing)}\n"
                "       Run seed_teams.py first.",
                file=sys.stderr,
            )
            sys.exit(1)

        # ------------------------------------------------------------------
        # 2. Upsert each fixture
        # ------------------------------------------------------------------
        upserted = 0
        for fix in fixtures:
            home_id = teams_by_code[fix["home_code"]]
            away_id = teams_by_code[fix["away_code"]]

            stmt = (
                pg_insert(Match)
                .values(
                    external_id=fix["external_id"],
                    home_team_id=home_id,
                    away_team_id=away_id,
                    scheduled_at=fix["scheduled_at"],
                    venue=fix["venue"],
                    city=fix["city"],
                    stage=fix["stage"],
                    status=fix["status"],
                )
                .on_conflict_do_update(
                    index_elements=["external_id"],
                    set_={
                        "home_team_id": home_id,
                        "away_team_id": away_id,
                        "scheduled_at": fix["scheduled_at"],
                        "venue": fix["venue"],
                        "city": fix["city"],
                        "stage": fix["stage"],
                        # status is intentionally NOT overwritten so live/finished
                        # matches keep their state on re-seed
                    },
                )
            )
            await session.execute(stmt)
            upserted += 1

        await session.commit()

    print(f"Done — upserted {upserted} group-stage fixtures.")


if __name__ == "__main__":
    asyncio.run(main())
