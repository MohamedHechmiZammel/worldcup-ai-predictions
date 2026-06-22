"""
Model evaluation script for the World Cup 2026 pre-match prediction model.

Loads a saved artifact and the raw results CSV, recreates the test set using
the same chronological split as training (test = year >= 2022, competitive
matches only), computes accuracy/F1/calibration metrics, and prints a summary.

Run from the backend/ directory:
    python -m ml.evaluate
    python -m ml.evaluate --artifact-path ml/artifacts/prematch_v1.0.0.joblib
    python -m ml.evaluate --data-path ml/data/raw/results.csv
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

# ---------------------------------------------------------------------------
# Constants (must match train_prematch.py)
# ---------------------------------------------------------------------------

TEST_START = "2022-01-01"
MIN_DRAW_SAMPLES = 500
N_CALIBRATION_BINS = 10

DEFAULT_ARTIFACT_PATH = Path("ml/artifacts/prematch_v1.0.0.joblib")
DEFAULT_DATA_PATH = Path("ml/data/raw/results.csv")
FEATURES_CACHE_PATH = Path("ml/data/raw/features_cache.parquet")

FORM_WINDOW = 5
H2H_WINDOW = 10
GOAL_WINDOW = 10


# ---------------------------------------------------------------------------
# Inline feature helpers (mirrors train_prematch.py to avoid leakage)
# ---------------------------------------------------------------------------

def _encode_outcome(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return 0
    if home_score == away_score:
        return 1
    return 2


def _form_points(team: str, before_date: pd.Timestamp, hist: pd.DataFrame, n: int) -> float:
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
            if row["away_score"] > row["home_score"]:
                home_wins += 1
            elif row["home_score"] == row["away_score"]:
                draws += 1
    return home_wins / total, draws / total


def _build_features_inline(df_full: pd.DataFrame, feature_columns: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """
    Build feature matrix and labels from the full (filtered) DataFrame.

    Uses strictly historical data before each match date to avoid leakage.
    Mirrors the logic in train_prematch.build_features().
    """
    df = df_full.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    has_ranking = "home_fifa_ranking" in df.columns and "away_fifa_ranking" in df.columns
    team_strength: dict[str, float] = {}

    rows: list[list[float]] = []
    labels: list[int] = []

    for _, match in df.iterrows():
        match_date = match["date"]
        home = match["home_team"]
        away = match["away_team"]

        hist = df[df["date"] < match_date]

        if has_ranking:
            home_rank = float(match["home_fifa_ranking"])
            away_rank = float(match["away_fifa_ranking"])
        else:
            home_str = team_strength.get(home, 0.5)
            away_str = team_strength.get(away, 0.5)
            home_rank = max(1.0, 200.0 * (1.0 - home_str))
            away_rank = max(1.0, 200.0 * (1.0 - away_str))

        ranking_diff = home_rank - away_rank

        home_form = _form_points(home, match_date, hist, FORM_WINDOW)
        away_form = _form_points(away, match_date, hist, FORM_WINDOW)
        if np.isnan(home_form):
            home_form = 5.0
        if np.isnan(away_form):
            away_form = 5.0
        form_diff = home_form - away_form

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

        h2h_hw, h2h_dr = _h2h_rates(home, away, match_date, hist, H2H_WINDOW)

        home_xg = home_gs * 0.9
        away_xg = away_gs * 0.9

        label = _encode_outcome(int(match["home_score"]), int(match["away_score"]))

        rows.append([
            home_rank, away_rank, ranking_diff,
            home_form, away_form, form_diff,
            home_gs, away_gs, home_gc, away_gc,
            h2h_hw, h2h_dr,
            home_xg, away_xg,
        ])
        labels.append(label)

        # Update team strength cache
        hs = match["home_score"]
        as_ = match["away_score"]
        he = team_strength.get(home, 0.5)
        ae = team_strength.get(away, 0.5)
        if hs > as_:
            team_strength[home] = he * 0.9 + 0.1 * 1.0
            team_strength[away] = ae * 0.9 + 0.1 * 0.0
        elif hs == as_:
            team_strength[home] = he * 0.9 + 0.1 * 0.5
            team_strength[away] = ae * 0.9 + 0.1 * 0.5
        else:
            team_strength[home] = he * 0.9 + 0.1 * 0.0
            team_strength[away] = ae * 0.9 + 0.1 * 1.0

    return np.array(rows, dtype=np.float32), np.array(labels, dtype=np.int32)


# ---------------------------------------------------------------------------
# Calibration helpers
# ---------------------------------------------------------------------------

def calibration_decile_table(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    class_idx: int,
    n_bins: int = N_CALIBRATION_BINS,
) -> list[dict]:
    """
    Build a calibration table for one class.

    Splits the predicted probability range [0, 1] into n_bins equal-width
    bins and for each bin reports: predicted mean probability, actual win rate,
    and sample count.
    """
    probs = y_prob[:, class_idx]
    actuals = (y_true == class_idx).astype(float)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    rows = []
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (probs >= lo) & (probs < hi) if i < n_bins - 1 else (probs >= lo) & (probs <= hi)
        n = mask.sum()
        if n == 0:
            continue
        pred_mean = float(probs[mask].mean())
        actual_rate = float(actuals[mask].mean())
        rows.append({"lo": lo, "hi": hi, "predicted": pred_mean, "actual": actual_rate, "n": int(n)})
    return rows


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def evaluate(artifact_path: Path, data_path: Path) -> None:
    # ------------------------------------------------------------------
    # 1. Load artifact
    # ------------------------------------------------------------------
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Artifact not found at {artifact_path}. "
            "Run python -m ml.train_prematch first."
        )
    print(f"\nLoading artifact from {artifact_path} ...")
    # Security note: joblib.load uses pickle internally and can execute arbitrary
    # code if given an untrusted file.  This script is only ever pointed at
    # artifacts produced by our own ml.train_prematch pipeline, which are
    # written to the version-controlled backend/ml/artifacts/ directory.
    # Never load an artifact received from an external or untrusted source.
    artifact: dict = joblib.load(artifact_path)

    model = artifact["model"]
    feature_columns: list[str] = artifact["feature_columns"]
    label_map: dict[int, str] = artifact["label_map"]
    version: str = artifact.get("version", "unknown")
    training_date: str = artifact.get("training_date", "unknown")
    ci_offsets: np.ndarray = artifact.get("ci_offsets", np.zeros(3))

    print(f"  Version:       {version}")
    print(f"  Training date: {training_date}")
    print(f"  Features:      {len(feature_columns)} columns")
    print(f"  Label map:     {label_map}")

    # ------------------------------------------------------------------
    # 2. Load raw data
    # ------------------------------------------------------------------
    if not data_path.exists():
        raise FileNotFoundError(
            f"Results CSV not found at {data_path}. "
            "Download from https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017"
        )
    print(f"\nLoading data from {data_path} ...")
    df_raw = pd.read_csv(data_path, parse_dates=["date"])
    print(f"  Total rows: {len(df_raw):,}")

    # ------------------------------------------------------------------
    # 3. Apply same filters as training (competitive matches only)
    # ------------------------------------------------------------------
    df_raw = df_raw[df_raw["date"].dt.year >= 2000].copy()
    if "tournament" in df_raw.columns:
        df_raw = df_raw[df_raw["tournament"] != "Friendly"].copy()
    else:
        warnings.warn(
            "Column 'tournament' not found in CSV — cannot filter friendlies.",
            stacklevel=2,
        )
    df_raw = df_raw.dropna(subset=["home_score", "away_score"]).copy()
    df_raw["home_score"] = df_raw["home_score"].astype(int)
    df_raw["away_score"] = df_raw["away_score"].astype(int)
    df_raw = df_raw.sort_values("date").reset_index(drop=True)
    print(f"  After filters (year>=2000, competitive): {len(df_raw):,} rows")

    # ------------------------------------------------------------------
    # 4. Build / load features
    # ------------------------------------------------------------------
    if FEATURES_CACHE_PATH.exists():
        print(f"\nLoading cached features from {FEATURES_CACHE_PATH} ...")
        df_cache = pd.read_parquet(FEATURES_CACHE_PATH)
        # Align index with df_raw
        X_all = df_cache[feature_columns].values.astype(np.float32)
        y_all = df_cache["label"].values.astype(np.int32)
        dates = pd.to_datetime(df_cache["date"].values)
    else:
        print(
            "\nNo features cache found. Computing features from scratch "
            "(this may take several minutes) ..."
        )
        try:
            from ml.features import build_prematch_features, FEATURE_COLUMNS as FC  # noqa: F401
            print("  Using ml.features.build_prematch_features ...")
            # build_prematch_features returns (X, y) aligned to df_raw rows
            X_all, y_all = build_prematch_features(df_raw)
        except (ImportError, TypeError):
            print("  ml.features.build_prematch_features not available; using inline feature builder ...")
            X_all, y_all = _build_features_inline(df_raw, feature_columns)
        dates = pd.to_datetime(df_raw["date"].values)

    # ------------------------------------------------------------------
    # 5. Isolate test set (year >= 2022, competitive matches only)
    # ------------------------------------------------------------------
    test_mask = dates >= pd.Timestamp(TEST_START)
    X_test = X_all[test_mask]
    y_test = y_all[test_mask]
    test_dates = dates[test_mask]

    n_test = len(X_test)
    n_home_win = int((y_test == 0).sum())
    n_draw = int((y_test == 1).sum())
    n_away_win = int((y_test == 2).sum())

    draw_warning = n_draw < MIN_DRAW_SAMPLES

    if n_test == 0:
        raise ValueError(
            f"No test samples found after {TEST_START}. "
            "Ensure the dataset contains matches from 2022 onwards."
        )

    print(f"\nTest set: {TEST_START} to present")
    print(f"  Total:     {n_test:,}")
    print(f"  home_win:  {n_home_win:,}")
    print(f"  draw:      {n_draw:,}" + (" *** WARNING: < 500 samples ***" if draw_warning else ""))
    print(f"  away_win:  {n_away_win:,}")

    # ------------------------------------------------------------------
    # 6. Predict
    # ------------------------------------------------------------------
    print("\nRunning predictions ...")
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)  # shape (N, 3)

    # ------------------------------------------------------------------
    # 7. Metrics
    # ------------------------------------------------------------------
    overall_acc = accuracy_score(y_test, y_pred)

    # Per-class accuracy
    per_class_acc: dict[int, float] = {}
    for c in range(3):
        mask_c = y_test == c
        if mask_c.sum() > 0:
            per_class_acc[c] = float((y_pred[mask_c] == c).mean())
        else:
            per_class_acc[c] = float("nan")

    # Per-class F1
    f1_scores = f1_score(y_test, y_pred, labels=[0, 1, 2], average=None, zero_division=0)

    # ------------------------------------------------------------------
    # 8. Calibration curve data (home_win class by default; print all)
    # ------------------------------------------------------------------
    cal_tables: dict[int, list[dict]] = {}
    for c in range(3):
        cal_tables[c] = calibration_decile_table(y_test, y_prob, c)

    # ------------------------------------------------------------------
    # 9. Print summary table
    # ------------------------------------------------------------------
    print()
    print(f"{'=' * 55}")
    print(f"=== Model Evaluation: prematch_v{version} ===")
    print(f"{'=' * 55}")
    print(f"Test period: {TEST_START}-present (N={n_test:,} matches)")
    print()
    print(f"Overall accuracy:  {overall_acc * 100:.1f}%")
    print(
        f"Home win accuracy: {per_class_acc[0] * 100:.1f}%  (N={n_home_win:,})"
    )
    draw_line = f"Draw accuracy:     {per_class_acc[1] * 100:.1f}%  (N={n_draw:,})"
    if draw_warning:
        draw_line += "   <- WARNING: < 500 samples (Platt scaling fallback may be needed)"
    print(draw_line)
    print(
        f"Away win accuracy: {per_class_acc[2] * 100:.1f}%  (N={n_away_win:,})"
    )
    print()
    print("Per-class F1:")
    print(f"  home_win: {f1_scores[0]:.3f}")
    print(f"  draw:     {f1_scores[1]:.3f}")
    print(f"  away_win: {f1_scores[2]:.3f}")
    print()

    # CI offsets info
    if ci_offsets is not None and np.any(ci_offsets != 0):
        print("CI offsets (bootstrap 90% interval half-widths):")
        for c, name in label_map.items():
            print(f"  {name}: ±{ci_offsets[c]:.4f}")
        print()

    # Calibration per class
    for c, class_name in label_map.items():
        table = cal_tables[c]
        if not table:
            continue
        print(f"Calibration — {class_name} (predicted prob vs actual rate):")
        for row in table:
            lo = row["lo"]
            hi = row["hi"]
            pred = row["predicted"]
            actual = row["actual"]
            n_bin = row["n"]
            print(f"  {lo:.2f}-{hi:.2f}:  predicted={pred:.3f}  actual={actual:.3f}  (N={n_bin})")
        print()

    print(f"{'=' * 55}")

    if draw_warning:
        warnings.warn(
            f"Draw class has only {n_draw} samples in the test set "
            f"(threshold: {MIN_DRAW_SAMPLES}). "
            "Platt scaling fallback (method='sigmoid') may produce better-calibrated "
            "draw probabilities than isotonic regression.",
            stacklevel=2,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the pre-match XGBoost model against the held-out test set."
    )
    parser.add_argument(
        "--artifact-path",
        type=Path,
        default=DEFAULT_ARTIFACT_PATH,
        help=f"Path to the .joblib artifact (default: {DEFAULT_ARTIFACT_PATH})",
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"Path to the raw results CSV (default: {DEFAULT_DATA_PATH})",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    evaluate(artifact_path=args.artifact_path, data_path=args.data_path)


if __name__ == "__main__":
    main()
