"""
Feature engineering module for the World Cup 2026 AI prediction model.

Computes the 14 pre-match features consumed by the XGBoost classifier from:
  - Historical international results (Kaggle CSV)
  - FIFA rankings (caller-supplied)
  - StatsBomb xG aggregates (team_name -> avg xG per match)

All lookback windows:
  - Form: last 5 matches per team (home OR away)
  - Goals scored / conceded: last 10 matches per team (home OR away)
  - H2H: last 10 matches between the two specific teams

H2H fallback: if fewer than 5 H2H matches exist the three rate features are
filled with the neutral prior (0.333…) rather than a small-sample estimate.
"""

from __future__ import annotations

import logging
from typing import cast

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

FEATURE_COLUMNS: list[str] = [
    "home_fifa_ranking",        # int  – lower is better
    "away_fifa_ranking",        # int
    "ranking_diff",             # int  – home - away (negative = home is stronger)
    "home_form_points",         # float – sum of pts from last 5 matches (W=3, D=1, L=0)
    "away_form_points",         # float
    "form_diff",                # float – home_form_points - away_form_points
    "home_avg_goals_scored",    # float – avg goals scored last 10 matches
    "away_avg_goals_scored",    # float
    "home_avg_goals_conceded",  # float – avg goals conceded last 10 matches
    "away_avg_goals_conceded",  # float
    "h2h_home_win_rate",        # float 0-1 – home-team wins in last 10 H2H
    "h2h_draw_rate",            # float 0-1
    "home_xg_avg",              # float – avg xG scored per match (StatsBomb)
    "away_xg_avg",              # float
]

# Minimum H2H matches required to trust the observed win rates.
_MIN_H2H_MATCHES: int = 5

# Neutral prior used when H2H sample is too small.
_NEUTRAL_WIN_RATE: float = 1 / 3
_NEUTRAL_DRAW_RATE: float = 1 / 3

# ---------------------------------------------------------------------------
# FACTOR_LABELS – plain-English templates for SHAP narration
# ---------------------------------------------------------------------------

FACTOR_LABELS: dict[str, str] = {
    "ranking_diff": (
        "{home} is ranked {diff} places {direction} {away}"
    ),
    "form_diff": (
        "{home} has {direction} recent form ({pts} pts vs {opp_pts} pts in last 5)"
    ),
    "h2h_home_win_rate": (
        "{home} has won {pct}% of recent head-to-head matches"
    ),
    "home_avg_goals_scored": (
        "{home} averages {goals} goals per game recently"
    ),
    "away_avg_goals_scored": (
        "{away} averages {goals} goals per game recently"
    ),
    "home_avg_goals_conceded": (
        "{home} concedes only {goals} goals per game on average"
    ),
    "home_xg_avg": (
        "{home} creates {xg} expected goals per match on average"
    ),
    "away_xg_avg": (
        "{away} creates {xg} expected goals per match on average"
    ),
}


def format_factor_label(
    feature: str,
    home_name: str,
    away_name: str,
    value: float,
) -> str:
    """Convert a SHAP feature name and its raw value to plain English.

    Parameters
    ----------
    feature:
        One of the keys in ``FACTOR_LABELS``.
    home_name:
        Display name of the home team.
    away_name:
        Display name of the away team.
    value:
        The raw feature value (used to compute directional qualifiers, etc.).

    Returns
    -------
    str
        A human-readable sentence.  Falls back to a generic description if the
        feature is not in ``FACTOR_LABELS``.
    """
    template = FACTOR_LABELS.get(feature)
    if template is None:
        return f"{feature} = {value:.3g}"

    if feature == "ranking_diff":
        # ranking_diff = home - away; negative means home is ranked higher (better)
        diff = abs(int(round(value)))
        direction = "higher" if value < 0 else "lower"
        return template.format(home=home_name, diff=diff, direction=direction, away=away_name)

    if feature == "form_diff":
        direction = "better" if value > 0 else "worse"
        # We can only report home points here; caller must pass both if needed.
        pts = f"{value:+.0f}"
        return template.format(
            home=home_name,
            direction=direction,
            pts=pts,
            opp_pts="?",
        )

    if feature == "h2h_home_win_rate":
        pct = int(round(value * 100))
        return template.format(home=home_name, pct=pct)

    if feature == "home_avg_goals_scored":
        return template.format(home=home_name, goals=f"{value:.2f}")

    if feature == "away_avg_goals_scored":
        return template.format(away=away_name, goals=f"{value:.2f}")

    if feature == "home_avg_goals_conceded":
        return template.format(home=home_name, goals=f"{value:.2f}")

    if feature == "home_xg_avg":
        return template.format(home=home_name, xg=f"{value:.2f}")

    if feature == "away_xg_avg":
        return template.format(away=away_name, xg=f"{value:.2f}")

    # Fallback (should not reach here if FACTOR_LABELS is consistent with code)
    return template


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _team_matches(df: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return all rows in which *team* participated (home or away)."""
    mask = (df["home_team"] == team) | (df["away_team"] == team)
    return df.loc[mask].copy()


def _compute_form_points(df: pd.DataFrame, team: str, n: int = 5) -> float:
    """Sum of W/D/L points for *team* across the last *n* matches.

    Points:
        Win  → 3
        Draw → 1
        Loss → 0

    The function resolves each match from the perspective of *team*,
    regardless of whether the team played at home or away.

    Parameters
    ----------
    df:
        Pre-filtered DataFrame containing only this team's matches,
        sorted ascending by date.  The caller is responsible for slicing
        and sorting.
    team:
        The team name to compute points for.
    n:
        Number of most-recent matches to consider.

    Returns
    -------
    float
        Sum of points (0 – 3*n).
    """
    recent = df.sort_values("date", ascending=True).tail(n)
    if recent.empty:
        return 0.0

    points_total: float = 0.0
    for _, row in recent.iterrows():
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        is_home = row["home_team"] == team

        if is_home:
            if home_score > away_score:
                points_total += 3.0
            elif home_score == away_score:
                points_total += 1.0
            # else: loss → 0
        else:
            if away_score > home_score:
                points_total += 3.0
            elif away_score == home_score:
                points_total += 1.0
            # else: loss → 0

    return points_total


def _compute_avg_goals(
    df: pd.DataFrame, team: str, n: int = 10
) -> tuple[float, float]:
    """Average goals scored and conceded for *team* across the last *n* matches.

    Parameters
    ----------
    df:
        Pre-filtered DataFrame containing only this team's matches,
        sorted ascending by date.
    team:
        The team name.
    n:
        Number of most-recent matches to consider.

    Returns
    -------
    tuple[float, float]
        ``(avg_scored, avg_conceded)`` – both 0.0 if no matches found.
    """
    recent = df.sort_values("date", ascending=True).tail(n)
    if recent.empty:
        return 0.0, 0.0

    scored_list: list[int] = []
    conceded_list: list[int] = []

    for _, row in recent.iterrows():
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        if row["home_team"] == team:
            scored_list.append(home_score)
            conceded_list.append(away_score)
        else:
            scored_list.append(away_score)
            conceded_list.append(home_score)

    avg_scored = float(np.mean(scored_list))
    avg_conceded = float(np.mean(conceded_list))
    return avg_scored, avg_conceded


def _compute_h2h_rates(
    home_team: str,
    away_team: str,
    historical_results: pd.DataFrame,
    n: int = 10,
) -> tuple[float, float]:
    """Compute H2H win rate (home-team perspective) and draw rate.

    Uses the last *n* matches between these two specific teams, irrespective
    of which was home/away at the time.

    Falls back to neutral priors (0.333 each) when fewer than
    ``_MIN_H2H_MATCHES`` encounters are found.

    Parameters
    ----------
    home_team:
        The team that is the *current* home side.
    away_team:
        The team that is the *current* away side.
    historical_results:
        Full results DataFrame with columns
        ``date, home_team, away_team, home_score, away_score``.
    n:
        Maximum number of H2H matches to consider.

    Returns
    -------
    tuple[float, float]
        ``(home_win_rate, draw_rate)``.
    """
    mask = (
        (
            (historical_results["home_team"] == home_team)
            & (historical_results["away_team"] == away_team)
        )
        | (
            (historical_results["home_team"] == away_team)
            & (historical_results["away_team"] == home_team)
        )
    )
    h2h = (
        historical_results.loc[mask]
        .sort_values("date", ascending=True)
        .tail(n)
    )

    n_matches = len(h2h)
    if n_matches < _MIN_H2H_MATCHES:
        logger.debug(
            "Only %d H2H matches found for %s vs %s (min=%d); using neutral prior.",
            n_matches,
            home_team,
            away_team,
            _MIN_H2H_MATCHES,
        )
        return _NEUTRAL_WIN_RATE, _NEUTRAL_DRAW_RATE

    home_wins = 0
    draws = 0
    for _, row in h2h.iterrows():
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        actual_home = row["home_team"]
        actual_away = row["away_team"]

        if home_score == away_score:
            draws += 1
        elif actual_home == home_team and home_score > away_score:
            home_wins += 1
        elif actual_away == home_team and away_score > home_score:
            home_wins += 1

    home_win_rate = home_wins / n_matches
    draw_rate = draws / n_matches
    return home_win_rate, draw_rate


def _default_xg(statsbomb_xg: dict[str, float]) -> float:
    """Return the mean xG across all teams present in *statsbomb_xg*.

    Falls back to a league-average constant (1.35) if the dict is empty.
    This constant is approximately the historical mean xG per match in
    major international tournaments.
    """
    if not statsbomb_xg:
        return 1.35
    return float(np.mean(list(statsbomb_xg.values())))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_prematch_features(
    home_team_name: str,
    away_team_name: str,
    home_fifa_ranking: int,
    away_fifa_ranking: int,
    historical_results: pd.DataFrame,
    statsbomb_xg: dict[str, float],
) -> dict[str, float]:
    """Build the 14 pre-match feature dict for one fixture.

    Parameters
    ----------
    home_team_name:
        Name of the home team, matching values in ``historical_results``.
    away_team_name:
        Name of the away team.
    home_fifa_ranking:
        Current FIFA ranking of the home team (integer; 1 = best).
    away_fifa_ranking:
        Current FIFA ranking of the away team.
    historical_results:
        DataFrame with columns:
        ``date, home_team, away_team, home_score, away_score, tournament``.
        ``date`` must be parseable by ``pd.to_datetime``.
    statsbomb_xg:
        Mapping from team name to average xG scored per match, sourced from
        StatsBomb open data.  Teams absent from this dict receive a default
        equal to the mean across all teams present.

    Returns
    -------
    dict[str, float]
        Keys are exactly ``FEATURE_COLUMNS`` (in the same order).  All values
        are Python ``float`` (or ``int`` for the ranking features, but typed
        as ``float`` for uniform downstream handling).

    Raises
    ------
    ValueError
        If ``historical_results`` is missing required columns.
    """
    required_cols = {"date", "home_team", "away_team", "home_score", "away_score"}
    missing = required_cols - set(historical_results.columns)
    if missing:
        raise ValueError(
            f"historical_results is missing required columns: {missing}"
        )

    # Ensure date column is datetime for reliable sorting.
    df = historical_results.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # --- Form (last 5 matches) ---
    home_matches = _team_matches(df, home_team_name)
    away_matches = _team_matches(df, away_team_name)

    home_form = _compute_form_points(home_matches, home_team_name, n=5)
    away_form = _compute_form_points(away_matches, away_team_name, n=5)

    # --- Average goals (last 10 matches) ---
    home_avg_scored, home_avg_conceded = _compute_avg_goals(
        home_matches, home_team_name, n=10
    )
    away_avg_scored, away_avg_conceded = _compute_avg_goals(
        away_matches, away_team_name, n=10
    )

    # --- H2H rates ---
    h2h_home_win_rate, h2h_draw_rate = _compute_h2h_rates(
        home_team_name, away_team_name, df, n=10
    )

    # --- xG (StatsBomb) ---
    default_xg = _default_xg(statsbomb_xg)
    home_xg_avg = statsbomb_xg.get(home_team_name, default_xg)
    away_xg_avg = statsbomb_xg.get(away_team_name, default_xg)

    # --- Assemble feature dict (order mirrors FEATURE_COLUMNS) ---
    features: dict[str, float] = {
        "home_fifa_ranking": float(home_fifa_ranking),
        "away_fifa_ranking": float(away_fifa_ranking),
        "ranking_diff": float(home_fifa_ranking - away_fifa_ranking),
        "home_form_points": home_form,
        "away_form_points": away_form,
        "form_diff": home_form - away_form,
        "home_avg_goals_scored": home_avg_scored,
        "away_avg_goals_scored": away_avg_scored,
        "home_avg_goals_conceded": home_avg_conceded,
        "away_avg_goals_conceded": away_avg_conceded,
        "h2h_home_win_rate": h2h_home_win_rate,
        "h2h_draw_rate": h2h_draw_rate,
        "home_xg_avg": home_xg_avg,
        "away_xg_avg": away_xg_avg,
    }

    # Sanity-check: all keys accounted for (catches typos during development).
    assert set(features.keys()) == set(FEATURE_COLUMNS), (
        f"Feature mismatch: got {set(features.keys())} expected {set(FEATURE_COLUMNS)}"
    )

    return features
