"""Expected value helpers for selections and boosted tickets."""
from __future__ import annotations

import math


def _valid_probability(probability: float) -> float:
    p = float(probability)
    if not math.isfinite(p) or p < 0.0 or p > 1.0:
        raise ValueError("Probability must be between 0 and 1.")
    return p


def _valid_odd(decimal_odd: float) -> float:
    odd = float(decimal_odd)
    if not math.isfinite(odd) or odd <= 1.0:
        raise ValueError("Decimal odd must be a finite value greater than 1.0.")
    return odd


def fair_odds(probability: float) -> float:
    p = _valid_probability(probability)
    if p == 0.0:
        return math.inf
    return 1.0 / p


def selection_ev(probability: float, decimal_odd: float) -> float:
    return _valid_probability(probability) * _valid_odd(decimal_odd) - 1.0


def boosted_odds(raw_decimal_odd: float, boost_rate: float) -> float:
    odd = _valid_odd(raw_decimal_odd)
    boost = float(boost_rate)
    if not math.isfinite(boost) or boost < 0.0:
        raise ValueError("Boost rate must be a finite positive value.")
    return odd * (1.0 + boost)


def break_even_probability(decimal_odd: float) -> float:
    return 1.0 / _valid_odd(decimal_odd)


def ticket_ev(ticket_probability: float, boosted_decimal_odd: float) -> float:
    return _valid_probability(ticket_probability) * _valid_odd(boosted_decimal_odd) - 1.0
