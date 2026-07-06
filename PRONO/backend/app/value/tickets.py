"""Boosted ticket evaluation built on independent event blocks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .blocks import EventBlock, independent_blocks_probability
from .ev import boosted_odds, ticket_ev


@dataclass(frozen=True)
class TicketEvaluation:
    raw_odds: float
    boost_rate: float
    boosted_odds: float
    probability: float
    ev: float


def evaluate_ticket(blocks: Sequence[EventBlock], boost_rate: float) -> TicketEvaluation:
    if not blocks:
        raise ValueError("A ticket requires at least one block.")
    raw_odds = 1.0
    for block in blocks:
        raw_odds *= block.combined_odds()
    boosted = boosted_odds(raw_odds, boost_rate)
    probability = independent_blocks_probability(blocks)
    return TicketEvaluation(
        raw_odds=raw_odds,
        boost_rate=boost_rate,
        boosted_odds=boosted,
        probability=probability,
        ev=ticket_ev(probability, boosted),
    )
