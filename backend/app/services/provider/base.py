from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MatchEvent:
    external_event_id: str   # deduplication key (composite string)
    event_type: str           # goal | yellow_card | red_card | substitution | halftime | fulltime
    team_code: str | None     # country_code of the team
    player_name: str | None
    minute: int
    extra_minute: int | None
    home_score_after: int
    away_score_after: int
    raw_payload: dict         # full raw event for debugging


@dataclass
class LiveMatchState:
    external_match_id: str  # ESPN gameId or similar
    home_team_code: str
    away_team_code: str
    home_score: int
    away_score: int
    status: str              # scheduled | live | halftime | finished
    minute: int | None
    events: list[MatchEvent]


class FootballDataProvider(ABC):
    @abstractmethod
    async def get_all_live_states(self) -> list[LiveMatchState]:
        """Fetch all currently live/recently updated match states in a single call."""
        ...

    @abstractmethod
    def normalize_event(self, raw: dict, home_score: int, away_score: int) -> MatchEvent:
        """Convert a raw provider event dict to a normalized MatchEvent."""
        ...
