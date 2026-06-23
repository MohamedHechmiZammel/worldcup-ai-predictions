"""
Idempotent seed script for the 48 FIFA World Cup 2026 teams.

Run from the backend/ directory:
    python -m scripts.seed_teams

or directly:
    python backend/scripts/seed_teams.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running the script directly from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects.postgresql import insert

from app.core.database import engine
from app.models.team import Team  # noqa: F401 – ensure mapper is registered

# ---------------------------------------------------------------------------
# Team data: 48 teams across 12 groups (4 per group)
# ---------------------------------------------------------------------------

# IMPORTANT: ``name`` MUST match the spelling used in ml/data/raw/results.csv,
# because the prediction engine looks up Elo/form features by team name. Mis-
# spelled names (e.g. "USA" vs "United States") silently fall back to default
# Elo (1500) and corrupt predictions. Verified spellings: United States, Czech
# Republic, Cape Verde, Turkey, Curaçao.
#
# Teams and group placements reflect the OFFICIAL final draw held 2025-12-05.
# fifa_ranking is display-only metadata (the model uses Elo, not FIFA ranking);
# values are approximate June-2026 rankings.

TEAMS: list[dict] = [
    # Group A
    {"name": "Mexico",                 "country_code": "MEX", "fifa_ranking": 13, "group_letter": "A"},
    {"name": "South Africa",           "country_code": "RSA", "fifa_ranking": 60, "group_letter": "A"},
    {"name": "South Korea",            "country_code": "KOR", "fifa_ranking": 23, "group_letter": "A"},
    {"name": "Czech Republic",         "country_code": "CZE", "fifa_ranking": 40, "group_letter": "A"},
    # Group B
    {"name": "Canada",                 "country_code": "CAN", "fifa_ranking": 30, "group_letter": "B"},
    {"name": "Bosnia and Herzegovina", "country_code": "BIH", "fifa_ranking": 45, "group_letter": "B"},
    {"name": "Qatar",                  "country_code": "QAT", "fifa_ranking": 36, "group_letter": "B"},
    {"name": "Switzerland",            "country_code": "SUI", "fifa_ranking": 19, "group_letter": "B"},
    # Group C
    {"name": "Brazil",                 "country_code": "BRA", "fifa_ranking":  5, "group_letter": "C"},
    {"name": "Morocco",                "country_code": "MAR", "fifa_ranking": 12, "group_letter": "C"},
    {"name": "Haiti",                  "country_code": "HAI", "fifa_ranking": 83, "group_letter": "C"},
    {"name": "Scotland",               "country_code": "SCO", "fifa_ranking": 39, "group_letter": "C"},
    # Group D
    {"name": "United States",          "country_code": "USA", "fifa_ranking": 16, "group_letter": "D"},
    {"name": "Paraguay",               "country_code": "PAR", "fifa_ranking": 46, "group_letter": "D"},
    {"name": "Australia",              "country_code": "AUS", "fifa_ranking": 24, "group_letter": "D"},
    {"name": "Turkey",                 "country_code": "TUR", "fifa_ranking": 26, "group_letter": "D"},
    # Group E
    {"name": "Germany",                "country_code": "GER", "fifa_ranking":  9, "group_letter": "E"},
    {"name": "Curaçao",                "country_code": "CUW", "fifa_ranking": 90, "group_letter": "E"},
    {"name": "Ivory Coast",            "country_code": "CIV", "fifa_ranking": 40, "group_letter": "E"},
    {"name": "Ecuador",                "country_code": "ECU", "fifa_ranking": 24, "group_letter": "E"},
    # Group F
    {"name": "Netherlands",            "country_code": "NED", "fifa_ranking":  6, "group_letter": "F"},
    {"name": "Japan",                  "country_code": "JPN", "fifa_ranking": 17, "group_letter": "F"},
    {"name": "Sweden",                 "country_code": "SWE", "fifa_ranking": 25, "group_letter": "F"},
    {"name": "Tunisia",                "country_code": "TUN", "fifa_ranking": 41, "group_letter": "F"},
    # Group G
    {"name": "Belgium",                "country_code": "BEL", "fifa_ranking":  8, "group_letter": "G"},
    {"name": "Egypt",                  "country_code": "EGY", "fifa_ranking": 32, "group_letter": "G"},
    {"name": "Iran",                   "country_code": "IRN", "fifa_ranking": 20, "group_letter": "G"},
    {"name": "New Zealand",            "country_code": "NZL", "fifa_ranking": 89, "group_letter": "G"},
    # Group H
    {"name": "Spain",                  "country_code": "ESP", "fifa_ranking":  2, "group_letter": "H"},
    {"name": "Cape Verde",             "country_code": "CPV", "fifa_ranking": 70, "group_letter": "H"},
    {"name": "Saudi Arabia",           "country_code": "KSA", "fifa_ranking": 58, "group_letter": "H"},
    {"name": "Uruguay",                "country_code": "URU", "fifa_ranking": 15, "group_letter": "H"},
    # Group I
    {"name": "France",                 "country_code": "FRA", "fifa_ranking":  3, "group_letter": "I"},
    {"name": "Senegal",                "country_code": "SEN", "fifa_ranking": 18, "group_letter": "I"},
    {"name": "Iraq",                   "country_code": "IRQ", "fifa_ranking": 58, "group_letter": "I"},
    {"name": "Norway",                 "country_code": "NOR", "fifa_ranking": 28, "group_letter": "I"},
    # Group J
    {"name": "Argentina",              "country_code": "ARG", "fifa_ranking":  1, "group_letter": "J"},
    {"name": "Algeria",                "country_code": "ALG", "fifa_ranking": 38, "group_letter": "J"},
    {"name": "Austria",                "country_code": "AUT", "fifa_ranking": 22, "group_letter": "J"},
    {"name": "Jordan",                 "country_code": "JOR", "fifa_ranking": 62, "group_letter": "J"},
    # Group K
    {"name": "Portugal",               "country_code": "POR", "fifa_ranking":  7, "group_letter": "K"},
    {"name": "DR Congo",               "country_code": "COD", "fifa_ranking": 55, "group_letter": "K"},
    {"name": "Uzbekistan",             "country_code": "UZB", "fifa_ranking": 50, "group_letter": "K"},
    {"name": "Colombia",               "country_code": "COL", "fifa_ranking": 13, "group_letter": "K"},
    # Group L
    {"name": "England",                "country_code": "ENG", "fifa_ranking":  4, "group_letter": "L"},
    {"name": "Croatia",                "country_code": "CRO", "fifa_ranking": 10, "group_letter": "L"},
    {"name": "Ghana",                  "country_code": "GHA", "fifa_ranking": 73, "group_letter": "L"},
    {"name": "Panama",                 "country_code": "PAN", "fifa_ranking": 31, "group_letter": "L"},
]


async def main() -> None:
    async with engine.begin() as conn:
        stmt = (
            insert(Team)
            .values(TEAMS)
            .on_conflict_do_update(
                index_elements=["name"],
                set_={
                    "country_code": insert(Team).excluded.country_code,
                    "fifa_ranking":  insert(Team).excluded.fifa_ranking,
                    "group_letter":  insert(Team).excluded.group_letter,
                },
            )
        )
        result = await conn.execute(stmt)

    print(f"Upserted {result.rowcount} team(s) successfully.")


if __name__ == "__main__":
    asyncio.run(main())
