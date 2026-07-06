"""Bridge between PRONO Ligue 1 history and value backtests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from app.ligue1.config import ODDS_SOURCES
from app.ligue1.data import load_history

from .backtest import MarketBacktestResult, run_market_1x2_backtest


@dataclass(frozen=True)
class MarketSourceCoverage:
    source: str
    total_rows: int
    valid_rows: int
    coverage_rate: float
    columns: dict[str, str]


def source_coverage(history: pd.DataFrame, sources: Iterable[tuple[str, dict[str, str]]] = ODDS_SOURCES) -> tuple[MarketSourceCoverage, ...]:
    total = len(history)
    out: list[MarketSourceCoverage] = []
    for name, columns in sources:
        required = [columns["H"], columns["D"], columns["A"], "FTR"]
        if any(c not in history.columns for c in required):
            valid = 0
        else:
            odds = history[[columns["H"], columns["D"], columns["A"]]].apply(pd.to_numeric, errors="coerce")
            valid = int(((odds > 1.0).all(axis=1) & history["FTR"].isin(["H", "D", "A"])).sum())
        out.append(MarketSourceCoverage(
            source=name,
            total_rows=total,
            valid_rows=valid,
            coverage_rate=(valid / total) if total else 0.0,
            columns=dict(columns),
        ))
    return tuple(out)


def run_ligue1_market_backtests(history: pd.DataFrame | None = None) -> tuple[MarketBacktestResult, ...]:
    """Run closing-proxy 1X2 market backtests for configured odds sources.

    Football-Data historical rows do not provide odds snapshot timestamps, so
    returned results carry the warning emitted by `run_market_1x2_backtest`.
    """
    hist = load_history() if history is None else history
    results: list[MarketBacktestResult] = []
    for coverage in source_coverage(hist):
        if coverage.valid_rows == 0:
            continue
        results.append(run_market_1x2_backtest(hist, coverage.columns, source=coverage.source))
    return tuple(results)
