"""
Pre-match XGBoost model training script.

Run from the backend/ directory:
    python -m ml.train_prematch

Data source: backend/ml/data/raw/results.csv
  (Kaggle international football results dataset)

Output: backend/ml/artifacts/prematch_v1.0.0.joblib
"""

from __future__ import annotations

import datetime
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEATURE_COLUMNS = [
    "home_elo",
    "away_elo",
    "elo_diff",
    "home_form_points",
    "away_form_points",
    "form_diff",
    "home_avg_goals_scored",
    "away_avg_goals_scored",
    "home_avg_goals_conceded",
    "away_avg_goals_conceded",
    "h2h_home_win_rate",
    "h2h_draw_rate",
    "home_xg_avg",
    "away_xg_avg",
    "is_neutral_venue",
]

# Elo constants
ELO_INITIAL = 1500.0
ELO_K = 20.0          # K-factor for standard internationals
ELO_K_WC = 30.0       # Higher K for World Cup / major tournaments
ELO_HOME_ADV = 100.0  # Elo home-field advantage (0 when neutral=True)

LABEL_MAP = {0: "home_win", 1: "draw", 2: "away_win"}

# Paths (relative to backend/ working directory)
DATA_PATH = Path("ml/data/raw/results.csv")
ARTIFACTS_DIR = Path("ml/artifacts")
MODEL_OUTPUT = ARTIFACTS_DIR / "prematch_v1.0.0.joblib"

# Chronological split boundaries
TRAIN_END = "2020-01-01"
VAL_END = "2022-01-01"

# Bootstrap settings
N_BOOTSTRAP = 200

# Minimum draw samples threshold
MIN_DRAW_SAMPLES = 500

# Form window: last N matches to compute form points
FORM_WINDOW = 5

# H2H window: last N head-to-head matches
H2H_WINDOW = 10

# Goal average window: last N matches
GOAL_WINDOW = 10


# ---------------------------------------------------------------------------
# Helper: compute label
# ---------------------------------------------------------------------------


def encode_outcome(home_score: int, away_score: int) -> int:
    """Encode match outcome as 0=home_win, 1=draw, 2=away_win."""
    if home_score > away_score:
        return 0
    if home_score == away_score:
        return 1
    return 2


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------


def _form_points(team: str, before_date: pd.Timestamp, hist: pd.DataFrame, n: int) -> float:
    """
    Return total points earned by *team* in its last *n* matches before *before_date*.

    Points: win=3, draw=1, loss=0.
    Considers matches where team played either as home or away.
    Returns NaN if fewer than 2 matches found (not enough history).
    """
    mask = (
        ((hist["home_team"] == team) | (hist["away_team"] == team))
        & (hist["date"] < before_date)
    )
    recent = hist[mask].tail(n)
    if len(recent) < 2:
        return np.nan

    pts = 0.0
    for _, row in recent.iterrows():
        if row["home_team"] == team:
            if row["home_score"] > row["away_score"]:
                pts += 3
            elif row["home_score"] == row["away_score"]:
                pts += 1
        else:
            if row["away_score"] > row["home_score"]:
                pts += 3
            elif row["home_score"] == row["away_score"]:
                pts += 1
    return pts


def _avg_goals(team: str, side: str, before_date: pd.Timestamp, hist: pd.DataFrame, n: int) -> float:
    """
    Average goals scored/conceded by *team* in last *n* matches before *before_date*.

    side='scored'   -> goals the team put in the net
    side='conceded' -> goals the team let in
    Returns NaN if fewer than 2 matches found.
    """
    mask = (
        ((hist["home_team"] == team) | (hist["away_team"] == team))
        & (hist["date"] < before_date)
    )
    recent = hist[mask].tail(n)
    if len(recent) < 2:
        return np.nan

    goals: list[int] = []
    for _, row in recent.iterrows():
        if row["home_team"] == team:
            goals.append(row["home_score"] if side == "scored" else row["away_score"])
        else:
            goals.append(row["away_score"] if side == "scored" else row["home_score"])
    return float(np.mean(goals))


def _h2h_rates(
    home_team: str,
    away_team: str,
    before_date: pd.Timestamp,
    hist: pd.DataFrame,
    n: int,
) -> tuple[float, float]:
    """
    Return (home_win_rate, draw_rate) from last *n* H2H encounters before *before_date*.

    The direction matters: home_win_rate is when home_team won at home against away_team
    OR when home_team beat away_team regardless of venue — we keep the fixture order
    consistent: first named team (home_team) vs second named team (away_team).

    Returns (0.33, 0.33) as neutral prior if < 2 H2H matches.
    """
    mask = (
        (
            ((hist["home_team"] == home_team) & (hist["away_team"] == away_team))
            | ((hist["home_team"] == away_team) & (hist["away_team"] == home_team))
        )
        & (hist["date"] < before_date)
    )
    h2h = hist[mask].tail(n)
    if len(h2h) < 2:
        return 0.333, 0.333

    home_wins = 0
    draws = 0
    total = len(h2h)
    for _, row in h2h.iterrows():
        if row["home_team"] == home_team:
            if row["home_score"] > row["away_score"]:
                home_wins += 1
            elif row["home_score"] == row["away_score"]:
                draws += 1
        else:
            # away_team in this row is home_team in our fixture -> "away win" from our perspective
            if row["away_score"] > row["home_score"]:
                home_wins += 1
            elif row["home_score"] == row["away_score"]:
                draws += 1

    return home_wins / total, draws / total


def _elo_expected(home_elo: float, away_elo: float, home_advantage: float = ELO_HOME_ADV) -> float:
    """Win probability for home team given Elo ratings."""
    return 1.0 / (1.0 + 10.0 ** ((away_elo - home_elo - home_advantage) / 400.0))


def _elo_update(
    home_elo: float, away_elo: float,
    home_score: int, away_score: int,
    k: float = ELO_K, neutral: bool = False,
) -> tuple[float, float]:
    """Return updated (home_elo, away_elo) after a match result."""
    adv = 0.0 if neutral else ELO_HOME_ADV
    expected = _elo_expected(home_elo, away_elo, home_advantage=adv)
    actual = 1.0 if home_score > away_score else (0.5 if home_score == away_score else 0.0)
    delta = k * (actual - expected)
    return home_elo + delta, away_elo - delta


def build_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Build feature matrix and label vector from raw results DataFrame.

    Uses strictly historical data before each match date to avoid leakage.
    FIFA ranking is approximated from the row itself (it changes slowly; the
    dataset does not include separate ranking snapshots, so we use the ranking
    implied by sorting — teams with more wins tend to rank higher).

    Because the Kaggle results.csv does not ship FIFA rankings, we derive a
    simple proxy ranking: rolling Elo-like score up to each match date.
    If a pre-computed ranking column is present it will be used directly.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Pre-compute chronological Elo ratings for every team.
    # Elo is updated after each match; at prediction time we use the rating
    # as of the moment just BEFORE the match (no data leakage).
    elo_ratings: dict[str, float] = {}  # team -> current Elo

    # Detect neutral-venue column
    has_neutral = "neutral" in df.columns

    # Major tournament keywords → higher K-factor
    major_keywords = {"world cup", "euro", "copa america", "africa cup", "asian cup", "gold cup"}

    rows = []
    labels = []

    for idx, match in df.iterrows():
        match_date = match["date"]
        home = match["home_team"]
        away = match["away_team"]

        # Historical data strictly before this match
        hist = df[df["date"] < match_date]

        # --- Elo ratings (before this match) ---
        home_elo = elo_ratings.get(home, ELO_INITIAL)
        away_elo = elo_ratings.get(away, ELO_INITIAL)
        elo_diff = home_elo - away_elo

        # --- Neutral venue ---
        is_neutral = bool(match["neutral"]) if has_neutral else False

        # --- Form ---
        home_form = _form_points(home, match_date, hist, FORM_WINDOW)
        away_form = _form_points(away, match_date, hist, FORM_WINDOW)
        if np.isnan(home_form):
            home_form = 5.0  # neutral prior (middle of 0-15 range)
        if np.isnan(away_form):
            away_form = 5.0
        form_diff = home_form - away_form

        # --- Goal averages ---
        home_gs = _avg_goals(home, "scored", match_date, hist, GOAL_WINDOW)
        away_gs = _avg_goals(away, "scored", match_date, hist, GOAL_WINDOW)
        home_gc = _avg_goals(home, "conceded", match_date, hist, GOAL_WINDOW)
        away_gc = _avg_goals(away, "conceded", match_date, hist, GOAL_WINDOW)

        if np.isnan(home_gs):
            home_gs = 1.2
        if np.isnan(away_gs):
            away_gs = 1.2
        if np.isnan(home_gc):
            home_gc = 1.2
        if np.isnan(away_gc):
            away_gc = 1.2

        # --- H2H ---
        h2h_hw, h2h_dr = _h2h_rates(home, away, match_date, hist, H2H_WINDOW)

        # --- xG proxy (StatsBomb not available; use goal avg * 0.9) ---
        home_xg = home_gs * 0.9
        away_xg = away_gs * 0.9

        # --- Label ---
        label = encode_outcome(int(match["home_score"]), int(match["away_score"]))

        rows.append([
            home_elo,
            away_elo,
            elo_diff,
            home_form,
            away_form,
            form_diff,
            home_gs,
            away_gs,
            home_gc,
            away_gc,
            h2h_hw,
            h2h_dr,
            home_xg,
            away_xg,
            1.0 if is_neutral else 0.0,
        ])
        labels.append(label)

        # Update Elo ratings after the match result
        tournament = str(match.get("tournament", "")).lower()
        k = ELO_K_WC if any(kw in tournament for kw in major_keywords) else ELO_K
        new_home_elo, new_away_elo = _elo_update(
            home_elo, away_elo,
            int(match["home_score"]), int(match["away_score"]),
            k=k, neutral=is_neutral,
        )
        elo_ratings[home] = new_home_elo
        elo_ratings[away] = new_away_elo

    X = np.array(rows, dtype=np.float32)
    y = np.array(labels, dtype=np.int32)
    return X, y


# ---------------------------------------------------------------------------
# Calibration check
# ---------------------------------------------------------------------------


def calibration_check(proba: np.ndarray, y_true: np.ndarray, n_bins: int = 5) -> None:
    """Print mean predicted probability vs actual frequency per class."""
    class_names = ["home_win", "draw", "away_win"]
    print("\n--- Calibration check (predicted mean prob vs actual frequency) ---")
    print(f"{'Class':<12} {'Pred mean':>10} {'Actual freq':>12} {'|Diff|':>8}")
    print("-" * 46)
    for c, name in enumerate(class_names):
        pred_mean = proba[:, c].mean()
        actual_freq = (y_true == c).mean()
        diff = abs(pred_mean - actual_freq)
        print(f"{name:<12} {pred_mean:>10.4f} {actual_freq:>12.4f} {diff:>8.4f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("Pre-match XGBoost model training")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Results CSV not found at {DATA_PATH}. "
            "Download from https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017"
        )

    print(f"\n[1/7] Loading data from {DATA_PATH} ...")
    df_raw = pd.read_csv(DATA_PATH, parse_dates=["date"])
    print(f"      Total rows loaded: {len(df_raw):,}")

    # Filter to year >= 2000
    df_raw = df_raw[df_raw["date"].dt.year >= 2000].copy()
    print(f"      Rows after year >= 2000 filter: {len(df_raw):,}")

    # Filter out friendlies
    if "tournament" in df_raw.columns:
        df_raw = df_raw[df_raw["tournament"] != "Friendly"].copy()
        print(f"      Rows after excluding friendlies: {len(df_raw):,}")
    else:
        warnings.warn(
            "Column 'tournament' not found in CSV — cannot filter friendlies. "
            "Proceeding with all matches.",
            stacklevel=2,
        )

    # Drop rows with NaN scores
    df_raw = df_raw.dropna(subset=["home_score", "away_score"]).copy()
    df_raw["home_score"] = df_raw["home_score"].astype(int)
    df_raw["away_score"] = df_raw["away_score"].astype(int)
    df_raw = df_raw.sort_values("date").reset_index(drop=True)
    print(f"      Rows after dropping NaN scores: {len(df_raw):,}")

    # ------------------------------------------------------------------
    # 2. Build features
    # ------------------------------------------------------------------
    print("\n[2/7] Building features (chronological, no data leakage) ...")
    print("      This may take several minutes for large datasets ...")
    X, y = build_features(df_raw)
    print(f"      Feature matrix shape: {X.shape}")

    # Align dates for splitting
    dates = pd.to_datetime(df_raw["date"].values)

    # ------------------------------------------------------------------
    # 3. Chronological train/val/test split
    # ------------------------------------------------------------------
    print("\n[3/7] Splitting data chronologically ...")
    train_mask = dates < pd.Timestamp(TRAIN_END)
    val_mask = (dates >= pd.Timestamp(TRAIN_END)) & (dates < pd.Timestamp(VAL_END))
    test_mask = dates >= pd.Timestamp(VAL_END)

    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    print(f"      Train size : {len(X_train):,} (pre-{TRAIN_END})")
    print(f"      Val size   : {len(X_val):,} ({TRAIN_END} to {VAL_END})")
    print(f"      Test size  : {len(X_test):,} (post-{VAL_END})")

    # Class distribution
    for split_name, y_split in [("Train", y_train), ("Val", y_val), ("Test", y_test)]:
        hw = (y_split == 0).sum()
        dr = (y_split == 1).sum()
        aw = (y_split == 2).sum()
        print(f"      {split_name}: home_win={hw}, draw={dr}, away_win={aw}")

    # Warn if Draw class is sparse in validation set
    draw_count = int((y_val == 1).sum())
    if draw_count < MIN_DRAW_SAMPLES:
        warnings.warn(
            f"WARNING: Draw class has only {draw_count} samples in validation set "
            f"(threshold: {MIN_DRAW_SAMPLES}). Consider using Platt scaling (method='sigmoid') "
            "instead of isotonic regression for calibration, as isotonic regression "
            "may overfit with small sample counts.",
            stacklevel=2,
        )
        print(
            f"\n  *** WARNING: Draw class has < {MIN_DRAW_SAMPLES} val samples ({draw_count}). "
            "Consider Platt scaling fallback. ***\n"
        )

    # ------------------------------------------------------------------
    # 4. Train model
    # ------------------------------------------------------------------
    print("\n[4/7] Training CalibratedClassifierCV(XGBClassifier, isotonic) ...")
    base = XGBClassifier(
        max_depth=4,
        n_estimators=300,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        verbosity=0,
    )
    # Upweight draws: draws are ~25% of matches but hardest to predict.
    # Weight 2.5× on draw samples to improve recall without collapsing accuracy.
    CLASS_WEIGHTS = {0: 1.0, 1: 1.3, 2: 1.0}
    sample_weights = np.array([CLASS_WEIGHTS[label] for label in y_train], dtype=np.float32)

    model = CalibratedClassifierCV(base, method="isotonic", cv=5)
    model.fit(X_train, y_train, sample_weight=sample_weights)
    print("      Training complete.")

    # ------------------------------------------------------------------
    # 5. Evaluate on validation set
    # ------------------------------------------------------------------
    print("\n[5/7] Evaluating on validation set ...")
    val_preds = model.predict(X_val)
    val_proba = model.predict_proba(X_val)
    accuracy = accuracy_score(y_val, val_preds)
    print(f"\n  Validation accuracy: {accuracy:.4f}")
    print("\n  Classification report (validation):")
    print(
        classification_report(
            y_val,
            val_preds,
            target_names=["home_win", "draw", "away_win"],
            digits=4,
        )
    )

    calibration_check(val_proba, y_val)

    # Test set quick check
    test_preds = model.predict(X_test)
    test_acc = accuracy_score(y_test, test_preds)
    print(f"\n  Test accuracy (post-{VAL_END}): {test_acc:.4f}")

    # ------------------------------------------------------------------
    # 6. Bootstrap confidence intervals (on validation set)
    # ------------------------------------------------------------------
    print(f"\n[6/7] Computing bootstrap CIs ({N_BOOTSTRAP} iterations) ...")
    rng = np.random.default_rng(seed=42)
    bootstrap_preds: list[np.ndarray] = []
    for _ in range(N_BOOTSTRAP):
        idx = rng.integers(0, len(X_val), size=len(X_val))
        preds = model.predict_proba(X_val[idx])
        bootstrap_preds.append(preds.mean(axis=0))

    bootstrap_arr = np.array(bootstrap_preds)  # shape (N_BOOTSTRAP, 3)
    ci_offsets = bootstrap_arr.std(axis=0) * 1.96  # shape (3,)

    print(f"      CI offsets (±1.96σ): home_win={ci_offsets[0]:.4f}, "
          f"draw={ci_offsets[1]:.4f}, away_win={ci_offsets[2]:.4f}")

    # ------------------------------------------------------------------
    # 7. Save artifact
    # ------------------------------------------------------------------
    print(f"\n[7/7] Saving artifact to {MODEL_OUTPUT} ...")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "label_map": LABEL_MAP,
        "ci_offsets": ci_offsets,          # shape (3,)
        "val_accuracy": float(accuracy),
        "training_date": str(datetime.date.today()),
        "version": "1.0.0",
    }
    joblib.dump(artifact, MODEL_OUTPUT)
    print(f"      Artifact saved: {MODEL_OUTPUT}")

    print("\n" + "=" * 60)
    print("Training complete.")
    print(f"  Version        : 1.0.0")
    print(f"  Training date  : {datetime.date.today()}")
    print(f"  Val accuracy   : {accuracy:.4f}")
    print(f"  Test accuracy  : {test_acc:.4f}")
    print(f"  CI offsets     : {ci_offsets}")
    print(f"  Artifact       : {MODEL_OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
