"""Minimal 1X2 market backtest for Ligue 1 historical odds.

This module evaluates market probabilities. It does not generate live betting
advice and it does not alter the existing PRONO display engine.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

import pandas as pd

from .metrics import CalibrationBin, brier_score_multiclass, calibration_bins, log_loss_multiclass
from .odds import devig_proportional

OUTCOME_TO_INDEX = {"H": 0, "D": 1, "A": 2}
INDEX_TO_OUTCOME = {v: k for k, v in OUTCOME_TO_INDEX.items()}
DEFAULT_WARNING_NO_SNAPSHOT = (
    "ODDS_SNAPSHOT_TIME_MISSING: historical odds are treated as a closing proxy; "
    "this can measure market calibration but cannot validate decision-time value, CLV, or anti-leakage."
)


class TemporalLeakageError(ValueError):
    """Raised when a backtest uses data unavailable at decision time."""


@dataclass(frozen=True)
class MatchPrediction:
    kickoff: str
    home: str
    away: str
    outcome: str
    probabilities: tuple[float, float, float]
    pick_outcome: str
    pick_probability: float
    success: bool
    source: str


@dataclass(frozen=True)
class MarketBacktestResult:
    source: str
    n_matches: int
    log_loss: float
    brier_score: float
    accuracy: float
    warnings: tuple[str, ...]
    calibration: tuple[CalibrationBin, ...]
    predictions: tuple[MatchPrediction, ...]


def validate_no_future_data(
    frame: pd.DataFrame,
    data_time_column: str,
    decision_time_column: str,
) -> None:
    """Reject rows where data timestamp is after the theoretical decision time."""
    missing = [c for c in (data_time_column, decision_time_column) if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing temporal column(s): {', '.join(missing)}")
    data_times = pd.to_datetime(frame[data_time_column], errors="coerce")
    decision_times = pd.to_datetime(frame[decision_time_column], errors="coerce")
    invalid = data_times.isna() | decision_times.isna()
    if invalid.any():
        raise TemporalLeakageError("Temporal columns must contain valid datetimes for every tested row.")
    leaked = data_times > decision_times
    if leaked.any():
        first = frame.index[leaked][0]
        raise TemporalLeakageError(
            f"Future data detected at row {first}: {data_time_column} is after {decision_time_column}."
        )


def run_market_1x2_backtest(
    matches: pd.DataFrame,
    odds_columns: Mapping[str, str],
    source: str,
    captured_at_column: str | None = None,
    decision_at_column: str | None = None,
) -> MarketBacktestResult:
    """Evaluate no-vig market probabilities against historical 1X2 results.

    If no captured/decision timestamps are supplied, the function returns a
    warning and treats odds as a closing proxy. That mode is useful for market
    calibration only, not for value-betting validation.
    """
    required = ["Kickoff", "HomeTeam", "AwayTeam", "FTR", odds_columns["H"], odds_columns["D"], odds_columns["A"]]
    missing = [c for c in required if c not in matches.columns]
    if missing:
        raise ValueError(f"Missing backtest column(s): {', '.join(missing)}")

    warnings: list[str] = []
    if captured_at_column and decision_at_column:
        validate_no_future_data(matches, captured_at_column, decision_at_column)
    else:
        warnings.append(DEFAULT_WARNING_NO_SNAPSHOT)

    predictions: list[MatchPrediction] = []
    probability_rows: list[tuple[float, float, float]] = []
    outcome_indexes: list[int] = []
    pick_probabilities: list[float] = []
    pick_successes: list[bool] = []

    for _, row in matches.iterrows():
        outcome = str(row.get("FTR", ""))
        if outcome not in OUTCOME_TO_INDEX:
            continue
        odds = [row.get(odds_columns["H"]), row.get(odds_columns["D"]), row.get(odds_columns["A"])]
        try:
            if any(not math.isfinite(float(o)) for o in odds):
                continue
            devig = devig_proportional(odds)
        except (TypeError, ValueError):
            continue
        probabilities = tuple(float(p) for p in devig.probabilities)
        if len(probabilities) != 3:
            continue
        pick_index = max(range(3), key=lambda i: probabilities[i])
        pick_outcome = INDEX_TO_OUTCOME[pick_index]
        success = pick_outcome == outcome

        probability_rows.append(probabilities)  # type: ignore[arg-type]
        outcome_indexes.append(OUTCOME_TO_INDEX[outcome])
        pick_probabilities.append(probabilities[pick_index])
        pick_successes.append(success)
        predictions.append(MatchPrediction(
            kickoff=str(row["Kickoff"]),
            home=str(row["HomeTeam"]),
            away=str(row["AwayTeam"]),
            outcome=outcome,
            probabilities=probabilities,  # type: ignore[arg-type]
            pick_outcome=pick_outcome,
            pick_probability=probabilities[pick_index],
            success=success,
            source=source,
        ))

    if not predictions:
        raise ValueError("No valid historical 1X2 rows available for backtest.")

    return MarketBacktestResult(
        source=source,
        n_matches=len(predictions),
        log_loss=log_loss_multiclass(probability_rows, outcome_indexes),
        brier_score=brier_score_multiclass(probability_rows, outcome_indexes),
        accuracy=sum(1.0 for ok in pick_successes if ok) / len(pick_successes),
        warnings=tuple(warnings),
        calibration=tuple(calibration_bins(pick_probabilities, pick_successes)),
        predictions=tuple(predictions),
    )
