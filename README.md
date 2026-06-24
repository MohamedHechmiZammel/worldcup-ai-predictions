# World Cup 2026 AI Prediction Dashboard

A real-time AI prediction dashboard for the 2026 FIFA World Cup. Every match gets win/draw/loss probabilities powered by an XGBoost model trained on Elo ratings, head-to-head history, and FIFA rankings — updated live via WebSocket as match events arrive.

**Live demo**: [worldcup-dashboard-zeta.vercel.app](https://worldcup-dashboard-zeta.vercel.app)

---

## Features

- **AI predictions** — Win/Draw/Loss probabilities + expected goals (xG) with SHAP-derived top-3 factors per match
- **Live updates** — WebSocket connection pushes Bayesian-updated predictions within seconds of a goal, red card, or half-time
- **Group standings** — Real-time standings proxied from ESPN (60 s cache) with a toggle to AI-projected final standings
- **Prediction history** — Recharts timeline showing how AI confidence evolved across prediction revisions
- **Accuracy tracking** — Post-match accuracy panel comparing AI prediction vs. actual outcome
- **AI learning** — After each result, Elo ratings are updated and remaining-match predictions are re-run automatically

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript, Vite, Zustand, TanStack Query, Recharts, Tailwind CSS |
| Backend | FastAPI (Python 3.11), SQLAlchemy async, Alembic, Uvicorn |
| ML | XGBoost, SHAP, scikit-learn (62 % validation accuracy) |
| Database | PostgreSQL (Neon serverless in production) |
| Data | ESPN public API (live scores, standings, match events) |
| Hosting | Render (backend Docker) + Vercel (frontend) |

---

## Project Structure

```
World_cup/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI routers
│   │   │   ├── matches.py   # match CRUD + PATCH results
│   │   │   ├── predictions.py
│   │   │   ├── standings.py # ESPN proxy (60 s cache)
│   │   │   ├── accuracy.py
│   │   │   ├── admin.py     # sync endpoints (auth-gated)
│   │   │   └── websocket.py # live prediction WS
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── ml/              # XGBoost training + SHAP inference
│   │   └── main.py
│   ├── alembic/             # DB migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # Dashboard, MatchDetail
│   │   ├── components/      # MatchCard, ProbabilityBar, GroupStandings, …
│   │   ├── hooks/           # useMatch, useStandings, useWebSocket
│   │   ├── store/           # Zustand predictions store
│   │   └── services/api.ts  # typed API client
│   └── package.json
├── docker-compose.yml        # full local stack
├── render.yaml               # Render deploy config
└── vercel.json               # Vercel deploy config
```

---

## Local Development

### Prerequisites

- Docker + Docker Compose
- Node.js 20+

### Run the full stack

```bash
git clone https://github.com/MohamedHechmiZammel/worldcup-ai-predictions.git
cd World_cup
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Run services individually

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
echo "VITE_WS_URL=ws://localhost:8000" >> .env.local
npm run dev
```

---

## Environment Variables

### Backend (`.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://…`) |
| `FOOTBALL_API_PROVIDER` | `espn` for production, `mock` for local dev |
| `ENVIRONMENT` | `production` or `development` |
| `ALLOWED_ORIGINS` | CORS origin (e.g. `https://worldcup-dashboard-zeta.vercel.app`) |
| `ADMIN_KEY` | Secret key for admin endpoints (`X-Admin-Key` header) |

### Frontend (`.env.local`)

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL |
| `VITE_WS_URL` | WebSocket base URL (`ws://` or `wss://`) |

---

## API Overview

```
GET  /api/v1/matches              all matches (filterable by group/status)
GET  /api/v1/matches/{id}         single match + prediction + accuracy
GET  /api/v1/predictions/{id}/history  prediction revision log
GET  /api/v1/standings/           live ESPN standings (all groups)
GET  /api/v1/standings/{group}    single group standings
WS   /api/v1/ws/{match_id}        live prediction stream

POST /api/v1/admin/sync-espn      sync ESPN results → DB (requires X-Admin-Key)
PATCH /api/v1/admin/matches/{id}  update match score + trigger re-prediction
GET  /api/v1/accuracy/summary     overall model accuracy stats
```

---

## ML Model

The prediction model is an XGBoost classifier trained on:

- **Elo ratings** — pre-match ratings for both teams, difference, and magnitude
- **FIFA ranking** — points and rank delta
- **Head-to-head record** — last 10 meetings, win rate, goals scored/conceded
- **Recent form** — last 5 matches points-per-game, goal difference
- **Neutral venue** — flag (World Cup group stage is always neutral)

After each finished match, Elo ratings update (K=32 base, adjusted for goal difference) and all remaining unplayed matches are re-predicted using the updated ratings.

SHAP values identify the top 3 factors per prediction for display in the UI.

---

## Deployment

The project ships as two separate services:

| Service | Platform | Config |
|---|---|---|
| Backend (Docker) | [Render](https://render.com) | `render.yaml` |
| Frontend (Vite SPA) | [Vercel](https://vercel.com) | `vercel.json` |
| Database | [Neon](https://neon.tech) | serverless Postgres |

Set `ALLOWED_ORIGINS` on Render to your Vercel URL, and `VITE_API_URL` / `VITE_WS_URL` on Vercel to your Render URL.

---

## License

MIT
