# Research: World Cup 2026 AI Prediction Dashboard

**Phase**: 0 — Research & Decision Log
**Date**: 2026-06-21
**Feature**: `specs/001-worldcup-ai-predictions/spec.md`

---

## Decision 1: ML Model Architecture

**Decision**: Two-model chain — XGBoost (pre-match) + Poisson in-game update

**Rationale**: A single model with live features zeroed pre-kickoff creates systematic bias
because the model cannot distinguish "0-0 at kickoff" from "0-0 at minute 85, a very
different game state." Two separate models with clean separation of concerns solves this.
XGBoost handles the 5k–10k historical match dataset well without overfitting if tree
depth is constrained (max_depth 3–5, early stopping on validation).

**Chain flow**:
```
Historical data → Pre-match XGBoost → P(home_win), P(draw), P(away_win), xG_home, xG_away
                                              ↓ these become IN-GAME features
Live events     → In-game Poisson   → Updated probabilities (Bayesian update)
```

**Alternatives considered**:
- Neural network: Rejected. Dataset too small (~5k–10k matches) for stable training;
  also lacks native interpretability needed for the top-3 factors requirement.
- Single model with dummy live features: Rejected. Introduces systematic kickoff bias
  and makes feature attribution (SHAP) unreliable pre-match.

**Critical failure mode**: Data leakage — the in-game training labels must use the
**final result**, not the result at time T. Training must only use data from match
minute 0–T to predict final outcome.

---

## Decision 2: Probability Calibration

**Decision**: `CalibratedClassifierCV(estimator=xgb, method='isotonic', cv=5)`

**Rationale**: XGBoost's raw `predict_proba` is overconfident for multi-class problems —
probabilities cluster toward 0 and 1. Isotonic regression corrects any monotone
distortion non-parametrically and is proven superior to Platt scaling (logistic) when
the score distribution is non-Gaussian. 5-fold cross-validation inside the calibrator
prevents overfitting the calibration map.

**Caveat**: Isotonic regression requires ≥500 samples per class to avoid overfitting.
If a class (e.g., Draw) has fewer samples, fall back to Platt scaling.

---

## Decision 3: Feature Interpretability (Top-3 Factors)

**Decision**: `shap.TreeExplainer` — per-class SHAP values mapped to natural language

**Rationale**: `shap.TreeExplainer(model)` returns a `(n_samples, n_features, n_classes)`
array. For each prediction, take `shap_values[:, :, predicted_class]`, rank by absolute
value, and take the top 3. Convert from log-odds units to percent impact via `np.expm1`.

Each SHAP factor is then mapped to a human-readable label via a `FACTOR_LABELS` dict:
```python
FACTOR_LABELS = {
    "fifa_ranking_diff": lambda v: f"FIFA ranking gap: {abs(v):.0f} places",
    "h2h_win_rate_home": lambda v: f"Won {v*100:.0f}% of last 10 H2H meetings",
    "recent_form_home":  lambda v: f"Last 5 matches: {'strong' if v > 9 else 'average'} form",
    ...
}
```

**Critical failure mode**: Summing SHAP values across all classes rather than
conditioning on the predicted class produces meaningless cancellation artifacts.

---

## Decision 4: In-Game Probability Update (Poisson Model)

**Decision**: Precomputed Poisson score-state transition table, queried at runtime

**Rationale**: Given current score H:A at minute T, remaining goals follow independent
Poisson distributions:
- `λ_remaining_home = λ_prematch_home × (1 − T/90) × trailing_factor`
- `λ_remaining_away = λ_prematch_away × (1 − T/90) × trailing_factor`

Where `trailing_factor = 1.15` if team is losing (teams push harder when behind).
Dixon-Coles ρ correction is applied only to scores 0-0, 1-0, 0-1, 1-1.

Enumerate all `(h_add, a_add) in range(0, 10)` additional goals → O(100) operations per
update — fast enough for real-time. Precompute at app startup; query is O(1).

**Empirical adjustment**: A +15% injury-time goal surge is applied for minutes 75–90
(backed by published football statistics research).

---

## Decision 5: Confidence Intervals

**Decision**: Bootstrap 200 calibrated model instances; report mean ± 1.96×std

**Rationale**: This is the statistically honest representation of model uncertainty. Train
200 bootstrap resamples of the calibrated XGBoost and store the distribution. At inference:
`confidence_low = mean − 1.96×std`, `confidence_high = mean + 1.96×std`.

This is computed **offline** at training time, not at inference. The mean and std are
stored per match-type segment (Group Stage vs. Knockout) so inference remains fast.

**Do not use**: Softmax entropy or raw predict_proba spread — these massively underestimate
uncertainty for out-of-distribution matches (e.g., first-ever meeting between two teams).

---

## Decision 6: Live Data API

**Decision**: ESPN unofficial API (free, no key) as primary; adapter pattern enables
upgrade to API-Football Pro later without touching business logic.

**Revised rationale**: No free API offers full live World Cup event data (goals, cards,
substitutions) with a sustainable request rate. The paid options (API-Football Pro $40-80/mo,
SportMonks €78-150/mo, Football-Data.org Tier 2 €50/mo) are viable but add cost to a
personal project. The ESPN unofficial API is genuinely free, requires no authentication,
covers the 2026 FIFA World Cup, and returns all live matches with embedded play-by-play
events in a **single request** — making it architecturally superior to per-match polling.

**ESPN API — verified structure**:
- Scoreboard: `https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard`
- No API key, no rate limit documented, no authentication
- Single call returns all current matches with embedded `details` (play-by-play events)
- Status values: `STATUS_SCHEDULED`, `STATUS_FIRST_HALF`, `STATUS_HALFTIME`,
  `STATUS_SECOND_HALF`, `STATUS_FULL_TIME`
- Event fields: `type.text` (Goal/Yellow Card/Red Card/Own Goal), `clock.displayValue`
  (match minute), `team.displayName`, `athletesInvolved[0].displayName`, `ownGoal` flag
- Score: per-team `score` field in `competitors` array
- Deduplication: construct `external_event_id = f"espn_{gameId}_{minute}_{type}_{team}"`
  (ESPN events do not have stable IDs in the scoreboard endpoint)

**Polling strategy**: One request to the scoreboard endpoint every 15 seconds covers
all simultaneous live matches. At 4 req/min total (not per match), this is far lighter
than per-match polling.

**Honest risk**: ESPN's API is undocumented and unsupported. It can change without
notice. The `FootballDataProvider` ABC isolates all ESPN-specific logic so a swap to
API-Football Pro is a one-file change (`api_football.py` replaces `espn.py`).

**Full provider comparison**:
| Provider          | Goals | Cards | Subs | WC 2026 | Auth  | Cost/mo |
|-------------------|-------|-------|------|---------|-------|---------|
| **ESPN (unofficial)** | ✅ | ✅ | ⚠️¹ | ✅  | None  | **Free** |
| API-Football       | ✅   | ✅    | ✅   | ✅      | Key   | $40-80  |
| Football-Data.org  | ✅   | ❌    | ❌   | ✅(paid)| Key   | €50     |
| SportMonks         | ✅   | ✅    | ✅   | ✅+add-on| Key  | €78-150 |
| TheSportsDB        | ❌   | ❌    | ❌   | partial | None  | Free    |

¹ Substitution events visible in ESPN data but with less detail than paid APIs.

**Adapter pattern** (FootballDataProvider ABC + ESPNAdapter):
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

EventType = Literal["goal", "yellow_card", "red_card", "substitution"]

@dataclass
class MatchEvent:
    external_id: str       # deduplication key (constructed, not from API)
    minute: int
    event_type: EventType
    team: str
    player: str
    home_score: int
    away_score: int
    is_own_goal: bool = False

class FootballDataProvider(ABC):
    @abstractmethod
    async def get_all_live_states(self) -> list[dict]: ...
    # Returns normalized state for ALL current live matches in one call
    # (ESPN-style: one endpoint for all matches)

    @abstractmethod
    def normalize_event(self, raw: dict, home_score: int, away_score: int) -> MatchEvent: ...

class ESPNAdapter(FootballDataProvider):
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"

    async def get_all_live_states(self) -> list[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/scoreboard", timeout=10)
            resp.raise_for_status()
        return resp.json().get("events", [])

    def normalize_event(self, raw: dict, home_score: int, away_score: int) -> MatchEvent:
        type_text = raw.get("type", {}).get("text", "")
        type_map = {
            "Goal": "goal", "Own Goal": "goal",
            "Yellow Card": "yellow_card", "Red Card": "red_card",
            "Substitution": "substitution",
        }
        minute_str = raw.get("clock", {}).get("displayValue", "0'")
        minute = int(minute_str.replace("'", "").strip() or 0)
        team = raw.get("team", {}).get("displayName", "")
        player = (raw.get("athletesInvolved") or [{}])[0].get("displayName", "")
        ext_id = f"espn_{team}_{minute}_{type_text}_{player}".replace(" ", "_")
        return MatchEvent(
            external_id=ext_id,
            minute=minute,
            event_type=type_map.get(type_text, "substitution"),
            team=team,
            player=player,
            home_score=home_score,
            away_score=away_score,
            is_own_goal=raw.get("ownGoal", False),
        )
```

**Note on `get_all_live_states` vs `get_match_state`**: The ABC now uses a single
`get_all_live_states()` call (ESPN pattern) instead of per-match polling. The ingestion
service loops over returned events and routes each to the correct match. For paid APIs
that require per-match calls, the subclass implements per-match fetching internally and
returns a list with one element.

**Polling interval**: 15 seconds (one ESPN call covers all live matches). During
pre-match window: 5 minutes to check for status changes.

---

## Decision 7: WebSocket Architecture

**Decision**: FastAPI native WebSocket + in-memory `ConnectionManager` + asyncio lifespan

**Rationale**: At <50 concurrent users on a single Railway instance, there is no need for
Redis Pub/Sub or Socket.IO. A plain `defaultdict(set)` mapping `match_id → Set[WebSocket]`
with a `broadcast_to_match()` method is correct, testable, and zero-dependency.

**Keep-alive**: Railway closes idle WebSocket connections after ~60s. Server sends
`{"type": "ping"}` every 30 seconds. Client echoes `{"type": "pong"}`.

**Scheduler**: `asyncio.create_task()` inside FastAPI's `lifespan()` context manager
(not APScheduler — APScheduler's default executor silently swallows task exceptions).

**CORS for Vercel ↔ Railway**: `allow_origins=["https://*.vercel.app"]` requires
Starlette ≥ 0.28. Pin `starlette>=0.28.0` in requirements.

**Critical pattern**: Always catch `WebSocketDisconnect` inside an infinite receive loop,
never outside. Dead connections must be collected in a separate set, then removed after
iteration — never modify a set while iterating it.

---

## Decision 8: Deployment Architecture

**Decision**: Vercel (React SPA) + Railway (FastAPI + PostgreSQL)

**Implications**:
- Frontend env vars: `VITE_API_URL=https://worldcup-backend.railway.app` and
  `VITE_WS_URL=wss://worldcup-backend.railway.app` (injected at Vercel build time)
- Vercel does **not** proxy WebSocket connections → frontend connects directly to Railway
- Railway `Procfile`: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- PostgreSQL: Railway managed Postgres service (connection string via `DATABASE_URL` env var)
- ML model artifacts (`.joblib` files) committed to repo or stored in Railway volume

**Free tier viability**: Railway's free tier has a compute hour limit — not suitable for
a 24/7 polling scheduler during the tournament. A paid plan ($5-10/mo) is needed.

---

## Decision 9: Historical Data Sources for ML Training

**Decision**: Kaggle "International football results from 1872 to 2024" (primary) +
StatsBomb Open Data (xG features) + openfootball (World Cup fixtures backup)

**Sources**:

| Source | What it provides | Format | Access |
|--------|-----------------|--------|--------|
| Kaggle "International football results" | ~45k historical W/D/L results with scorelines since 1872 | CSV | Free download, no key |
| StatsBomb Open Data (GitHub) | Event-level data (passes, shots, xG, pressures) for selected competitions including some World Cups | JSON | Free, github.com/statsbomb/open-data |
| openfootball/world-cup (GitHub) | World Cup results since 1930 | JSON | Free, backup/verification |
| FIFA website | Current team rankings | HTML (manual CSV export) | Free |

**Why StatsBomb**: The `goals_scored_avg` / `goals_conceded_avg` features are stronger
predictors when based on **xG** (expected goals) rather than raw goals. StatsBomb Open
Data provides free xG for competitions it covers, including Women's World Cup and some
club competitions. Where xG is unavailable, we fall back to raw goal averages.

**Seeding scripts**:
- `ml/download_data.py` — downloads Kaggle CSV + StatsBomb JSON from GitHub
- `scripts/seed_teams.py` — insert 48 teams with FIFA rankings (manual CSV input)
- `scripts/seed_matches.py` — insert all 64 WC 2026 fixtures (from ESPN API or manual)

Training is an offline step run once before the tournament, not on Railway.

---

## All Clarifications Resolved

| # | Question | Resolution |
|---|---------|-----------|
| 1 | One model or two? | Two-model chain (pre-match XGBoost + in-game Poisson) |
| 2 | Calibration method? | Isotonic regression via CalibratedClassifierCV |
| 3 | Top-3 factors how? | SHAP TreeExplainer per-class, mapped to natural language |
| 4 | In-game update method? | Precomputed Poisson table |
| 5 | Confidence intervals? | Bootstrap 200x at training time |
| 6 | Which data API? | ESPN unofficial (free) via ESPNAdapter; upgrade path to API-Football Pro |
| 7 | WebSocket backend? | FastAPI native + asyncio lifespan |
| 8 | Deployment target? | Vercel (frontend) + Railway (backend + DB) |
| 9 | Training data source? | Kaggle international results + StatsBomb Open Data (xG) + openfootball |
