"""Event blocks and correlation guards for ticket evaluation."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class Selection:
    event_id: str
    market: str
    name: str
    probability: float
    odd: float


@dataclass(frozen=True)
class EventBlock:
    event_id: str
    selections: tuple[Selection, ...]
    joint_probability: float | None = None

    @classmethod
    def from_selections(
        cls,
        selections: Sequence[Selection],
        joint_probability: float | None = None,
    ) -> "EventBlock":
        if not selections:
            raise ValueError("An event block requires at least one selection.")
        event_ids = {s.event_id for s in selections}
        if len(event_ids) != 1:
            raise ValueError("All selections in an event block must share the same event_id.")
        return cls(event_id=selections[0].event_id, selections=tuple(selections), joint_probability=joint_probability)

    def probability(self) -> float:
        if len(self.selections) == 1:
            return _valid_probability(self.selections[0].probability)
        if self.joint_probability is None:
            raise ValueError(
                "Correlated selections from the same event require an explicit joint probability."
            )
        return _valid_probability(self.joint_probability)

    def combined_odds(self) -> float:
        odd = 1.0
        for selection in self.selections:
            odd *= _valid_odd(selection.odd)
        return odd


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


def independent_blocks_probability(blocks: Sequence[EventBlock]) -> float:
    """Multiply probabilities across independent event blocks only."""
    seen = set()
    probability = 1.0
    for block in blocks:
        if block.event_id in seen:
            raise ValueError("Each event must appear in a single block before ticket aggregation.")
        seen.add(block.event_id)
        probability *= block.probability()
    return probability
