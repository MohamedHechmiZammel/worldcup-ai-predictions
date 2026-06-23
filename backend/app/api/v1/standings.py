from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/standings", tags=["standings"])

ESPN_STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"

# Simple in-process cache: (data, fetched_at)
_cache: tuple[dict, float] | None = None
_CACHE_TTL = 60.0  # seconds
_fetch_lock = asyncio.Lock()


def _parse_entry(entry: dict) -> dict:
    stats = {s["abbreviation"]: s for s in entry.get("stats", [])}

    def val(abbr: str, default: int = 0) -> int:
        s = stats.get(abbr)
        if s is None:
            return default
        try:
            return int(float(s.get("value", default)))
        except (ValueError, TypeError):
            return default

    team = entry.get("team", {})
    note = entry.get("note", {})

    return {
        "team_abbr": team.get("abbreviation", ""),
        "team_name": team.get("displayName", team.get("location", "")),
        "played": val("GP"),
        "won": val("W"),
        "drawn": val("D"),
        "lost": val("L"),
        "goals_for": val("F"),
        "goals_against": val("A"),
        "goal_diff": val("GD"),
        "points": val("P"),
        "note": note.get("description", ""),
        "note_color": note.get("color", ""),
    }


async def _fetch_standings() -> dict[str, list[dict]]:
    """Fetch ESPN standings and return keyed by group letter (A-L)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(ESPN_STANDINGS_URL)
        resp.raise_for_status()
        data = resp.json()

    groups: dict[str, list[dict]] = {}
    for group in data.get("children", []):
        name: str = group.get("name", "")
        if not name.startswith("Group "):
            continue
        letter = name.replace("Group ", "").strip()
        entries = group.get("standings", {}).get("entries", [])
        groups[letter] = [_parse_entry(e) for e in entries]

    return groups


async def _get_cached() -> dict[str, list[dict]]:
    global _cache
    async with _fetch_lock:
        if _cache is not None and (time.monotonic() - _cache[1]) < _CACHE_TTL:
            return _cache[0]
        data = await _fetch_standings()
        _cache = (data, time.monotonic())
        return data


@router.get("/")
async def get_all_standings() -> dict[str, Any]:
    """Return live WC 2026 group standings from ESPN (60s cache)."""
    try:
        groups = await _get_cached()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"ESPN unreachable: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"ESPN error {exc.response.status_code}") from exc
    return {"groups": groups}


@router.get("/{group_letter}")
async def get_group_standings(group_letter: str) -> dict[str, Any]:
    """Return standings for a single group (e.g. /standings/A)."""
    letter = group_letter.upper()
    try:
        groups = await _get_cached()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"ESPN unreachable: {exc}") from exc
    if letter not in groups:
        raise HTTPException(status_code=404, detail=f"Group {letter} not found")
    return {"group": letter, "standings": groups[letter]}
