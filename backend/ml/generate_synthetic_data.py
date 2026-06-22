"""
Generate synthetic international football results for model training.
Produces a CSV matching the Kaggle 'international-football-results' schema:
  date, home_team, away_team, home_score, away_score, tournament, city, country, neutral
Run from backend/:  python -m ml.generate_synthetic_data
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

TEAMS = {
    # FIFA ranking tier → list of teams
    1:  ["Brazil", "France", "Argentina", "Belgium", "England", "Portugal", "Spain", "Netherlands"],
    2:  ["Germany", "Italy", "Croatia", "Denmark", "Uruguay", "Switzerland", "USA", "Mexico"],
    3:  ["Morocco", "Senegal", "Japan", "South Korea", "Colombia", "Ecuador", "Poland", "Australia"],
    4:  ["Cameroon", "Ghana", "Tunisia", "Serbia", "Wales", "Canada", "Costa Rica", "Iran"],
    5:  ["Saudi Arabia", "Qatar", "Ecuador", "Panama", "Jamaica", "Honduras", "Syria", "Iraq"],
}

TEAM_LIST = [t for ts in TEAMS.values() for t in ts]
TIER = {t: tier for tier, ts in TEAMS.items() for t in ts}

TOURNAMENTS = (
    ["FIFA World Cup"] * 3
    + ["UEFA Euro"] * 2
    + ["CONMEBOL Copa America"] * 2
    + ["Africa Cup of Nations"] * 2
    + ["AFC Asian Cup"] * 2
    + ["CONCACAF Gold Cup"] * 1
    + ["World Cup qualification"] * 6
    + ["UEFA Nations League"] * 4
)


def _goal_lambda(tier: int) -> float:
    """Expected goals per match based on FIFA tier."""
    return max(0.5, 1.8 - (tier - 1) * 0.2)


def simulate_match(home: str, away: str) -> tuple[int, int]:
    ht, at = TIER[home], TIER[away]
    home_lam = _goal_lambda(ht) + 0.15 * (at - ht)  # home advantage + ranking diff
    away_lam = _goal_lambda(at) - 0.10 * (at - ht)
    home_lam = max(0.2, home_lam)
    away_lam = max(0.2, away_lam)
    return int(np.random.poisson(home_lam)), int(np.random.poisson(away_lam))


def generate(n_matches: int = 8000) -> pd.DataFrame:
    records = []
    start = pd.Timestamp("2000-01-01")
    end = pd.Timestamp("2025-06-01")
    dates = pd.date_range(start, end, freq="D")

    for _ in range(n_matches):
        home, away = random.sample(TEAM_LIST, 2)
        date = random.choice(dates)
        hs, as_ = simulate_match(home, away)
        records.append({
            "date": date.strftime("%Y-%m-%d"),
            "home_team": home,
            "away_team": away,
            "home_score": hs,
            "away_score": as_,
            "tournament": random.choice(TOURNAMENTS),
            "city": "N/A",
            "country": "N/A",
            "neutral": random.choice([True, False]),
        })

    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    return df


if __name__ == "__main__":
    out = Path("ml/data/raw/results.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df = generate(8000)
    df.to_csv(out, index=False)
    print(f"Generated {len(df):,} synthetic matches → {out}")
    print(df["tournament"].value_counts().head(8).to_string())
