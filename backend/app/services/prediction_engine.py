"""
Core ML prediction service for the World Cup 2026 AI Prediction Dashboard.

Loads the active pre-match XGBoost artifact from the database, runs inference
with SHAP explanations, and persists each prediction to the ``predictions`` table.

Singleton usage::

    from app.services.prediction_engine import prediction_engine

    # At application startup (lifespan):
    await prediction_engine.load(db)

    # At request time:
    result = await prediction_engine.predict_and_save(match_id=42, db=db)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.match import Match
from app.models.model_version import ModelVersion
from app.models.prediction import Prediction
from ml.features import (
    FEATURE_COLUMNS,
    build_prematch_features,
    format_factor_label,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data transfer object
# ---------------------------------------------------------------------------


@dataclass
class PredictionResult:
    """Immutable snapshot of a single pre-match prediction."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: float
    expected_away_goals: float
    confidence_low: float
    confidence_high: float
    top_factors: list[dict[str, Any]] = field(default_factory=list)
    model_version_id: int = 0


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class PredictionEngine:
    """Loads the active pre-match ML model and runs calibrated inference.

    Lifecycle
    ---------
    1.  Call ``await load(db)`` once at application startup (lifespan hook).
    2.  Call ``predict_prematch(...)`` for synchronous, in-process inference.
    3.  Call ``await predict_and_save(match_id, db)`` to persist results.
    """

    def __init__(self) -> None:
        self._artifact: dict[str, Any] | None = None
        self._historical_results: pd.DataFrame | None = None
        self._statsbomb_xg: dict[str, float] = {}
        self._model_version_id: int | None = None

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    async def load(self, db: AsyncSession) -> None:
        """Load the active prematch model and supporting data.

        Steps
        -----
        1. Query ``model_versions`` for ``model_type='prematch'`` and
           ``is_active=TRUE``.
        2. ``joblib.load(artifact_path)`` to deserialise the artifact dict.
        3. Load ``ml/data/raw/results.csv`` as historical results if present.
        4. Load StatsBomb xG mapping if available.

        Parameters
        ----------
        db:
            An async SQLAlchemy session (used only for the DB query).
        """
        # 1. Resolve active model version from DB
        stmt = select(ModelVersion).where(
            ModelVersion.model_type == "prematch",
            ModelVersion.is_active.is_(True),
        )
        result = await db.execute(stmt)
        model_version: ModelVersion | None = result.scalars().first()

        if model_version is None:
            logger.warning(
                "No active prematch model found in model_versions. "
                "Prediction engine will not be available until a model is registered."
            )
            return

        artifact_path = model_version.artifact_path
        if not Path(artifact_path).exists():
            logger.error(
                "Artifact file does not exist at %s. "
                "Run ml/train_prematch.py and ml/register_model.py first.",
                artifact_path,
            )
            return

        # 2. Deserialise artifact.
        # joblib.load executes pickle bytecode, which allows arbitrary code
        # execution from a malicious file.  This is safe here because:
        #   a) The artifact is produced exclusively by our own ml/train_prematch.py
        #      script and stored at a path we control (committed to the repo or
        #      written by the training pipeline on the same host).
        #   b) The artifact_path comes from our own model_versions DB row, not
        #      from any external/user-supplied input.
        #   c) The file is never fetched from a remote URL at runtime.
        self._artifact = joblib.load(artifact_path)  # noqa: S301
        self._model_version_id = model_version.id

        logger.info(
            "Loaded prematch model version=%s (id=%d) from %s",
            model_version.version,
            model_version.id,
            artifact_path,
        )

        # 3. Historical results CSV
        raw_csv = Path(__file__).resolve().parents[3] / "ml" / "data" / "raw" / "results.csv"
        if raw_csv.exists():
            self._historical_results = pd.read_csv(raw_csv, parse_dates=["date"])
            logger.info(
                "Loaded %d historical results from %s",
                len(self._historical_results),
                raw_csv,
            )
        else:
            # Empty DataFrame — features will fall back to their neutral priors
            logger.warning(
                "Historical results CSV not found at %s. "
                "Feature engineering will use neutral priors for form/H2H.",
                raw_csv,
            )
            self._historical_results = pd.DataFrame(
                columns=["date", "home_team", "away_team", "home_score", "away_score", "tournament"]
            )

        # 4. StatsBomb xG (optional)
        statsbomb_path = (
            Path(__file__).resolve().parents[3] / "ml" / "data" / "raw" / "statsbomb_xg.json"
        )
        if statsbomb_path.exists():
            import json

            with statsbomb_path.open() as fh:
                self._statsbomb_xg = json.load(fh)
            logger.info("Loaded StatsBomb xG data for %d teams", len(self._statsbomb_xg))
        else:
            self._statsbomb_xg = {}
            logger.info("No StatsBomb xG file found — will use feature defaults.")

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _require_loaded(self) -> None:
        """Raise if the engine has not been initialised yet."""
        if self._artifact is None:
            raise RuntimeError(
                "Prediction engine not initialized. Call load() first."
            )

    # ------------------------------------------------------------------
    # Core inference
    # ------------------------------------------------------------------

    def predict_prematch(
        self,
        home_team_name: str,
        away_team_name: str,
        home_fifa_ranking: int,
        away_fifa_ranking: int,
    ) -> PredictionResult:
        """Run calibrated pre-match inference for a single fixture.

        Parameters
        ----------
        home_team_name:
            Display name of the home team (must match historical results rows).
        away_team_name:
            Display name of the away team.
        home_fifa_ranking:
            Current FIFA ranking (1 = best) for the home side.
        away_fifa_ranking:
            Current FIFA ranking for the away side.

        Returns
        -------
        PredictionResult
            Probabilities, expected goals, CI, and top SHAP factors.

        Raises
        ------
        RuntimeError
            If ``load()`` has not been called successfully.
        """
        self._require_loaded()

        artifact: dict[str, Any] = self._artifact  # type: ignore[assignment]
        model = artifact["model"]
        ci_offsets: np.ndarray = artifact["ci_offsets"]

        # 1. Build feature dict
        assert self._historical_results is not None  # noqa: S101 — always set after load()
        features = build_prematch_features(
            home_team_name=home_team_name,
            away_team_name=away_team_name,
            home_fifa_ranking=home_fifa_ranking,
            away_fifa_ranking=away_fifa_ranking,
            historical_results=self._historical_results,
            statsbomb_xg=self._statsbomb_xg,
        )

        # 2. Build ordered numpy array matching artifact feature_columns
        feature_columns: list[str] = artifact.get("feature_columns", FEATURE_COLUMNS)
        X = np.array(
            [[features[col] for col in feature_columns]], dtype=np.float32
        )  # shape (1, 14)

        # 3. Predict probabilities
        proba: np.ndarray = model.predict_proba(X)[0]  # shape (3,)
        p_home, p_draw, p_away = float(proba[0]), float(proba[1]), float(proba[2])

        # 4. Expected goals (Poisson parameters)
        lambda_home = (
            features["home_avg_goals_scored"] * 0.9 + features["home_xg_avg"] * 0.1
        )
        lambda_away = (
            features["away_avg_goals_scored"] * 0.9 + features["away_xg_avg"] * 0.1
        )

        # 5. Confidence interval (win probability for the predicted class ± 1.96σ)
        predicted_class = int(np.argmax(proba))
        ci_offset = float(ci_offsets[predicted_class])
        predicted_prob = float(proba[predicted_class])
        confidence_low = max(0.0, predicted_prob - ci_offset)
        confidence_high = min(1.0, predicted_prob + ci_offset)

        # 6. SHAP top-3 factors
        top_factors = self._compute_top_factors(
            model=model,
            X=X,
            predicted_class=predicted_class,
            feature_columns=feature_columns,
            features=features,
            home_team_name=home_team_name,
            away_team_name=away_team_name,
        )

        return PredictionResult(
            home_win_prob=p_home,
            draw_prob=p_draw,
            away_win_prob=p_away,
            expected_home_goals=lambda_home,
            expected_away_goals=lambda_away,
            confidence_low=confidence_low,
            confidence_high=confidence_high,
            top_factors=top_factors,
            model_version_id=self._model_version_id or 0,
        )

    # ------------------------------------------------------------------
    # SHAP helpers
    # ------------------------------------------------------------------

    def _compute_top_factors(
        self,
        model: Any,
        X: np.ndarray,
        predicted_class: int,
        feature_columns: list[str],
        features: dict[str, float],
        home_team_name: str,
        away_team_name: str,
    ) -> list[dict[str, Any]]:
        """Extract the top-3 SHAP factors for the predicted outcome class.

        Falls back gracefully to an empty list if SHAP is unavailable or the
        inner estimator cannot be accessed.

        Parameters
        ----------
        model:
            The ``CalibratedClassifierCV`` loaded from the artifact.
        X:
            Feature matrix of shape ``(1, n_features)``.
        predicted_class:
            Index of the predicted class (0=home_win, 1=draw, 2=away_win).
        feature_columns:
            Ordered list of feature names (must align with ``X`` columns).
        features:
            Feature dict (raw values, for human-readable labels).
        home_team_name / away_team_name:
            Used by ``format_factor_label``.

        Returns
        -------
        list[dict]
            Up to 3 dicts with keys ``feature``, ``impact_pct``, ``label``.
        """
        try:
            import shap

            # CalibratedClassifierCV wraps multiple calibrated classifiers;
            # access the base XGBoost estimator from the first one.
            inner_model = model.calibrated_classifiers_[0].estimator
            explainer = shap.TreeExplainer(inner_model)
            shap_values = explainer.shap_values(X)
            # shap_values shape: (3, n_samples, n_features) for multi-class XGBoost
            # For n_samples=1: shap_values[class_idx][0] → (n_features,)
            shap_for_class: np.ndarray = shap_values[predicted_class][0]
        except Exception as exc:
            logger.warning("SHAP computation failed: %s — top_factors will be empty.", exc)
            return []

        abs_shap = np.abs(shap_for_class)
        total_abs = float(abs_shap.sum())
        if total_abs == 0.0:
            return []

        top_indices = np.argsort(abs_shap)[::-1][:3]
        top_factors: list[dict[str, Any]] = []
        for idx in top_indices:
            feature_name = feature_columns[idx]
            shap_val = float(shap_for_class[idx])
            impact_pct = abs(shap_val) / total_abs * 100.0
            label = format_factor_label(
                feature_name,
                home_team_name,
                away_team_name,
                features[feature_name],
            )
            top_factors.append(
                {
                    "feature": feature_name,
                    "impact_pct": round(impact_pct, 2),
                    "label": label,
                }
            )

        return top_factors

    # ------------------------------------------------------------------
    # DB-backed orchestration
    # ------------------------------------------------------------------

    async def predict_and_save(
        self,
        match_id: int,
        db: AsyncSession,
        triggering_event_id: int | None = None,
    ) -> PredictionResult | None:
        """Load match + team data from DB, run prediction, and persist.

        A **new** ``Prediction`` row is inserted each time (history is kept).
        Returns ``None`` when the engine is not yet loaded or the match is not
        found, so callers can treat a ``None`` return as "no prediction available"
        without raising.

        Parameters
        ----------
        match_id:
            Primary key of the ``matches`` row to predict for.
        db:
            Async SQLAlchemy session.
        triggering_event_id:
            Optional FK to ``live_events.id`` (set for in-game re-predictions).

        Returns
        -------
        PredictionResult | None
            The prediction result, or ``None`` on failure.
        """
        if self._artifact is None:
            logger.warning(
                "predict_and_save called before engine was loaded (match_id=%d). Skipping.",
                match_id,
            )
            return None

        # 1. Load match with home/away teams eagerly
        stmt = (
            select(Match)
            .options(
                selectinload(Match.home_team),
                selectinload(Match.away_team),
            )
            .where(Match.id == match_id)
        )
        result = await db.execute(stmt)
        match: Match | None = result.scalars().first()

        if match is None:
            logger.warning("Match id=%d not found in DB.", match_id)
            return None

        home_team = match.home_team
        away_team = match.away_team

        home_ranking = int(home_team.fifa_ranking) if home_team.fifa_ranking is not None else 100
        away_ranking = int(away_team.fifa_ranking) if away_team.fifa_ranking is not None else 100

        # 2. Run inference
        try:
            prediction_result = self.predict_prematch(
                home_team_name=home_team.name,
                away_team_name=away_team.name,
                home_fifa_ranking=home_ranking,
                away_fifa_ranking=away_ranking,
            )
        except Exception:
            logger.exception(
                "Inference failed for match_id=%d (%s vs %s).",
                match_id,
                home_team.name,
                away_team.name,
            )
            return None

        # 3. Persist — insert a new row every time (history preserved)
        db_prediction = Prediction(
            match_id=match_id,
            model_version_id=prediction_result.model_version_id,
            prediction_type="prematch",
            home_win_prob=round(prediction_result.home_win_prob, 5),
            draw_prob=round(prediction_result.draw_prob, 5),
            away_win_prob=round(prediction_result.away_win_prob, 5),
            expected_home_goals=round(prediction_result.expected_home_goals, 2),
            expected_away_goals=round(prediction_result.expected_away_goals, 2),
            confidence_low=round(prediction_result.confidence_low, 5),
            confidence_high=round(prediction_result.confidence_high, 5),
            top_factors=prediction_result.top_factors,
            triggering_event_id=triggering_event_id,
        )
        db.add(db_prediction)
        await db.flush()  # assign PK without committing — caller controls transaction

        logger.info(
            "Saved prediction id=%d for match_id=%d: home_win=%.3f draw=%.3f away_win=%.3f",
            db_prediction.id,
            match_id,
            prediction_result.home_win_prob,
            prediction_result.draw_prob,
            prediction_result.away_win_prob,
        )

        return prediction_result


    # ------------------------------------------------------------------
    # In-game (live) prediction
    # ------------------------------------------------------------------

    async def predict_ingame(
        self,
        match_id: int,
        triggering_event_id: int,
        db: AsyncSession,
    ) -> PredictionResult | None:
        """Compute in-game prediction using Poisson goal model.

        Algorithm:
        1. Fetch current match state (score, minute)
        2. Get pre-match expected goals (λ_home, λ_away) from the most recent prematch prediction
        3. Scale remaining λ by (1 - minute/90), applying trailing_factor=1.15 for losing team
        4. Enumerate P(h, a) for h,a in 0..9 additional goals via Poisson PMF
        5. Apply Dixon-Coles ρ correction for scorelines (0-0), (1-0), (0-1), (1-1)
        6. Sum outcomes to get P(home_win), P(draw), P(away_win) given current score
        7. Blend with pre-match priors weighted by minute/90
        8. Store and return PredictionResult
        """
        if self._artifact is None:
            return None

        # 1. Load match with teams
        from sqlalchemy.orm import selectinload as _selectinload
        stmt = (
            select(Match)
            .options(_selectinload(Match.home_team), _selectinload(Match.away_team))
            .where(Match.id == match_id)
        )
        result = await db.execute(stmt)
        match: Match | None = result.scalars().first()
        if match is None:
            return None

        home_score = match.home_score or 0
        away_score = match.away_score or 0
        # Estimate current minute from triggering event
        from app.models.live_event import LiveEvent
        ev_stmt = select(LiveEvent).where(LiveEvent.id == triggering_event_id)
        ev_result = await db.execute(ev_stmt)
        live_event = ev_result.scalar_one_or_none()
        minute = live_event.minute if live_event else 45
        minute = max(1, min(90, minute))

        # 2. Get pre-match λ values from most recent prematch prediction
        from sqlalchemy import desc
        prematch_stmt = (
            select(Prediction)
            .where(Prediction.match_id == match_id, Prediction.prediction_type == "prematch")
            .order_by(desc(Prediction.created_at))
            .limit(1)
        )
        prematch_result = await db.execute(prematch_stmt)
        prematch_pred = prematch_result.scalar_one_or_none()

        if prematch_pred is not None:
            lambda_home_full = float(prematch_pred.expected_home_goals)
            lambda_away_full = float(prematch_pred.expected_away_goals)
            p_home_prior = float(prematch_pred.home_win_prob)
            p_draw_prior = float(prematch_pred.draw_prob)
            p_away_prior = float(prematch_pred.away_win_prob)
        else:
            # Fallback: compute from team features
            lambda_home_full = 1.35
            lambda_away_full = 1.15
            p_home_prior, p_draw_prior, p_away_prior = 0.40, 0.30, 0.30

        # 3. Scale remaining λ
        time_fraction = minute / 90.0
        remaining = 1.0 - time_fraction
        TRAILING_FACTOR = 1.15

        # Apply trailing factor for the losing team
        if home_score < away_score:
            lambda_home_remaining = lambda_home_full * remaining * TRAILING_FACTOR
            lambda_away_remaining = lambda_away_full * remaining
        elif away_score < home_score:
            lambda_home_remaining = lambda_home_full * remaining
            lambda_away_remaining = lambda_away_full * remaining * TRAILING_FACTOR
        else:
            lambda_home_remaining = lambda_home_full * remaining
            lambda_away_remaining = lambda_away_full * remaining

        # 4 & 5. Enumerate additional goals and compute outcome probabilities
        from scipy.stats import poisson

        # Dixon-Coles ρ correction
        RHO = -0.13

        def dc_correction(h_add: int, a_add: int, lh: float, la: float) -> float:
            """Dixon-Coles correction for low-scoring outcomes."""
            if h_add == 0 and a_add == 0:
                return 1.0 - lh * la * RHO
            elif h_add == 1 and a_add == 0:
                return 1.0 + la * RHO
            elif h_add == 0 and a_add == 1:
                return 1.0 + lh * RHO
            elif h_add == 1 and a_add == 1:
                return 1.0 - RHO
            return 1.0

        MAX_GOALS = 10
        p_home_win = 0.0
        p_draw = 0.0
        p_away_win = 0.0

        for h_add in range(MAX_GOALS):
            for a_add in range(MAX_GOALS):
                ph = poisson.pmf(h_add, lambda_home_remaining)
                pa = poisson.pmf(a_add, lambda_away_remaining)
                correction = dc_correction(h_add, a_add, lambda_home_remaining, lambda_away_remaining)
                prob = ph * pa * correction

                final_home = home_score + h_add
                final_away = away_score + a_add

                if final_home > final_away:
                    p_home_win += prob
                elif final_home == final_away:
                    p_draw += prob
                else:
                    p_away_win += prob

        # Normalize (should already sum to ~1 but floating point)
        total = p_home_win + p_draw + p_away_win
        if total > 0:
            p_home_win /= total
            p_draw /= total
            p_away_win /= total

        # 7. Blend with pre-match priors (more weight on Poisson as match progresses)
        blend_weight = time_fraction  # 0 at kickoff → 1 at fulltime
        p_home_win = blend_weight * p_home_win + (1 - blend_weight) * p_home_prior
        p_draw = blend_weight * p_draw + (1 - blend_weight) * p_draw_prior
        p_away_win = blend_weight * p_away_win + (1 - blend_weight) * p_away_prior

        # Re-normalize after blending
        total = p_home_win + p_draw + p_away_win
        p_home_win /= total
        p_draw /= total
        p_away_win /= total

        # 8. CI from artifact bootstrap offsets
        artifact = self._artifact
        ci_offsets: np.ndarray = artifact["ci_offsets"]
        predicted_class = int(np.argmax([p_home_win, p_draw, p_away_win]))
        ci_offset = float(ci_offsets[predicted_class])
        predicted_prob = [p_home_win, p_draw, p_away_win][predicted_class]
        confidence_low = max(0.0, predicted_prob - ci_offset)
        confidence_high = min(1.0, predicted_prob + ci_offset)

        # 9. Persist and return
        db_prediction = Prediction(
            match_id=match_id,
            model_version_id=self._model_version_id or 0,
            prediction_type="live",
            home_win_prob=round(p_home_win, 5),
            draw_prob=round(p_draw, 5),
            away_win_prob=round(p_away_win, 5),
            expected_home_goals=round(lambda_home_remaining, 2),
            expected_away_goals=round(lambda_away_remaining, 2),
            confidence_low=round(confidence_low, 5),
            confidence_high=round(confidence_high, 5),
            top_factors=[],  # Poisson model doesn't produce SHAP factors
            triggering_event_id=triggering_event_id,
        )
        db.add(db_prediction)
        await db.flush()

        return PredictionResult(
            home_win_prob=p_home_win,
            draw_prob=p_draw,
            away_win_prob=p_away_win,
            expected_home_goals=lambda_home_remaining,
            expected_away_goals=lambda_away_remaining,
            confidence_low=confidence_low,
            confidence_high=confidence_high,
            top_factors=[],
            model_version_id=self._model_version_id or 0,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

prediction_engine = PredictionEngine()
