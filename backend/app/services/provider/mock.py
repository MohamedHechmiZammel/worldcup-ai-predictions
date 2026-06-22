from __future__ import annotations

import random

from app.services.provider.base import FootballDataProvider, LiveMatchState, MatchEvent


class MockProvider(FootballDataProvider):
    # Class-level state so it persists across calls
    _match_states: dict[str, dict] = {}
    _event_sequences: dict[str, list[dict]] = {}

    MOCK_MATCHES = [
        {
            "external_match_id": "mock_001",
            "home_team_code": "FRA",
            "away_team_code": "ARG",
            "home_score": 0,
            "away_score": 0,
        },
        {
            "external_match_id": "mock_002",
            "home_team_code": "ESP",
            "away_team_code": "BRA",
            "home_score": 0,
            "away_score": 0,
        },
    ]

    # Pre-scripted event sequence for mock_001 (realistic WC final simulation)
    SCRIPTED_EVENTS: dict[str, list[dict]] = {
        "mock_001": [
            {"minute": 12, "type": "goal", "team": "FRA", "player": "Mbappé", "h": 1, "a": 0},
            {"minute": 34, "type": "yellow_card", "team": "ARG", "player": "De Paul", "h": 1, "a": 0},
            {"minute": 45, "type": "halftime", "team": None, "player": None, "h": 1, "a": 0},
            {"minute": 67, "type": "goal", "team": "ARG", "player": "Messi", "h": 1, "a": 1},
            {"minute": 78, "type": "red_card", "team": "FRA", "player": "Camavinga", "h": 1, "a": 1},
            {"minute": 90, "type": "fulltime", "team": None, "player": None, "h": 1, "a": 1},
        ]
    }

    def __init__(self) -> None:
        # Initialize match states at minute=0
        for match in self.MOCK_MATCHES:
            mid = match["external_match_id"]
            if mid not in self._match_states:
                self._match_states[mid] = {**match, "minute": 0, "status": "live"}

    async def get_all_live_states(self) -> list[LiveMatchState]:
        states = []
        for match in self.MOCK_MATCHES:
            mid = match["external_match_id"]
            state = self._match_states[mid]

            # Advance minute by 1-3 each poll
            if state["status"] == "live" and state["minute"] < 90:
                state["minute"] = min(90, state["minute"] + random.randint(1, 3))

            # Find events that should have fired by now
            events: list[MatchEvent] = []
            for scripted in self.SCRIPTED_EVENTS.get(mid, []):
                if scripted["minute"] <= state["minute"]:
                    events.append(self.normalize_event(scripted, scripted["h"], scripted["a"]))
                    if scripted["type"] == "fulltime":
                        state["status"] = "finished"
                    elif scripted["type"] == "halftime":
                        state["status"] = "halftime"

            # Update scores from last goal event
            for ev in events:
                state["home_score"] = ev.home_score_after
                state["away_score"] = ev.away_score_after

            states.append(LiveMatchState(
                external_match_id=mid,
                home_team_code=state["home_team_code"],
                away_team_code=state["away_team_code"],
                home_score=state["home_score"],
                away_score=state["away_score"],
                status=state["status"],
                minute=state["minute"],
                events=events,
            ))
        return states

    def normalize_event(self, raw: dict, home_score: int, away_score: int) -> MatchEvent:
        key = (
            f"mock_{raw['minute']}_{raw['type']}_{raw.get('player', 'none')}"
            .replace(" ", "_")
        )
        return MatchEvent(
            external_event_id=key,
            event_type=raw["type"],
            team_code=raw.get("team"),
            player_name=raw.get("player"),
            minute=raw["minute"],
            extra_minute=None,
            home_score_after=home_score,
            away_score_after=away_score,
            raw_payload=raw,
        )
