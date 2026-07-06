"""Backtest metrics for value-betting research."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

EPSILON = 1e-15


@dataclass(frozen=True)
class CalibrationBin:
    lower: float
    upper: float
    count: int
    predicted_mean: float | None
    actual_rate: float | None
    gap: float | None


def _clip_probability(probability: float) -> float:
    p = float(probability)
    if not math.isfinite(p):
        raise ValueError("Probability must be finite.")
    return min(max(p, EPSILON), 1.0 - EPSILON)


def log_loss_multiclass(probabilities: Sequence[Sequence[float]], outcomes: Sequence[int]) -> float:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("Probabilities and outcomes must have the same non-zero length.")
    losses = []
    for row, outcome in zip(probabilities, outcomes):
        if outcome < 0 or outcome >= len(row):
            raise ValueError("Outcome index is outside the probability vector.")
        losses.append(-math.log(_clip_probability(row[outcome])))
    return sum(losses) / len(losses)


def brier_score_multiclass(probabilities: Sequence[Sequence[float]], outcomes: Sequence[int]) -> float:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("Probabilities and outcomes must have the same non-zero length.")
    scores = []
    for row, outcome in zip(probabilities, outcomes):
        if outcome < 0 or outcome >= len(row):
            raise ValueError("Outcome index is outside the probability vector.")
        scores.append(sum((float(p) - (1.0 if i == outcome else 0.0)) ** 2 for i, p in enumerate(row)))
    return sum(scores) / len(scores)


def calibration_bins(
    predicted_probabilities: Iterable[float],
    actual_successes: Iterable[bool],
    bins: Sequence[tuple[float, float]] | None = None,
) -> list[CalibrationBin]:
    probs = [float(p) for p in predicted_probabilities]
    successes = [bool(s) for s in actual_successes]
    if len(probs) != len(successes):
        raise ValueError("Predicted probabilities and outcomes must have the same length.")
    if bins is None:
        bins = tuple((i / 100.0, (i + 5) / 100.0) for i in range(50, 100, 5))

    out: list[CalibrationBin] = []
    for lower, upper in bins:
        indexes = [i for i, p in enumerate(probs) if lower <= p < upper or (upper == 1.0 and p == 1.0)]
        if not indexes:
            out.append(CalibrationBin(lower, upper, 0, None, None, None))
            continue
        predicted_mean = sum(probs[i] for i in indexes) / len(indexes)
        actual_rate = sum(1.0 for i in indexes if successes[i]) / len(indexes)
        out.append(CalibrationBin(lower, upper, len(indexes), predicted_mean, actual_rate, actual_rate - predicted_mean))
    return out
