"""Odds conversion and no-vig probabilities."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

@dataclass(frozen=True)
class DevigResult:
    probabilities: tuple[float, ...]
    overround: float
    margin: float


def _as_valid_odds(odds: Iterable[float]) -> tuple[float, ...]:
    values = tuple(float(o) for o in odds)
    if not values:
        raise ValueError("At least one odd is required.")
    if any((not math.isfinite(o)) or o <= 1.0 for o in values):
        raise ValueError("Decimal odds must be finite values greater than 1.0.")
    return values


def implied_probability(decimal_odd: float) -> float:
    """Convert a decimal odd to its raw implied probability."""
    odd = _as_valid_odds([decimal_odd])[0]
    return 1.0 / odd


def devig_proportional(odds: Iterable[float]) -> DevigResult:
    """Remove bookmaker margin with proportional normalization.

    This works for 2-way, 3-way, or n-way mutually exclusive markets.
    """
    values = _as_valid_odds(odds)
    implied = tuple(1.0 / o for o in values)
    overround = sum(implied)
    if overround <= 0.0:
        raise ValueError("Overround must be positive.")
    probabilities = tuple(p / overround for p in implied)
    return DevigResult(probabilities=probabilities, overround=overround, margin=overround - 1.0)


