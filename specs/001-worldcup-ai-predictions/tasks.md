# Tasks: World Cup 2026 AI Prediction Dashboard

**Input**: Design documents from `specs/001-worldcup-ai-predictions/`
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)
**Stack**: Python 3.11 + FastAPI + PostgreSQL (Railway) | React 18 + Tailwind (Vercel)

## Model Key

| Badge | Command | Use when |
|-------|---------|---------|
| 🟢 `/quick` | Haiku | Config files, schemas mirroring a contract, directory setup, renames |
| 🔵 `/task` | Sonnet | Feature implementation, services, components, tests, hooks |
| 🔴 `/deep` | Opus | Complex algorithms (Poisson math, SHAP mapping), WebSocket edge cases |

## Skill Key

| Tag | Skill | Invoke with |
|-----|-------|------------|
| `[fe]` | frontend-design | `/frontend-design` |
| `[vd]` | vercel deploy | `/vercel:deploy` |
| `[tdd]` | test-driven dev | `/superpowers:test-driven-development` |
| `[dbg]` | systematic debug | `/superpowers:systematic-debugging` |

---

## Phase 1: Setup (Project Structure)

**Purpose**: Create the repository layout and tooling. No logic, just scaffolding.

- [X] T001 Create root directory structure: `backend/`, `frontend/`, `specs/` as defined in plan.md `→ 🟢 /quick`
- [X] T002 Create `backend/` Python project: `pyproject.toml`, `requirements.txt`, `requirements-ml.txt`, `requirements-dev.txt` with all deps from plan.md `→ 🟢 /quick`
- [X] T003 [P] Create `frontend/` Vite + React + TypeScript + Tailwind project via `npm create vite@latest` `→ 🟢 /quick`
- [X] T004 [P] Create `docker-compose.yml` with three services: `postgres:16`, `backend` (FastAPI), `frontend` (Vite dev) per quickstart.md `→ 🟢 /quick`
- [X] T005 [P] Create `.env.example` documenting all required variables: `DATABASE_URL`, `FOOTBALL_API_PROVIDER`, `ENVIRONMENT`, `ALLOWED_ORIGINS`, `VITE_API_URL`, `VITE_WS_URL` `→ 🟢 /quick`
- [X] T006 [P] Create `backend/Procfile` with Railway entry point: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT` and `frontend/vercel.json` with SPA fallback rewrite `→ 🟢 /quick`

**Checkpoint**: `docker compose up --build` starts all three services without errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on.
**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Database & Configuration

- [X] T007 Create `backend/app/core/config.py` using `pydantic-settings`: read `DATABASE_URL`, `FOOTBALL_API_PROVIDER`, `ENVIRONMENT`, `ALLOWED_ORIGINS` from environment `→ 🟢 /quick`
- [X] T008 Create `backend/app/core/database.py`: SQLAlchemy async engine + `AsyncSession` factory + `get_db` FastAPI dependency `→ 🔵 /task`
- [X] T009 Create `backend/alembic/` structure and `alembic.ini`; configure `env.py` to read `DATABASE_URL` from pydantic settings `→ 🔵 /task`

### SQLAlchemy ORM Models (all 6 tables from data-model.md)

- [X] T010 [P] Create `backend/app/models/team.py`: `Team` model with all columns from data-model.md `teams` table including constraints `→ 🟢 /quick`
- [X] T011 [P] Create `backend/app/models/match.py`: `Match` model with foreign keys to `Team`, status enum, score columns, CHECK constraint on status values `→ 🔵 /task`
- [X] T012 [P] Create `backend/app/models/live_event.py`: `LiveEvent` model with `external_event_id UNIQUE` constraint (deduplication key) and `raw_payload JSONB` `→ 🟢 /quick`
- [X] T013 [P] Create `backend/app/models/model_version.py`: `ModelVersion` model with `is_active` + partial unique index `WHERE is_active = TRUE` per data-model.md `→ 🟢 /quick`
- [X] T014 [P] Create `backend/app/models/prediction.py`: `Prediction` model with `top_factors JSONB`, probability `CHECK` constraint (sum ≈ 1.0), foreign keys to `Match` and `ModelVersion` `→ 🔵 /task`
- [X] T015 [P] Create `backend/app/models/accuracy_record.py`: `AccuracyRecord` model with UNIQUE on `match_id` per data-model.md `→ 🟢 /quick`
- [X] T016 Create Alembic migration `001_initial_schema.py` from all 6 models; run `alembic upgrade head` to verify clean migration `→ 🔵 /task`

### Pydantic Schemas (mirroring REST contract)

- [X] T017 [P] Create `backend/app/schemas/match.py`: `MatchListResponse`, `MatchDetailResponse`, `TeamSchema`, `PredictionSchema` — fields must match `contracts/rest-api.md` exactly `→ 🟢 /quick`
- [X] T018 [P] Create `backend/app/schemas/prediction.py`: `PredictionHistoryResponse`, `FactorSchema` with `feature`, `impact_pct`, `label` fields `→ 🟢 /quick`
- [X] T019 [P] Create `backend/app/schemas/accuracy.py`: `AccuracySummaryResponse`, `StageAccuracySchema`, `NotableMissSchema` per `contracts/rest-api.md` `→ 🟢 /quick`

### FastAPI App Skeleton

- [X] T020 Create `backend/app/main.py`: FastAPI app with `CORSMiddleware` (`allow_origins` from config, Starlette ≥ 0.28 wildcard), include all routers, `GET /health` endpoint returning DB + model status `→ 🔵 /task`
- [X] T021 Create `backend/app/api/__init__.py` aggregating all routers; add stub `matches.py`, `predictions.py`, `accuracy.py`, `ws.py`, `admin.py` router files with placeholder `404` responses `→ 🟢 /quick`

### Data Seeding Scripts

- [X] T022 [P] Create `backend/scripts/seed_teams.py`: insert 48 World Cup 2026 teams with FIFA rankings and group assignments; idempotent (upsert by country_code) `→ 🔵 /task`
- [X] T023 [P] Create `backend/scripts/seed_matches.py`: insert all 64 WC 2026 fixtures with `external_id` mapped to ESPN `gameId`; pull schedule from ESPN scoreboard or hardcode from official draw `→ 🔵 /task`

**Checkpoint**: `GET /health` returns `{"status": "ok", "db": "connected"}`; `GET /api/v1/matches` returns 64 matches with team names.

---

## Phase 3: User Story 1 — Pre-Match Prediction Viewer (Priority: P1) 🎯 MVP

**Goal**: Show Win/Draw/Loss probabilities + expected score + top-3 factors for every upcoming match using a trained XGBoost model.

**Independent Test**: Navigate to any upcoming match card → see probabilities summing to 100%, expected scoreline, confidence indicator, and 3 plain-language factors. No live data feed needed.

### ML Pipeline (offline training)

- [X] T024 Create `backend/ml/download_data.py`: download Kaggle "International football results" CSV and StatsBomb Open Data JSON from GitHub; save to `backend/ml/data/raw/` `→ 🔵 /task`
- [X] T025 Create `backend/ml/features.py`: `build_prematch_features(match, teams, h2h)` function returning a feature dict with all 14 pre-match features from data-model.md; pure function, no DB dependency `→ 🔴 /deep`
- [X] T026 Create `backend/ml/train_prematch.py`: train `XGBoostClassifier(max_depth=4, n_estimators=300)` wrapped in `CalibratedClassifierCV(method='isotonic', cv=5)`; bootstrap 200× for CI offsets; save to `backend/ml/artifacts/prematch_v1.0.0.joblib` `→ 🔴 /deep`
- [X] T027 [P] Create `backend/ml/evaluate.py`: print accuracy, calibration curve, and per-class F1 on held-out test set; flag if Draw class has <500 samples (Platt fallback trigger) `→ 🔵 /task`
- [X] T028 Create `backend/ml/register_model.py`: insert row into `model_versions`, set `is_active=TRUE`, deactivate previous active model of same type `→ 🔵 /task`

### Prediction Engine (serving)

- [X] T029 Create `backend/app/services/prediction_engine.py`: load active pre-match model at startup; implement `predict_prematch(match_id, db)` → computes features, runs inference, calls SHAP TreeExplainer, maps top-3 SHAP values to `FACTOR_LABELS` natural-language strings, returns `PredictionResult` `→ 🔴 /deep`
- [X] T030 Create `backend/scripts/generate_prematch_predictions.py`: call `predict_prematch()` for every `status='scheduled'` match; store in `predictions` table with `prediction_type='prematch'` `→ 🔵 /task`

### REST Endpoints (US1)

- [X] T031 Implement `GET /api/v1/matches` in `backend/app/api/matches.py`: query all matches with latest prediction join; support `?status=` and `?stage=` filters; return `MatchListResponse` per contract `→ 🔵 /task`
- [X] T032 Implement `GET /api/v1/matches/{match_id}` in `backend/app/api/matches.py`: full match detail with `live_events` array and `prediction` object per `contracts/rest-api.md` `→ 🔵 /task`
- [X] T033 [P] Implement `GET /api/v1/predictions/{match_id}/latest` in `backend/app/api/predictions.py`: return most recent prediction row for match `→ 🟢 /quick`
- [X] T034 [P] Implement `GET /api/v1/predictions/{match_id}/history` in `backend/app/api/predictions.py`: return all predictions ordered by `created_at` with triggering event details `→ 🔵 /task`

### React Frontend — US1 Components `[fe]`

- [X] T035 Create `frontend/src/types/index.ts`: TypeScript interfaces for `Match`, `Team`, `Prediction`, `Factor`, `LiveEvent`, `AccuracySummary` — must match REST contract response shapes exactly `→ 🟢 /quick` `[fe]`
- [X] T036 Create `frontend/src/services/api.ts`: typed fetch wrappers for all REST endpoints using `VITE_API_URL`; include error handling for 404/503 `→ 🔵 /task` `[fe]`
- [X] T037 Create `frontend/src/hooks/useMatches.ts`: TanStack Query hook fetching `/api/v1/matches`; poll every 30s; return matches grouped by stage `→ 🔵 /task` `[fe]`
- [X] T038 [P] Create `frontend/src/components/ProbabilityBar/ProbabilityBar.tsx`: animated three-segment bar (home/draw/away) with CSS transitions on probability change; shows team names and percentages `→ 🔵 /task` `[fe]`
- [X] T039 [P] Create `frontend/src/components/FactorsPanel/FactorsPanel.tsx`: list of exactly 3 factors with feature label, impact percentage badge, and plain-language description `→ 🔵 /task` `[fe]`
- [X] T040 [P] Create `frontend/src/components/LiveBadge/LiveBadge.tsx`: pulsing "LIVE" pill with CSS animation; "UPCOMING" and "FT" variants `→ 🟢 /quick` `[fe]`
- [X] T041 Create `frontend/src/components/MatchCard/MatchCard.tsx`: composites LiveBadge + ProbabilityBar + FactorsPanel; shows current score if live/finished; shows "Limited data" badge when factor count < 3 `→ 🔵 /task` `[fe]`
- [X] T042 Create `frontend/src/pages/Dashboard.tsx`: fetches all matches via `useMatches`; groups by stage; renders grid of `MatchCard` components; loading skeleton state `→ 🔵 /task` `[fe]`
- [X] T043 Wire up `frontend/src/App.tsx` with React Router: `/` → `Dashboard`, `/match/:id` → `MatchDetail` (stub page for now) `→ 🟢 /quick` `[fe]`

**Checkpoint**: `GET /api/v1/matches` returns predictions; Dashboard shows 64 match cards with probabilities, confidence, and 3 factors. User Story 1 fully testable independently.

---

## Phase 4: User Story 2 — Live Match Prediction Updates (Priority: P1)

**Goal**: When a match is live, probabilities update within 30 seconds of any goal, red card, or substitution, pushed to the dashboard via WebSocket without page refresh.

**Independent Test**: Set a match to `status='live'` via dev script → inject a goal via `/admin/events/simulate` → dashboard probability bars animate within 30 seconds. No real API key needed (mock provider).

### Live Data Provider Layer

- [X] T044 Create `backend/app/services/provider/base.py`: `FootballDataProvider` ABC with `get_all_live_states() -> list[dict]` and `normalize_event(raw, home_score, away_score) -> MatchEvent`; `MatchEvent` dataclass per research.md `→ 🔵 /task`
- [X] T045 Create `backend/app/services/provider/mock.py`: `MockProvider` implementing ABC; returns deterministic events in a fixed sequence per match; reads match state from DB to simulate realistic progression `→ 🔵 /task`
- [X] T046 Create `backend/app/services/provider/espn.py`: `ESPNAdapter` implementing ABC; calls `https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard`; maps ESPN `details` events to `MatchEvent` using composite deduplication key `f"espn_{gameId}_{minute}_{type}_{team}_{player}"` per research.md `→ 🔴 /deep`

### Ingestion Service

- [X] T047 Create `backend/app/services/ingestion.py`: `run_polling_loop()` async function; every 15s calls `provider.get_all_live_states()`; for each event: insert into `live_events` with `ON CONFLICT (external_event_id) DO NOTHING`; only trigger prediction update if row was actually inserted; broadcast `live_event` WS message immediately; then trigger `predict_ingame()` `→ 🔴 /deep`

### In-Game Prediction (Poisson Update)

- [X] T048 Add `predict_ingame(match_id, triggering_event_id, db)` to `backend/app/services/prediction_engine.py`: fetch pre-match xG (λ_home, λ_away) from last prematch prediction; compute remaining λ scaled by `(1 − minute/90)` with `trailing_factor=1.15` for losing team; enumerate P(h,a) for h,a in 0..9 additional goals; apply Dixon-Coles ρ correction for (0-0), (1-0), (0-1), (1-1); sum outcomes to get P(home_win), P(draw), P(away_win); blend with pre-match priors weighted by `minute/90`; store prediction; return result `→ 🔴 /deep`

### WebSocket + Broadcast

- [X] T049 Create `backend/app/services/broadcast.py`: `ConnectionManager` class with `defaultdict(set[WebSocket])` rooms; `connect()`, `disconnect()`, `broadcast_to_match()`; broadcast collects dead sockets before removal (never modify set during iteration) per research.md `→ 🔵 /task`
- [X] T050 Create `backend/app/api/ws.py`: `WS /ws/matches/{match_id}` endpoint; call `manager.connect()`; send `connected` message with latest prediction; start `keep_alive` coroutine (30s JSON ping); receive loop catching `WebSocketDisconnect`; call `manager.disconnect()` on disconnect per websocket contract `→ 🔵 /task`
- [X] T051 Update `backend/app/main.py` `lifespan()` context manager: `asyncio.create_task(run_polling_loop())` on startup; cancel task on shutdown; instantiate `ConnectionManager` singleton; load active model `→ 🔵 /task`
- [X] T052 Wire broadcast into `ingestion.py`: after `predict_ingame()` returns, call `manager.broadcast_to_match(match_id, {"type": "prediction_update", ...})` per websocket contract message format `→ 🔵 /task`
- [X] T053 Add `backend/app/api/admin.py`: `POST /api/v1/admin/events/simulate`; guard with `if settings.environment != 'development': raise 403`; insert fake `LiveEvent`; trigger prediction pipeline; return new prediction `→ 🔵 /task`

### Feed Status Broadcasting

- [X] T054 Add `feed_status` broadcast in `ingestion.py`: catch `httpx.RequestError` / rate limit from ESPN adapter; broadcast `{"type": "feed_status", "payload": {"available": false, "reason": "..."}}` to all rooms; re-broadcast `available: true` on recovery `→ 🔵 /task`

### React Frontend — US2 Components `[fe]`

- [X] T055 Create `frontend/src/store/predictions.ts`: Zustand store with `{ predictions: Record<matchId, Prediction>, updatePrediction, feedStatus: Record<matchId, boolean> }`; actions called by WebSocket hook `→ 🔵 /task` `[fe]`
- [X] T056 Create `frontend/src/hooks/useWebSocket.ts`: open `WebSocket` to `${VITE_WS_URL}/ws/matches/${matchId}`; handle `prediction_update`, `live_event`, `match_status_change`, `feed_status`, `ping` messages; respond to `ping` with `pong`; exponential backoff reconnect (1s → 2s → 4s → ... → 30s max); update Zustand store on each message `→ 🔴 /deep` `[fe]`
- [X] T057 [P] Create `frontend/src/components/LiveEventLog/LiveEventLog.tsx`: scrollable list of `LiveEvent` items with event-type icons (⚽ goal, 🟨 yellow, 🟥 red); newest at top; auto-scroll on new event; shows "No events yet" when empty `→ 🔵 /task` `[fe]`
- [X] T058 [P] Create `frontend/src/components/FeedStatusBanner/FeedStatusBanner.tsx`: shows yellow "Live data paused — last updated HH:MM" banner when `feedStatus[matchId] = false`; animates in/out `→ 🔵 /task` `[fe]`
- [X] T059 Create `frontend/src/pages/MatchDetail.tsx`: connects `useWebSocket(matchId)` on mount, disconnects on unmount; renders `ProbabilityBar` from Zustand store (updates animate on state change); renders `LiveEventLog`; renders `FactorsPanel`; renders `FeedStatusBanner`; renders probability history sparkline from `/predictions/{id}/history` `→ 🔵 /task` `[fe]`
- [X] T060 Update `frontend/src/components/MatchCard/MatchCard.tsx`: add click navigation to `/match/:id`; show current score overlay when status is `live`; read live prediction from Zustand store (overrides REST data when available) `→ 🔵 /task` `[fe]`

**Checkpoint**: With mock provider active and a match set to `live`, injecting a goal via `/admin/events/simulate` causes probability bars on the Dashboard and MatchDetail page to animate within 5 seconds. `FeedStatusBanner` appears when mock provider is stopped. User Story 2 testable independently.

---

## Phase 5: User Story 3 — Full Tournament Overview (Priority: P2)

**Goal**: All 64 matches visible on the Dashboard organized by stage with Upcoming/Live/Final badges. Completed matches show actual results and an AI accuracy indicator.

**Independent Test**: Open Dashboard → see all matches grouped by Group A through Group L, Round of 16, Quarterfinals, Semifinals, Final — each with correct status badge. A completed match shows actual score and "✓ AI correct" or "✗ AI wrong" indicator.

### Backend

- [X] T061 Update `GET /api/v1/matches` to include `accuracy_record` join when match status is `finished`: add `was_ai_correct` and `predicted_outcome` to `MatchListResponse` `→ 🔵 /task`
- [X] T062 Add stage ordering logic in `backend/app/api/matches.py`: return matches sorted by stage priority (Group A-L → R16 → QF → SF → Final) then by `scheduled_at` `→ 🟢 /quick`

### React Frontend — US3 Components `[fe]`

- [X] T063 Update `frontend/src/pages/Dashboard.tsx`: group matches by stage using stage priority order; render a collapsible `<StageSection>` per stage; show live match count badge per stage `→ 🔵 /task` `[fe]`
- [X] T064 [P] Create `frontend/src/components/MatchCard/AIResultBadge.tsx`: shows "✓ AI predicted correctly" (green) or "✗ AI missed this one" (red) on finished match cards; tooltip shows predicted vs actual outcome `→ 🟢 /quick` `[fe]`
- [X] T065 Update `frontend/src/components/MatchCard/MatchCard.tsx`: when `status === 'finished'` display actual score prominently instead of probabilities; show `AIResultBadge`; hide `FactorsPanel` `→ 🔵 /task` `[fe]`
- [X] T066 [P] Add model version tooltip to `MatchCard`: on hovering the confidence indicator, show "Predicted by model v{version}" per FR-014 `→ 🟢 /quick` `[fe]`
- [X] T067 Update `frontend/src/hooks/useMatches.ts`: handle `match_status_change` WebSocket messages from the broadcast service; update match status in local state without full refetch `→ 🔵 /task` `[fe]`

**Checkpoint**: Dashboard shows all 64 matches in stage groups; completed matches display actual results with AI accuracy badge; live matches pulse with LIVE indicator.

---

## Phase 6: User Story 4 — Prediction Accuracy Tracker (Priority: P2)

**Goal**: After each match ends, the dashboard accuracy panel updates showing cumulative correct predictions broken down by tournament stage.

**Independent Test**: After 5+ completed matches, accuracy panel shows correct count/total/percentage; stage breakdown is present; high-confidence wrong predictions appear as notable misses.

### Backend

- [X] T068 Create `backend/app/services/accuracy.py`: `record_match_result(match_id, actual_home, actual_away, db)` — determine `actual_outcome` from scoreline; fetch last pre-match prediction; compute `was_correct`; insert/upsert `AccuracyRecord`; call `broadcast_accuracy_update()` `→ 🔵 /task`
- [X] T069 Update `ingestion.py`: when ESPN scoreboard returns `STATUS_FULL_TIME` for a match currently stored as `live`: update `match.status = 'finished'`, store actual score, call `accuracy.record_match_result()` `→ 🔵 /task`
- [X] T070 Implement `GET /api/v1/accuracy` in `backend/app/api/accuracy.py`: aggregate `accuracy_records` grouped by stage; compute `notable_misses` (was_correct=False AND predicted_confidence > 0.7); return `AccuracySummaryResponse` per contract `→ 🔵 /task`

### React Frontend — US4 Components `[fe]`

- [X] T071 Create `frontend/src/components/AccuracyPanel/AccuracyPanel.tsx`: overall accuracy fraction + percentage; Recharts `BarChart` for per-stage accuracy; "Notable misses" list with team names and confidence shown; TanStack Query polling `/accuracy` every 60s `→ 🔵 /task` `[fe]`
- [X] T072 Add `AccuracyPanel` to `frontend/src/pages/Dashboard.tsx` as a sticky sidebar or bottom section `→ 🟢 /quick` `[fe]`
- [X] T073 Add accuracy broadcast in `broadcast.py`: `broadcast_all({"type": "accuracy_update", "payload": {...}})` after each match finishes; clients re-fetch `/accuracy` on receiving this message `→ 🔵 /task`

**Checkpoint**: After seeding a completed match and calling `record_match_result()`, accuracy panel updates within 2 seconds in the browser.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness, deployment, and end-to-end validation.

- [X] T074 [P] Add error boundaries to React app: `ErrorBoundary` wrapping each page; fallback UI shows "Something went wrong" without blank panels (constitution V) `→ 🔵 /task` `[fe]`
- [X] T075 [P] Add `backend/scripts/dev_set_match_live.py` helper: updates match status to `live`/`finished` in DB for local testing; used in quickstart.md step 6 `→ 🟢 /quick`
- [X] T076 Write contract tests in `backend/tests/contract/test_rest_contract.py`: assert every REST endpoint response shape matches `contracts/rest-api.md` JSON structure using `httpx.AsyncClient` + `pytest` `→ 🔵 /task` `[tdd]`
- [X] T077 Write WebSocket integration test in `backend/tests/integration/test_websocket.py`: connect WS client → inject mock event → assert `prediction_update` message received within 5s `→ 🔵 /task` `[tdd]`
- [X] T078 Configure Railway deployment: `railway.json` or Railway dashboard — set `DATABASE_URL`, `FOOTBALL_API_PROVIDER=espn`, `ENVIRONMENT=production`, `ALLOWED_ORIGINS`; run `alembic upgrade head` on first deploy `→ 🔵 /task`
- [X] T079 Configure Vercel deployment `[vd]`: set `VITE_API_URL` and `VITE_WS_URL` to Railway backend URL; verify `vercel.json` SPA fallback; test WebSocket connection from Vercel preview URL to Railway `→ 🔵 /task` `[vd]`
- [X] T080 End-to-end validation per `quickstart.md`: seed → generate pre-match predictions → set match live → simulate 3 events → verify all 7 success criteria (SC-001 to SC-007) `→ 🔵 /task` `[dbg]`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    └─→ Phase 2 (Foundational) ← BLOCKS all phases below
            ├─→ Phase 3 (US1 - Pre-Match Viewer) — MVP
            │       └─→ Phase 4 (US2 - Live Updates) — depends on US1 prediction engine
            ├─→ Phase 5 (US3 - Tournament Overview) — can start after Phase 2
            └─→ Phase 6 (US4 - Accuracy Tracker) — can start after Phase 4 (needs match finish logic)
Phase 7 (Polish) — starts after Phase 3 + 4 complete (US1 + US2 are P1)
```

### User Story Dependencies

| Story | Depends on | Can start after |
|-------|-----------|----------------|
| US1 (Pre-match viewer) | Foundational phase only | T007–T023 complete |
| US2 (Live updates) | US1 prediction engine (T029) | T029 complete |
| US3 (Tournament overview) | Foundational phase + US1 REST | T031 complete |
| US4 (Accuracy tracker) | US2 match finish detection (T069) | T069 complete |

### Within Each Phase — Parallelizable Groups

**Phase 2** — all [P] tasks (T010–T015) can be created simultaneously by different subagents.
**Phase 3** — T035–T040 (React components) all [P]; T024–T026 (ML offline) fully parallel with REST work.
**Phase 4** — T044–T046 (providers) all [P]; T057–T058 (React components) [P].
**Phase 5** — T063–T067: T064 and T066 are [P] with each other.

---

## Parallel Execution Examples

### Phase 2 — Models (launch simultaneously)

```
Task T010: Create backend/app/models/team.py
Task T011: Create backend/app/models/match.py
Task T012: Create backend/app/models/live_event.py
Task T013: Create backend/app/models/model_version.py
Task T014: Create backend/app/models/prediction.py
Task T015: Create backend/app/models/accuracy_record.py
```

### Phase 3 — React components (launch simultaneously after T035)

```
Task T038: Build ProbabilityBar.tsx
Task T039: Build FactorsPanel.tsx
Task T040: Build LiveBadge.tsx
Task T037: Build useMatches.ts hook
```

### Phase 4 — Provider adapters (launch simultaneously after T044)

```
Task T045: Build MockProvider
Task T046: Build ESPNAdapter
```

---

## Implementation Strategy

### MVP First (US1 only — pre-match predictions working)

1. Complete Phase 1 (T001–T006)
2. Complete Phase 2 (T007–T023)
3. Run `ml/train_prematch.py` + `ml/register_model.py` offline
4. Complete Phase 3 (T024–T043)
5. **Validate US1**: Dashboard shows all 64 matches with AI predictions, confidence, and factors
6. Deploy MVP to Vercel + Railway

### Incremental Delivery

1. **MVP** (US1): Pre-match predictions dashboard — deploy, validate SC-001 + SC-006
2. **+Live updates** (US2): WebSocket + ESP adapter — validate SC-002 + SC-003
3. **+Tournament view** (US3): Stage grouping + results — validate SC-005
4. **+Accuracy panel** (US4): Accuracy tracking — validate SC-004 + SC-007

---

## Task Count Summary

| Phase | Tasks | Model breakdown |
|-------|-------|----------------|
| Phase 1: Setup | T001–T006 (6) | 6× 🟢 Haiku |
| Phase 2: Foundational | T007–T023 (17) | 9× 🟢 Haiku, 8× 🔵 Sonnet |
| Phase 3: US1 Pre-Match | T024–T043 (20) | 5× 🟢 Haiku, 12× 🔵 Sonnet, 3× 🔴 Opus |
| Phase 4: US2 Live Updates | T044–T060 (17) | 0× 🟢 Haiku, 11× 🔵 Sonnet, 4× 🔴 Opus, 2× hybrid |
| Phase 5: US3 Tournament | T061–T067 (7) | 3× 🟢 Haiku, 4× 🔵 Sonnet |
| Phase 6: US4 Accuracy | T068–T073 (6) | 1× 🟢 Haiku, 5× 🔵 Sonnet |
| Phase 7: Polish | T074–T080 (7) | 1× 🟢 Haiku, 6× 🔵 Sonnet |
| **Total** | **80 tasks** | **25× 🟢 / 46× 🔵 / 7× 🔴 / 2× hybrid** |

**Opus tasks** (T025, T026, T029, T046, T047, T048, T056): These are the 7 tasks requiring deep reasoning — ML feature engineering, Poisson math, ESPN adapter deduplication, WebSocket reconnect logic.

---

## Notes

- `[P]` = can be worked on in parallel with other `[P]` tasks in the same phase (different files)
- `[US1/2/3/4]` = traceability to user story acceptance criteria in spec.md
- `[fe]`, `[vd]`, `[tdd]`, `[dbg]` = load the listed skill before starting the task
- 🔴 Opus tasks: use `/deep` for complex algorithmic work; the Poisson math (T048) is the hardest single task
- Commit after each phase checkpoint, not after every individual task
- Test the mock provider end-to-end (T077) before connecting the real ESPN API
