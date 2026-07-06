"""Closing line value helpers."""
from __future__ import annotations

import math


def clv(taken_odd: float, closing_odd: float) -> float:
    taken = float(taken_odd)
    closing = float(closing_odd)
    if not math.isfinite(taken) or not math.isfinite(closing) or taken <= 1.0 or closing <= 1.0:
        raise ValueError("Taken and closing odds must be finite values greater than 1.0.")
    return taken / closing - 1.0
