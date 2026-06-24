import httpx

from app.services.provider.base import FootballDataProvider, LiveMatchState, MatchEvent

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

# Map ESPN status state to our status values
STATUS_MAP = {
    "pre": "scheduled",
    "in": "live",
    "post": "finished",
}

# Map ESPN event type text to our event_type values
EVENT_TYPE_MAP = {
    "Goal": "goal",
    "Yellow Card": "yellow_card",
    "Red Card": "red_card",
    "Substitution": "substitution",
    "End Period": "halftime",  # period=1 → halftime, period=2 → fulltime
}


class ESPNAdapter(FootballDataProvider):

    async def get_all_live_states(self) -> list[LiveMatchState]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(ESPN_URL)
                resp.raise_for_status()
                data = resp.json()
            except httpx.RequestError:
                raise  # let ingestion.py handle retry/broadcast

        states = []
        for event in data.get("events", []):
            try:
                state = self._parse_event(event)
                if state:
                    states.append(state)
            except Exception:
                continue  # skip malformed events, don't crash the whole poll
        return states

    def _parse_event(self, event: dict) -> LiveMatchState | None:
        game_id = event.get("id", "")
        status_obj = event.get("status", {})
        status_type = STATUS_MAP.get(
            status_obj.get("type", {}).get("state", "pre"), "scheduled"
        )

        # Only process live or recently finished matches
        if status_type not in ("live", "finished"):
            return None

        competitions = event.get("competitions", [{}])
        if not competitions:
            return None
        comp = competitions[0]

        home_team_code = ""
        away_team_code = ""
        home_score = 0
        away_score = 0

        for competitor in comp.get("competitors", []):
            abbr = competitor.get("team", {}).get("abbreviation", "")
            score = int(competitor.get("score", "0") or 0)
            if competitor.get("homeAway") == "home":
                home_team_code = abbr
                home_score = score
            else:
                away_team_code = abbr
                away_score = score

        # Parse play-by-play details
        events = []
        for detail in comp.get("details", []):
            try:
                ev = self.normalize_event(
                    {**detail, "_game_id": game_id},
                    int(detail.get("homeScore", home_score)),
                    int(detail.get("awayScore", away_score)),
                )
                events.append(ev)
            except Exception:
                continue

        # Determine minute from displayClock
        clock_str = status_obj.get("displayClock", "0:00")
        try:
            minute = int(clock_str.split(":")[0])
        except (ValueError, IndexError):
            minute = None

        # Parse per-team live statistics (possession, shots, corners, fouls)
        home_stats: dict | None = None
        away_stats: dict | None = None
        for competitor in comp.get("competitors", []):
            raw = competitor.get("statistics", [])
            if not raw:
                continue
            parsed = {s["name"]: s.get("displayValue", s.get("value")) for s in raw if "name" in s}
            if competitor.get("homeAway") == "home":
                home_stats = parsed
            else:
                away_stats = parsed

        # Period and human-readable description ("First Half", "Halftime", "Final")
        period = status_obj.get("period")
        period_description = status_obj.get("type", {}).get("description", "")

        return LiveMatchState(
            external_match_id=f"espn_{game_id}",
            home_team_code=home_team_code,
            away_team_code=away_team_code,
            home_score=home_score,
            away_score=away_score,
            status=status_type,
            minute=minute,
            events=events,
            period=period,
            period_description=period_description,
            home_stats=home_stats,
            away_stats=away_stats,
        )

    def normalize_event(self, raw: dict, home_score: int, away_score: int) -> MatchEvent:
        game_id = raw.get("_game_id", "")
        type_text = raw.get("type", {}).get("text", "")
        event_type = EVENT_TYPE_MAP.get(type_text, "substitution")

        # Special case: End Period with period number 2 → fulltime
        if type_text == "End Period" and raw.get("period", {}).get("number", 1) == 2:
            event_type = "fulltime"

        clock_str = raw.get("clock", {}).get("displayValue", "0:00")
        try:
            minute = int(clock_str.split(":")[0])
        except (ValueError, IndexError):
            minute = 0

        athletes = raw.get("athletesInvolved", [])
        player_name = athletes[0].get("displayName") if athletes else None

        team_abbr = raw.get("team", {}).get("abbreviation")

        # Deduplication composite key — must be stable across polls
        dedup_key = (
            f"espn_{game_id}_{minute}_{type_text}_{team_abbr or 'none'}_{player_name or 'none'}"
            .replace(" ", "_")
            .lower()
        )

        return MatchEvent(
            external_event_id=dedup_key,
            event_type=event_type,
            team_code=team_abbr,
            player_name=player_name,
            minute=minute,
            extra_minute=None,
            home_score_after=home_score,
            away_score_after=away_score,
            raw_payload={k: v for k, v in raw.items() if k != "_game_id"},
        )
