# Data Model: World Cup 2026 AI Prediction Dashboard

**Phase**: 1 — Design
**Date**: 2026-06-21

---

## Entity Relationship Overview

```
teams ←──────────── matches ──────────→ teams
                      │
             ┌────────┼────────┐
             │        │        │
         live_events  │  accuracy_records
             │        │
             └──→ predictions ←── model_versions
```

---

## PostgreSQL Schema

### Table: `teams`

Stores all 48 teams participating in the 2026 World Cup.

```sql
CREATE TABLE teams (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    country_code    CHAR(3) NOT NULL,          -- ISO 3166-1 alpha-3
    fifa_ranking    INTEGER,                   -- Current ranking (lower = better)
    group_letter    CHAR(1),                   -- 'A'–'L' (2026 has 12 groups)
    avg_goals_scored    NUMERIC(4,2),          -- Last 10 matches
    avg_goals_conceded  NUMERIC(4,2),          -- Last 10 matches
    form_points     INTEGER,                   -- Points in last 5 matches (0–15)
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_teams_country_code ON teams(country_code);
```

**State transitions**: FIFA ranking updates when FIFA releases new rankings (~monthly).
Form and averages are recalculated by the data seeding/update scripts.

---

### Table: `head_to_head`

Stores last 10 historical meetings between any two teams (pre-computed aggregates).

```sql
CREATE TABLE head_to_head (
    id              SERIAL PRIMARY KEY,
    team_a_id       INTEGER NOT NULL REFERENCES teams(id),
    team_b_id       INTEGER NOT NULL REFERENCES teams(id),
    match_date      DATE NOT NULL,
    team_a_score    INTEGER NOT NULL,
    team_b_score    INTEGER NOT NULL,
    competition     VARCHAR(100),
    CONSTRAINT h2h_team_order CHECK (team_a_id < team_b_id)  -- canonical ordering
);

CREATE INDEX idx_h2h_pair ON head_to_head(team_a_id, team_b_id);
```

**Note**: The `CHECK` constraint enforces that `team_a_id < team_b_id` always, so
every pair has exactly one canonical representation. Queries must use `LEAST`/`GREATEST`
to look up a pair in either direction.

---

### Table: `matches`

Every World Cup 2026 fixture — pre-seeded from the tournament schedule.

```sql
CREATE TABLE matches (
    id              SERIAL PRIMARY KEY,
    external_id     VARCHAR(50) UNIQUE,        -- Provider fixture ID (API-Football etc.)
    home_team_id    INTEGER NOT NULL REFERENCES teams(id),
    away_team_id    INTEGER NOT NULL REFERENCES teams(id),
    scheduled_at    TIMESTAMPTZ NOT NULL,
    venue           VARCHAR(150),
    city            VARCHAR(100),
    stage           VARCHAR(50) NOT NULL,      -- 'Group A', 'Round of 16', etc.
    status          VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    -- status enum: scheduled | live | halftime | finished | postponed | cancelled
    home_score      INTEGER,                   -- NULL until match starts
    away_score      INTEGER,                   -- NULL until match starts
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_status CHECK (
        status IN ('scheduled','live','halftime','finished','postponed','cancelled')
    )
);

CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_scheduled_at ON matches(scheduled_at);
CREATE INDEX idx_matches_stage ON matches(stage);
```

**Status transitions**:
```
scheduled → live → halftime → live → finished
scheduled → postponed
scheduled → cancelled
```

---

### Table: `live_events`

Individual match events ingested from the data provider. Primary deduplication key
is `external_event_id` — guaranteed unique per provider.

```sql
CREATE TABLE live_events (
    id                  SERIAL PRIMARY KEY,
    match_id            INTEGER NOT NULL REFERENCES matches(id),
    external_event_id   VARCHAR(100) UNIQUE NOT NULL,  -- deduplication key
    event_type          VARCHAR(20) NOT NULL,
    -- event_type enum: goal | yellow_card | red_card | substitution | halftime | fulltime
    team_id             INTEGER REFERENCES teams(id),
    player_name         VARCHAR(100),
    minute              INTEGER NOT NULL,
    extra_minute        INTEGER,                -- injury time (+1, +2, etc.)
    home_score_after    INTEGER NOT NULL,
    away_score_after    INTEGER NOT NULL,
    raw_payload         JSONB,                  -- original API response for debugging
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_event_type CHECK (
        event_type IN ('goal','yellow_card','red_card','substitution','halftime','fulltime')
    )
);

CREATE INDEX idx_live_events_match_id ON live_events(match_id);
CREATE INDEX idx_live_events_external_id ON live_events(external_event_id);
```

**Deduplication guarantee**: The `UNIQUE` constraint on `external_event_id` means
concurrent poll results for the same event result in a `ON CONFLICT DO NOTHING` — the
prediction pipeline is only triggered when a new row is actually inserted.

---

### Table: `model_versions`

Registry of all trained ML model artifacts. At most one active version per type.

```sql
CREATE TABLE model_versions (
    id              SERIAL PRIMARY KEY,
    version         VARCHAR(20) NOT NULL UNIQUE,   -- semantic: '1.0.0'
    model_type      VARCHAR(20) NOT NULL,
    -- model_type enum: prematch | ingame
    training_date   DATE NOT NULL,
    description     TEXT,
    artifact_path   VARCHAR(300) NOT NULL,         -- relative path to .joblib file
    accuracy_on_val NUMERIC(5,4),                  -- validation set accuracy (0-1)
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_model_type CHECK (model_type IN ('prematch', 'ingame'))
);

-- Partial index: only one active model per type
CREATE UNIQUE INDEX idx_one_active_prematch
    ON model_versions(model_type) WHERE is_active = TRUE;
```

**Note**: The partial unique index `WHERE is_active = TRUE` enforces that only one
prematch model and one ingame model can be active simultaneously, enforced at the DB
level without application logic.

---

### Table: `predictions`

Every prediction snapshot — one row per match per event (forms a time series).

```sql
CREATE TABLE predictions (
    id                  SERIAL PRIMARY KEY,
    match_id            INTEGER NOT NULL REFERENCES matches(id),
    model_version_id    INTEGER NOT NULL REFERENCES model_versions(id),
    prediction_type     VARCHAR(10) NOT NULL,   -- 'prematch' | 'live'
    home_win_prob       NUMERIC(6,5) NOT NULL,  -- 0.00000–1.00000
    draw_prob           NUMERIC(6,5) NOT NULL,
    away_win_prob       NUMERIC(6,5) NOT NULL,
    expected_home_goals NUMERIC(4,2) NOT NULL,
    expected_away_goals NUMERIC(4,2) NOT NULL,
    confidence_low      NUMERIC(6,5) NOT NULL,  -- bootstrap CI lower bound
    confidence_high     NUMERIC(6,5) NOT NULL,  -- bootstrap CI upper bound
    top_factors         JSONB NOT NULL,
    -- top_factors shape:
    -- [{"feature": "fifa_ranking_diff", "impact_pct": 12.3,
    --   "label": "France ranked 5 places above Argentina"}]
    triggering_event_id INTEGER REFERENCES live_events(id),  -- NULL for prematch
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_probs_sum CHECK (
        ABS(home_win_prob + draw_prob + away_win_prob - 1.0) < 0.001
    ),
    CONSTRAINT chk_prediction_type CHECK (
        prediction_type IN ('prematch', 'live')
    )
);

CREATE INDEX idx_predictions_match_id ON predictions(match_id, created_at DESC);
CREATE INDEX idx_predictions_latest ON predictions(match_id, created_at DESC)
    WHERE prediction_type = 'live';
```

**Constraint note**: `CHECK (ABS(sum - 1.0) < 0.001)` tolerates floating-point rounding
while enforcing that probabilities always sum to 100%.

---

### Table: `accuracy_records`

One row per completed match — tracks whether the pre-match prediction was correct.

```sql
CREATE TABLE accuracy_records (
    id                  SERIAL PRIMARY KEY,
    match_id            INTEGER NOT NULL UNIQUE REFERENCES matches(id),
    prediction_id       INTEGER NOT NULL REFERENCES predictions(id),
    -- prediction_id points to the LAST pre-match prediction (closest to kickoff)
    predicted_outcome   VARCHAR(10) NOT NULL,   -- 'home_win' | 'draw' | 'away_win'
    actual_outcome      VARCHAR(10) NOT NULL,
    predicted_confidence NUMERIC(6,5) NOT NULL,
    was_correct         BOOLEAN NOT NULL,
    stage               VARCHAR(50) NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_outcome CHECK (
        predicted_outcome IN ('home_win','draw','away_win') AND
        actual_outcome    IN ('home_win','draw','away_win')
    )
);

CREATE INDEX idx_accuracy_stage ON accuracy_records(stage);
CREATE INDEX idx_accuracy_correct ON accuracy_records(was_correct);
```

---

## ML Feature Sets

### Pre-Match Features (XGBoost input)

| Feature | Type | Source | Description |
|---------|------|---------|-------------|
| `fifa_ranking_home` | int | teams table | Home team FIFA rank (lower=better) |
| `fifa_ranking_away` | int | teams table | Away team FIFA rank |
| `ranking_diff` | int | derived | home rank − away rank |
| `form_pts_home` | int | teams table | Points in last 5 matches (0–15) |
| `form_pts_away` | int | teams table | Points in last 5 matches (0–15) |
| `goals_scored_avg_home` | float | teams table | Goals/game, last 10 matches |
| `goals_conceded_avg_home` | float | teams table | Goals conceded/game, last 10 |
| `goals_scored_avg_away` | float | teams table | Goals/game, last 10 matches |
| `goals_conceded_avg_away` | float | teams table | Goals conceded/game, last 10 |
| `h2h_home_win_rate` | float | head_to_head | Win rate in last 10 H2H meetings |
| `h2h_goal_diff_avg` | float | head_to_head | Avg goal diff (home perspective) |
| `h2h_matches_count` | int | head_to_head | Number of H2H matches available |
| `is_neutral_venue` | bool | matches | World Cup = almost always neutral |
| `stage_weight` | float | derived | 0.5 group stage, 1.0 knockout |

**Target** (3-class): `outcome ∈ {home_win, draw, away_win}`
**Additional regression targets**: `expected_home_goals`, `expected_away_goals`

### In-Game Features (Poisson model input)

Derived in real-time from live_events accumulated for a match:

| Feature | Derived From |
|---------|-------------|
| `current_score_diff` | home_score − away_score from latest live_event |
| `minute` | latest event minute |
| `red_cards_home` | COUNT of red_card events for home team |
| `red_cards_away` | COUNT of red_card events for away team |
| `is_halftime` | TRUE if last status = 'halftime' |
| `prematch_xg_home` | expected_home_goals from pre-match prediction |
| `prematch_xg_away` | expected_away_goals from pre-match prediction |

---

## Validation Rules (enforced by Pydantic at API boundary)

- Probabilities: `0.0 ≤ p ≤ 1.0` and `|p_home + p_draw + p_away − 1| < 0.001`
- Match scores: `0 ≤ score ≤ 20` (sanity cap)
- Minutes: `0 ≤ minute ≤ 120` (extra time)
- `confidence_low ≤ home_win_prob ≤ confidence_high`
- `top_factors` array length: exactly 3 items
- `external_event_id`: non-empty string, unique constraint enforced at DB level
