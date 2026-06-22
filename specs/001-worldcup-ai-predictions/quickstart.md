# Developer Quickstart

**World Cup 2026 AI Prediction Dashboard**

---

## Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Python | 3.11+ | pyenv or system |
| Node.js | 20 LTS | nvm or system |
| PostgreSQL | 16+ | local or Docker |
| Docker + Compose | latest | docker.com |
| Railway CLI | latest | `npm i -g @railway/cli` |
| Vercel CLI | latest | `npm i -g vercel` |

---

## 1. Clone and configure environment

```bash
git clone <repo-url> worldcup-predictions
cd worldcup-predictions
cp .env.example .env
```

Edit `.env`:
```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/worldcup

# Football data provider (espn = free unofficial API, no key needed)
# Options: espn | mock | api_football (paid upgrade)
FOOTBALL_API_PROVIDER=espn

# Only needed if you switch to FOOTBALL_API_PROVIDER=api_football:
# FOOTBALL_API_KEY=your_rapidapi_key_here
# FOOTBALL_API_HOST=v3.football.api-sports.io

# Environment
ENVIRONMENT=development              # development | production
ALLOWED_ORIGINS=http://localhost:5173

# Frontend (set these in Vercel dashboard for production)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## 2. Start everything with Docker Compose (recommended for local dev)

```bash
docker compose up --build
```

Services started:
- `http://localhost:8000` — FastAPI backend (auto-reload)
- `http://localhost:5173` — React frontend (Vite HMR)
- `localhost:5432` — PostgreSQL 16

First run takes ~2 minutes to build images. Subsequent starts: ~10 seconds.

---

## 3. Seed the database

```bash
# In a new terminal (or exec into the backend container)
docker compose exec backend python scripts/seed_teams.py
docker compose exec backend python scripts/seed_matches.py
```

This populates:
- 48 teams with current FIFA rankings and form
- All 64 World Cup 2026 fixtures

---

## 4. Train the ML models (one-time, run locally)

```bash
cd backend

# Install ML training dependencies
pip install -r requirements-ml.txt

# Download training data (openfootball + Kaggle international results)
python ml/download_data.py

# Train pre-match XGBoost model + calibrator + bootstrap CI
python ml/train_prematch.py
# Output: ml/artifacts/prematch_v1.0.0.joblib

# Evaluate on held-out test set (prints accuracy, calibration plot)
python ml/evaluate.py ml/artifacts/prematch_v1.0.0.joblib

# Register model in the database
python ml/register_model.py ml/artifacts/prematch_v1.0.0.joblib --activate
```

Training takes ~5 minutes. The model artifact is ~2 MB and is committed to git.

---

## 5. Generate pre-match predictions

With the database seeded and model registered:

```bash
docker compose exec backend python scripts/generate_prematch_predictions.py
```

This generates and stores a pre-match prediction for every upcoming match.
Open `http://localhost:5173` — you should see match cards with predictions.

---

## 6. Test the live update pipeline (without a real API key)

Set `FOOTBALL_API_PROVIDER=mock` in `.env` and restart the backend. The mock
provider simulates live events for any match marked as `live`:

```bash
# Mark a match as live for testing
docker compose exec backend python scripts/dev_set_match_live.py --match-id 1

# Inject a fake goal event
curl -X POST http://localhost:8000/api/v1/admin/events/simulate \
  -H "Content-Type: application/json" \
  -d '{"match_id": 1, "event_type": "goal", "team_id": 5, "player_name": "Test", "minute": 34, "home_score_after": 1, "away_score_after": 0}'
```

Open the match detail page — the probability bars should animate within ~2 seconds.

---

## Production Deployment

### Backend → Railway

```bash
railway login
railway link          # link to your Railway project
railway up            # deploy backend
```

Set environment variables in Railway dashboard:
- `DATABASE_URL` — Railway PostgreSQL connection string (auto-populated if using Railway Postgres)
- `FOOTBALL_API_PROVIDER` — `espn` (free, no key needed)
- `ENVIRONMENT` — `production`
- `ALLOWED_ORIGINS` — `https://your-app.vercel.app`

Run migrations and seed on Railway:
```bash
railway run alembic upgrade head
railway run python scripts/seed_teams.py
railway run python scripts/seed_matches.py
railway run python scripts/generate_prematch_predictions.py
```

### Frontend → Vercel

```bash
cd frontend
vercel            # follow prompts, link to your Vercel project
```

Set environment variables in Vercel dashboard:
- `VITE_API_URL` — `https://your-backend.railway.app`
- `VITE_WS_URL` — `wss://your-backend.railway.app`

---

## Running Tests

```bash
# Backend unit + integration tests
cd backend
pytest tests/ -v

# Contract tests (validates REST responses against contract spec)
pytest tests/contract/ -v

# Frontend
cd frontend
npm run test
```

---

## Key File Locations

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app + lifespan (scheduler startup) |
| `backend/app/services/ingestion.py` | Football API polling loop |
| `backend/app/services/prediction_engine.py` | XGBoost inference + Poisson update |
| `backend/app/services/broadcast.py` | WebSocket ConnectionManager |
| `backend/app/api/ws.py` | WebSocket endpoint handler |
| `backend/ml/train_prematch.py` | Pre-match model training script |
| `frontend/src/hooks/useWebSocket.ts` | WS connection + reconnect logic |
| `frontend/src/store/predictions.ts` | Zustand store for live predictions |
| `specs/001-worldcup-ai-predictions/` | All spec-kit design documents |

---

## Troubleshooting

**WebSocket connection fails in production**:
Check that `ALLOWED_ORIGINS` on Railway matches your exact Vercel URL (including `https://`).
Starlette wildcard `*.vercel.app` requires Starlette ≥ 0.28 — check `pip show starlette`.

**Predictions not updating during live match**:
1. Check Railway logs: `railway logs` — look for "Fetching ESPN scoreboard" every 15s
2. Test ESPN endpoint manually: `curl "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"`
3. Verify the match `external_id` in the DB matches the ESPN `gameId` returned by the scoreboard
4. If ESPN API is down, set `FOOTBALL_API_PROVIDER=mock` temporarily to keep the pipeline running

**Database migration errors**:
```bash
railway run alembic downgrade base
railway run alembic upgrade head
```

**Model not loading on startup**:
Check `backend/ml/artifacts/` — the `.joblib` file must be committed to git or accessible
at the path registered in `model_versions.artifact_path`.
