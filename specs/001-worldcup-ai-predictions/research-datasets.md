# Dataset Research: Improving Pre-Match Prediction Before WC 2026

**Date**: 2026-06-22
**Author**: research pass (deep)
**Goal**: identify free, no-auth datasets (GitHub/Kaggle) that close the *specific* gaps in the current model, deployable before the 2026 World Cup.

---

## 1. What the current model actually uses (and where it lies)

The trained `prematch_v1.0.0` model has **14 features** (`backend/ml/train_prematch.py`). Three groups of them are **fabricated proxies**, not real data:

| Feature group | Current source | Problem |
|---|---|---|
| `home/away_fifa_ranking`, `ranking_diff` | ELO-lite proxy from cumulative win rate (`team_strength` dict, lines 299–312) | **Not real FIFA ranking.** A crude recency-weighted win counter. Cold-start teams all get 0.5. |
| `home/away_xg_avg` | `goals_scored × 0.9` (lines 274–276) | **Fake xG.** Perfectly collinear with goal average — adds zero information. |
| H2H, form, goal avg | Real, computed from `results.csv` | Fine — *but only as good as the underlying results.csv*. We trained on **synthetic** data. |

Two features the data-model spec lists but the training code **never uses**: `is_neutral_venue` and `stage_weight`. The `neutral` column *exists* in the data but is dropped. **Every WC match is neutral**, so the model's learned home-advantage is systematically wrong for the actual tournament.

The **draw class has 0 recall** — partly class imbalance, partly because the proxy ranking can't express "two evenly-matched strong teams," which is exactly when draws happen.

---

## 2. Recommended datasets, ranked by value-per-effort

### Tier 1 — Do these before kickoff (free, no Kaggle login, direct CSV)

#### ① Real `results.csv` — martj42/international_results ⭐ #1 priority
- **Raw URL**: `https://raw.githubusercontent.com/martj42/international_results/master/results.csv` *(verified HTTP 200, 3.7 MB)*
- **Note**: repo is `international_results` (underscore). The `-football-results` URL in the training script comment is **wrong** — that's why the download 404'd.
- **Coverage**: 49,000+ men's full internationals, 1872 → 2026, updated continuously.
- **Schema**: `date, home_team, away_team, home_score, away_score, tournament, city, country, neutral`
- **Fixes**: replaces synthetic data → real form, real H2H, real goal averages. The single biggest accuracy win available. Drop-in: the script already reads this exact schema.
- **Bonus files in same repo** (verified 200):
  - `goalscorers.csv` — player + minute + penalty/own-goal → enables scorer-form features later
  - `shootouts.csv` — penalty shootout winners → correct knockout-stage labels (a "draw" that went to pens isn't a draw outcome in knockouts)

#### ② FIFA World Ranking — cnc8/fifa-world-ranking (GitHub, no auth)
- **Repo**: `https://github.com/cnc8/fifa-world-ranking` — files `fifa_ranking-YYYY-MM-DD.csv`
- **Kaggle mirror**: [cashncarry/fifaworldranking](https://www.kaggle.com/datasets/cashncarry/fifaworldranking) (1992–2024)
- **Schema**: `rank, country_full, country_abrv, total_points, previous_points, rank_change, confederation, rank_date`
- **Fixes**: replaces the fake ranking proxy. Join by `(team, nearest rank_date ≤ match_date)`. The script already has a `has_ranking` branch (line 216) that uses real `home_fifa_ranking`/`away_fifa_ranking` columns if present — **the code is already wired for this**, you just have to supply the column.

#### ③ International Elo ratings — better predictor than FIFA rank ⭐
- **Kaggle**: [saifalnimri/international-football-elo-ratings](https://www.kaggle.com/datasets/saifalnimri/international-football-elo-ratings) (1872 → 2025, from eloratings.net)
- **GitHub alt**: `ericsanmiguel/football_elo` (also publishes 2026 WC predictions)
- **Why Elo beats FIFA rank for prediction**: Elo is a *match-outcome* rating — designed to convert a rating gap directly into a win probability. FIFA points are a competition-reward formula, not a forecasting tool. Elo also moves on every match, so it captures form. Independent predictors using Elo report ~60% W/D/L accuracy.
- **Fixes**: the ranking proxy *and* helps the draw class (small Elo gap → genuine draw signal).

### Tier 2 — Real xG (higher effort, partial coverage)

#### ④ StatsBomb Open Data — real expected goals
- **Repo**: `https://github.com/statsbomb/open-data` (+ `statsbombpy` to stream into Python)
- **Coverage for internationals**: **WC 2022 (64 matches, events + 360) and WC 2018** — free. That's ~128 matches, *not* a full training set.
- **Use it as**: an **xG calibration source**, not a training column. Replace the `goals × 0.9` fake with a shot-quality xG only where StatsBomb covers it; fall back to a goals-based estimate elsewhere. Or train a lightweight xG model on these matches and apply it forward.
- **Trade-off**: real xG is the single most predictive football feature, but 128 matches can't feed the main model directly. Worth it only after Tier 1 is done.

### Tier 3 — Ready-made 2026 tournament metadata (for seeding, not training)

#### ⑤ FIFA World Cup Complete Dataset 1930–2026 — [kulkarniparth09](https://www.kaggle.com/datasets/kulkarniparth09/fifa-world-cup-complete-dataset-19302026)
- Has **2026 group assignments, FIFA rank, confederation, head coach, best-ever result**. Use to **seed the `teams` table** (`group_letter`, `fifa_ranking`) for the actual 48-team tournament — directly fills the data-model `teams` schema.
#### ⑥ piterfm/fifa-football-world-cup — WC match/squad data 1930–2026, good for fixture seeding.

---

## 3. Concrete integration plan (minimal diffs)

1. **Swap real data in** (5 min, biggest win):
   `curl -L -o backend/ml/data/raw/results.csv https://raw.githubusercontent.com/martj42/international_results/master/results.csv` → re-run `python -m ml.train_prematch`. No code change; expect test accuracy and draw recall to move immediately.
2. **Add real FIFA ranking or Elo** (~30 min): build a `(team, date) → rating` lookup, inject `home_fifa_ranking`/`away_fifa_ranking` columns into the DataFrame before `build_features`. The `has_ranking` path already consumes them.
3. **Use the `neutral` column** (~10 min): add `is_neutral_venue` as a 15th feature. Critical because WC = all neutral.
4. **Use `shootouts.csv` for knockout labels** (~15 min): correct the outcome label for matches decided on penalties.
5. **(Later) StatsBomb xG**: replace the fake `xg_avg`.

**Ordering rationale**: steps 1–3 are pure data-quality fixes with near-zero code risk and directly target the three fabricated/unused feature groups. xG (step 5) is highest-ceiling but lowest coverage, so it comes last.

---

## 4. Sources
- [martj42/international_results (GitHub)](https://github.com/martj42/international_results) · [Kaggle mirror](https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017)
- [cnc8/fifa-world-ranking (GitHub)](https://github.com/cnc8/fifa-world-ranking) · [cashncarry/fifaworldranking (Kaggle)](https://www.kaggle.com/datasets/cashncarry/fifaworldranking)
- [International Football Elo Ratings (Kaggle)](https://www.kaggle.com/datasets/saifalnimri/international-football-elo-ratings) · [ericsanmiguel/football_elo (GitHub)](https://github.com/ericsanmiguel/football_elo)
- [statsbomb/open-data (GitHub)](https://github.com/statsbomb/open-data) · [statsbombpy](https://github.com/statsbomb/statsbombpy)
- [FIFA World Cup Complete Dataset 1930–2026 (Kaggle)](https://www.kaggle.com/datasets/kulkarniparth09/fifa-world-cup-complete-dataset-19302026) · [piterfm/fifa-football-world-cup (Kaggle)](https://www.kaggle.com/datasets/piterfm/fifa-football-world-cup)
