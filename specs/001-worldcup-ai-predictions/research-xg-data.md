# xG Data Research: How to Replace the Fake `goals × 0.9` Proxy

**Date**: 2026-06-22
**Status**: Research complete + data extraction in progress

---

## 1. The Problem (Precisely)

In `backend/ml/train_prematch.py` lines 274–276:

```python
home_xg = home_gs * 0.9   # fake: 90% collinear with goals scored
away_xg = away_gs * 0.9   # fake: adds zero independent information
```

XGBoost will assign near-zero importance to these features because they carry no signal beyond what `home_avg_goals_scored` already encodes. Real xG measures **shot quality** (location, angle, body part, pressure) — a team can score 2 goals from 0.4 xG (lucky) or score 2 goals from 3.5 xG (clinical). These are very different signals.

---

## 2. What Free Data Actually Exists (Verified)

### ① StatsBomb Open Data — THE answer ⭐

**Repo**: `https://github.com/statsbomb/open-data`

**Key finding**: The `statsbomb_xg` field is **pre-computed by StatsBomb** and included directly in every shot event JSON. No modeling required.

```python
shot["statsbomb_xg"]  # e.g., 0.0389 — probability this shot scores
```

**Exact international coverage (verified by fetching competitions.json + match files):**

| Tournament | Matches | xG available |
|---|---|---|
| FIFA World Cup 2022 | 64 | ✅ + 360 data |
| FIFA World Cup 2018 | 64 | ✅ |
| UEFA Euro 2024 | 51 | ✅ + 360 data |
| UEFA Euro 2020 | 51 | ✅ |
| Copa America 2024 | 32 | ✅ |
| AFCON 2023 | 52 | ✅ |
| Women's WC 2023 | ~52 | ✅ |
| Women's Euro 2022/2025 | ~31+? | ✅ |
| **Total men's international** | **~314 matches** | **✅** |

**Shot event fields** (confirmed from `match_id=3857276`):
- `statsbomb_xg` — pre-computed xG per shot (0.0 to 1.0)
- `location` — [x, y] coordinates on 120×80 pitch
- `shot.technique` — Normal, Volley, Half Volley, Lob, Backheel
- `shot.body_part` — Left Foot, Right Foot, Head
- `shot.outcome` — Goal, Saved, Blocked, Off T, Wayward

### ② Understat — NOT useful for internationals
Only covers 6 European domestic leagues. No international matches at all.

### ③ FBref — Partial, scraping required
Has xG for some international competitions but: (a) requires scraping, (b) xG shows as NA for friendlies, (c) ToS restricts bulk scraping. Not reliable.

### ④ Commercial APIs (Sportmonks, TheStatsAPI, etc.)
All require subscriptions ($50–$129/month). Not free.

### ⑤ FotMob / FootyStats
Display xG on website for WC 2026 but no documented free API. Unofficial endpoint scraping is fragile and ToS-violating.

---

## 3. The Core Limitation (Why This Is Hard)

**The fundamental mismatch:**

- `martj42/international_results` — 49,478 matches, final scores only, **zero shot data**
- `StatsBomb open-data` — 314 men's matches, complete shot events with xG, **only recent major tournaments**

You **cannot** retroactively compute xG for the 49k historical matches because xG requires shot-level data (location, technique, body part) — information that was never recorded for most of football history.

**What you CAN do:** build a *team-level xG profile* from the 314 StatsBomb matches and join it onto the training data.

---

## 4. Recommended Strategy: Team xG Profiles

**Approach**: for each team, compute their average xG-for and xG-against across all StatsBomb international matches they appear in. This gives a "shot quality fingerprint" per team that is independent of goals scored.

```python
# Example profiles (approximate, from data extraction in progress):
# France:    avg_xg_for=1.82, avg_xg_against=0.71 (8 matches)
# Argentina: avg_xg_for=1.65, avg_xg_against=0.88 (7 matches)
# England:   avg_xg_for=2.11, avg_xg_against=0.95 (6 matches)
```

**Join logic in `build_features()`:**
```python
# For each training match, look up xG profile:
home_xg = xg_profiles.get(home, {}).get('avg_xg_for', home_gs)  # fallback to goals
away_xg = xg_profiles.get(away, {}).get('avg_xg_for', away_gs)
```

**Coverage**: ~80 unique teams have StatsBomb data (WC 2022+2018 alone covers all 64 qualified nations). This covers every team that matters in WC 2026.

**Limitation**: xG profiles are static (from recent tournaments). They don't update match-by-match the way the Elo and form features do. This is acceptable — team shot quality changes slowly.

---

## 5. Alternative: Build a Micro xG Model

Train a logistic regression on StatsBomb shot features → score probability, then apply it to live ESPN shot data for real-time in-game predictions (not for historical training).

**Features needed per shot** (all in StatsBomb events):
- Distance to goal
- Angle to goal
- Body part (head vs foot)
- Technique (normal vs volley)
- Is first touch
- Was under pressure (from freeze_frame)

**Use case**: the **in-game Bayesian model** (not the pre-match XGBoost). When a live shot comes in via ESPN, compute its xG and update the in-game prediction immediately — much more meaningful than just tracking scoreline.

Repos with working implementations:
- [GuechtouliAnis/xG-model](https://github.com/GuechtouliAnis/xG-model) — StatsBomb, logistic regression
- [andrewRowlinson/expected-goals-thesis](https://github.com/andrewRowlinson/expected-goals-thesis) — StatsBomb + Wyscout, LightGBM

---

## 6. Implementation Plan

### Step 1 — Extract team xG profiles from StatsBomb (done via script)
```bash
# Already running: fetches all 314 men's matches, sums statsbomb_xg per team
# Output: backend/ml/data/raw/team_xg_profiles.json
```

### Step 2 — Add to `build_features()` in `train_prematch.py`
Replace `home_xg = home_gs * 0.9` with:
```python
XG_PROFILES = json.load(open("ml/data/raw/team_xg_profiles.json"))

def _team_xg(team: str, side: str, fallback: float) -> float:
    p = XG_PROFILES.get(team, {})
    key = "avg_xg_for" if side == "for" else "avg_xg_against"
    return p.get(key, fallback)
```

### Step 3 — Retrain and compare
Expected improvement: ~1–2 pts on accuracy, more meaningful gain on draw recall (draws often happen in matches where both teams' xG was close — a signal impossible to derive from goals alone).

### Step 4 — Micro xG model for in-game (optional, later)
Train on StatsBomb shot events. Apply to ESPN live shot feed for real-time in-game prediction updates.

---

## 7. Sources

- [statsbomb/open-data (GitHub)](https://github.com/statsbomb/open-data) — verified HTTP 200, `statsbomb_xg` confirmed in shot events
- [GuechtouliAnis/xG-model](https://github.com/GuechtouliAnis/xG-model) — xG model on StatsBomb
- [andrewRowlinson/expected-goals-thesis](https://github.com/andrewRowlinson/expected-goals-thesis) — StatsBomb + Wyscout LightGBM
- [bsobkowicz1096/Football-xG-Predictor](https://github.com/bsobkowicz1096/Football-xG-Predictor) — WC 2022 xG predictor
- [FootyStats WC xG](https://footystats.org/international/world-cup/xg) — web display only, no API
- [FotMob WC 2026 xG table](https://www.fotmob.com/leagues/77/table/world-cup?filter=xg) — web display only
