"""Confirmed product parameters for PRONO value simulations."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationDefaults:
    sports: tuple[str, ...]
    markets: tuple[str, ...]
    session_ticket_count: int
    stake_eur: float
    boost_model: str


DEFAULT_SIMULATION = SimulationDefaults(
    sports=("football_ligue1", "tennis"),
    markets=("1x2", "h2h"),
    session_ticket_count=10,
    stake_eur=50.0,
    boost_model="winamax_like_configurable",
)
