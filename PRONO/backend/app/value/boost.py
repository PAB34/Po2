"""Boost schedules for simulated combined tickets.

The live Winamax boost grid must be kept configurable because public promotion
rules can change and are not a stable statistical input. The default schedule is
therefore explicit and can be replaced from settings or a captured rule sheet.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


# Conservative placeholder for a Winamax-like variable boost by number of legs.
# Replace this mapping when the current official grid is captured/confirmed.
DEFAULT_WINAMAX_LIKE_BOOSTS = MappingProxyType({
    2: 0.02,
    3: 0.05,
    4: 0.10,
    5: 0.15,
    6: 0.20,
    7: 0.25,
    8: 0.30,
    9: 0.35,
    10: 0.40,
})


@dataclass(frozen=True)
class BoostSchedule:
    name: str
    rates_by_selection_count: Mapping[int, float]
    max_selection_count: int = 10

    def rate_for(self, selection_count: int) -> float:
        if selection_count <= 0:
            raise ValueError("Selection count must be positive.")
        if selection_count > self.max_selection_count:
            raise ValueError("Selection count exceeds the configured session/ticket limit.")
        eligible_counts = [count for count in self.rates_by_selection_count if count <= selection_count]
        if not eligible_counts:
            return 0.0
        rate = float(self.rates_by_selection_count[max(eligible_counts)])
        if rate < 0.0:
            raise ValueError("Boost rates must be positive.")
        return rate


WINAMAX_LIKE_SCHEDULE = BoostSchedule(
    name="winamax_like_configurable",
    rates_by_selection_count=DEFAULT_WINAMAX_LIKE_BOOSTS,
    max_selection_count=10,
)
