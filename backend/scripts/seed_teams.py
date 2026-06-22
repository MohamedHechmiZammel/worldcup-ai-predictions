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

TEAMS: list[dict] = [
    # Group A
    {"name": "Mexico",       "country_code": "MEX", "fifa_ranking": 13, "group_letter": "A"},
    {"name": "Jamaica",      "country_code": "JAM", "fifa_ranking": 45, "group_letter": "A"},
    {"name": "Venezuela",    "country_code": "VEN", "fifa_ranking": 27, "group_letter": "A"},
    {"name": "Ecuador",      "country_code": "ECU", "fifa_ranking": 19, "group_letter": "A"},
    # Group B
    {"name": "Argentina",   "country_code": "ARG", "fifa_ranking":  1, "group_letter": "B"},
    {"name": "Chile",        "country_code": "CHI", "fifa_ranking": 26, "group_letter": "B"},
    {"name": "Peru",         "country_code": "PER", "fifa_ranking": 22, "group_letter": "B"},
    {"name": "Canada",       "country_code": "CAN", "fifa_ranking": 38, "group_letter": "B"},
    # Group C
    {"name": "Brazil",       "country_code": "BRA", "fifa_ranking":  5, "group_letter": "C"},
    {"name": "Paraguay",     "country_code": "PAR", "fifa_ranking": 37, "group_letter": "C"},
    {"name": "Colombia",     "country_code": "COL", "fifa_ranking":  9, "group_letter": "C"},
    {"name": "Bolivia",      "country_code": "BOL", "fifa_ranking": 39, "group_letter": "C"},
    # Group D
    {"name": "Uruguay",      "country_code": "URU", "fifa_ranking": 11, "group_letter": "D"},
    {"name": "USA",          "country_code": "USA", "fifa_ranking": 12, "group_letter": "D"},
    {"name": "Panama",       "country_code": "PAN", "fifa_ranking": 31, "group_letter": "D"},
    {"name": "Cuba",         "country_code": "CUB", "fifa_ranking": 48, "group_letter": "D"},
    # Group E
    {"name": "Spain",        "country_code": "ESP", "fifa_ranking":  3, "group_letter": "E"},
    {"name": "Netherlands",  "country_code": "NED", "fifa_ranking":  7, "group_letter": "E"},
    {"name": "Serbia",       "country_code": "SRB", "fifa_ranking": 23, "group_letter": "E"},
    {"name": "Morocco",      "country_code": "MAR", "fifa_ranking": 15, "group_letter": "E"},
    # Group F
    {"name": "Germany",      "country_code": "GER", "fifa_ranking":  8, "group_letter": "F"},
    {"name": "Belgium",      "country_code": "BEL", "fifa_ranking": 20, "group_letter": "F"},
    {"name": "Ukraine",      "country_code": "UKR", "fifa_ranking": 25, "group_letter": "F"},
    {"name": "Saudi Arabia", "country_code": "KSA", "fifa_ranking": 44, "group_letter": "F"},
    # Group G
    {"name": "France",       "country_code": "FRA", "fifa_ranking":  2, "group_letter": "G"},
    {"name": "Portugal",     "country_code": "POR", "fifa_ranking":  6, "group_letter": "G"},
    {"name": "Croatia",      "country_code": "CRO", "fifa_ranking": 16, "group_letter": "G"},
    {"name": "Australia",    "country_code": "AUS", "fifa_ranking": 24, "group_letter": "G"},
    # Group H
    {"name": "England",      "country_code": "ENG", "fifa_ranking":  4, "group_letter": "H"},
    {"name": "Italy",        "country_code": "ITA", "fifa_ranking": 10, "group_letter": "H"},
    {"name": "Romania",      "country_code": "ROU", "fifa_ranking": 46, "group_letter": "H"},
    {"name": "Algeria",      "country_code": "ALG", "fifa_ranking": 33, "group_letter": "H"},
    # Group I
    {"name": "Japan",        "country_code": "JPN", "fifa_ranking": 14, "group_letter": "I"},
    {"name": "South Korea",  "country_code": "KOR", "fifa_ranking": 18, "group_letter": "I"},
    {"name": "Iran",         "country_code": "IRN", "fifa_ranking": 21, "group_letter": "I"},
    {"name": "New Zealand",  "country_code": "NZL", "fifa_ranking": 43, "group_letter": "I"},
    # Group J
    {"name": "Qatar",        "country_code": "QAT", "fifa_ranking": 47, "group_letter": "J"},
    {"name": "Iraq",         "country_code": "IRQ", "fifa_ranking": 42, "group_letter": "J"},
    {"name": "Jordan",       "country_code": "JOR", "fifa_ranking": 41, "group_letter": "J"},
    {"name": "Uzbekistan",   "country_code": "UZB", "fifa_ranking": 40, "group_letter": "J"},
    # Group K
    {"name": "Senegal",      "country_code": "SEN", "fifa_ranking": 17, "group_letter": "K"},
    {"name": "Egypt",        "country_code": "EGY", "fifa_ranking": 30, "group_letter": "K"},
    {"name": "Tunisia",      "country_code": "TUN", "fifa_ranking": 32, "group_letter": "K"},
    {"name": "South Africa", "country_code": "RSA", "fifa_ranking": 35, "group_letter": "K"},
    # Group L
    {"name": "Nigeria",      "country_code": "NGA", "fifa_ranking": 28, "group_letter": "L"},
    {"name": "Cameroon",     "country_code": "CMR", "fifa_ranking": 29, "group_letter": "L"},
    {"name": "DR Congo",     "country_code": "COD", "fifa_ranking": 36, "group_letter": "L"},
    {"name": "Ivory Coast",  "country_code": "CIV", "fifa_ranking": 34, "group_letter": "L"},
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
