"""Boosted ticket backtest using historical 1X2 market probabilities.

This is a validation tool. It uses market no-vig probabilities as `p_final` and
therefore tests the ticket/boost mechanics before any personal model exists.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

import pandas as pd

from .boost import BoostSchedule, WINAMAX_LIKE_SCHEDULE
from .ev import boosted_odds, ticket_ev
from .odds import devig_proportional

OUTCOME_TO_INDEX = {"H": 0, "D": 1, "A": 2}
INDEX_TO_OUTCOME = {0: "H", 1: "D", 2: "A"}


@dataclass(frozen=True)
class BacktestSelection:
    event_id: str
    kickoff: str
    home: str
    away: str
    market: str
    outcome: str
    selection: str
    probability: float
    odd: float
    ev: float
    result: bool
    source: str


@dataclass(frozen=True)
class BoostedTicketRow:
    ticket_id: int
    selections: tuple[BacktestSelection, ...]
    raw_odds: float
    boost_rate: float
    boosted_odds: float
    probability: float
    estimated_ev: float
    won: bool
    stake: float
    profit: float
    cumulative_profit: float
    drawdown: float


@dataclass(frozen=True)
class BoostedTicketBacktestResult:
    source: str
    n_selections: int
    n_tickets: int
    selections_per_ticket: int
    stake: float
    total_staked: float
    total_profit: float
    roi: float
    hit_rate: float
    max_drawdown: float
    avg_estimated_ev: float | None
    tickets: tuple[BoostedTicketRow, ...]


def _valid_odd(value: object) -> float | None:
    try:
        odd = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(odd) or odd <= 1.0:
        return None
    return odd


def _event_id(row: pd.Series) -> str:
    return "|".join([
        str(row.get("Kickoff", "")).strip(),
        str(row.get("HomeTeam", "")).strip(),
        str(row.get("AwayTeam", "")).strip(),
    ])


def build_market_favorite_selections(
    matches: pd.DataFrame,
    odds_columns: Mapping[str, str],
    source: str,
    min_odd: float | None = None,
    max_odd: float | None = None,
    min_ev: float | None = None,
) -> tuple[BacktestSelection, ...]:
    """Build one favorite selection per historical match.

    `probability` is the no-vig market probability. `ev` is measured against the
    same bookmaker/source odd, so it will usually be negative before boosts.
    """
    required = ["Kickoff", "HomeTeam", "AwayTeam", "FTR", odds_columns["H"], odds_columns["D"], odds_columns["A"]]
    missing = [c for c in required if c not in matches.columns]
    if missing:
        raise ValueError(f"Missing selection column(s): {', '.join(missing)}")

    selections: list[BacktestSelection] = []
    ordered = matches.sort_values("Kickoff") if "Kickoff" in matches.columns else matches
    for _, row in ordered.iterrows():
        result = str(row.get("FTR", ""))
        if result not in OUTCOME_TO_INDEX:
            continue
        odds = [_valid_odd(row.get(odds_columns[outcome])) for outcome in ("H", "D", "A")]
        if any(odd is None for odd in odds):
            continue
        probabilities = devig_proportional(odds).probabilities  # type: ignore[arg-type]
        pick_index = max(range(3), key=lambda idx: probabilities[idx])
        outcome = INDEX_TO_OUTCOME[pick_index]
        odd = float(odds[pick_index])
        if min_odd is not None and odd < min_odd:
            continue
        if max_odd is not None and odd > max_odd:
            continue
        ev = probabilities[pick_index] * odd - 1.0
        if min_ev is not None and ev < min_ev:
            continue
        home = str(row["HomeTeam"])
        away = str(row["AwayTeam"])
        selection_name = home if outcome == "H" else away if outcome == "A" else "Draw"
        selections.append(BacktestSelection(
            event_id=_event_id(row),
            kickoff=str(row["Kickoff"]),
            home=home,
            away=away,
            market="1x2",
            outcome=outcome,
            selection=selection_name,
            probability=float(probabilities[pick_index]),
            odd=odd,
            ev=ev,
            result=(result == outcome),
            source=source,
        ))
    return tuple(selections)


def run_boosted_ticket_backtest(
    selections: Sequence[BacktestSelection],
    selections_per_ticket: int,
    stake: float = 50.0,
    boost_schedule: BoostSchedule = WINAMAX_LIKE_SCHEDULE,
    max_tickets: int | None = None,
) -> BoostedTicketBacktestResult:
    if selections_per_ticket <= 0:
        raise ValueError("selections_per_ticket must be positive.")
    if stake <= 0.0:
        raise ValueError("stake must be positive.")

    tickets: list[BoostedTicketRow] = []
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    ordered = list(selections)
    ticket_id = 1
    for start in range(0, len(ordered), selections_per_ticket):
        chunk = tuple(ordered[start:start + selections_per_ticket])
        if len(chunk) < selections_per_ticket:
            break
        if max_tickets is not None and len(tickets) >= max_tickets:
            break
        raw_odds = 1.0
        probability = 1.0
        for selection in chunk:
            raw_odds *= selection.odd
            probability *= selection.probability
        boost_rate = boost_schedule.rate_for(len(chunk))
        boosted = boosted_odds(raw_odds, boost_rate)
        estimated_ev = ticket_ev(probability, boosted)
        won = all(selection.result for selection in chunk)
        profit = stake * (boosted - 1.0) if won else -stake
        cumulative += profit
        peak = max(peak, cumulative)
        drawdown = peak - cumulative
        max_drawdown = max(max_drawdown, drawdown)
        tickets.append(BoostedTicketRow(
            ticket_id=ticket_id,
            selections=chunk,
            raw_odds=raw_odds,
            boost_rate=boost_rate,
            boosted_odds=boosted,
            probability=probability,
            estimated_ev=estimated_ev,
            won=won,
            stake=stake,
            profit=profit,
            cumulative_profit=cumulative,
            drawdown=drawdown,
        ))
        ticket_id += 1

    total_staked = stake * len(tickets)
    total_profit = sum(ticket.profit for ticket in tickets)
    avg_ev = (sum(ticket.estimated_ev for ticket in tickets) / len(tickets)) if tickets else None
    sources = sorted({selection.source for selection in selections})
    return BoostedTicketBacktestResult(
        source="+".join(sources) if sources else "unknown",
        n_selections=len(selections),
        n_tickets=len(tickets),
        selections_per_ticket=selections_per_ticket,
        stake=stake,
        total_staked=total_staked,
        total_profit=total_profit,
        roi=(total_profit / total_staked) if total_staked else 0.0,
        hit_rate=(sum(1 for ticket in tickets if ticket.won) / len(tickets)) if tickets else 0.0,
        max_drawdown=max_drawdown,
        avg_estimated_ev=avg_ev,
        tickets=tuple(tickets),
    )
