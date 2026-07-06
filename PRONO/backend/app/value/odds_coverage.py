"""Coverage reporting for multi-bookmaker odds snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .betting_completeness import BettingCompletenessAssessment, assess_betting_completeness
from .snapshots import OddsSnapshot


@dataclass(frozen=True)
class OddsCoverageEvent:
    event_id: str
    sport: str
    competition: str
    participant_1: str
    participant_2: str
    commence_time: str
    snapshot_count: int
    bookmaker_count: int
    markets: tuple[str, ...]
    selections_by_market: dict[str, tuple[str, ...]]
    bookmakers_by_market: dict[str, tuple[str, ...]]
    first_captured_at: str | None
    last_captured_at: str | None
    completeness: BettingCompletenessAssessment


@dataclass(frozen=True)
class OddsCoverageReport:
    source: str
    event_count: int
    snapshot_count: int
    required_markets: tuple[str, ...]
    events: tuple[OddsCoverageEvent, ...]


def build_odds_coverage_report(
    snapshots: Sequence[OddsSnapshot],
    required_markets: Sequence[str] = ("1x2",),
    decision_at: str | None = None,
    source: str = "odds-snapshots",
) -> OddsCoverageReport:
    grouped: dict[str, list[OddsSnapshot]] = {}
    for snapshot in snapshots:
        grouped.setdefault(snapshot.event_id, []).append(snapshot)
    events = tuple(
        _build_event(event_id, rows, required_markets=required_markets, decision_at=decision_at)
        for event_id, rows in sorted(grouped.items())
    )
    return OddsCoverageReport(
        source=source,
        event_count=len(events),
        snapshot_count=len(snapshots),
        required_markets=tuple(required_markets),
        events=events,
    )


def _build_event(
    event_id: str,
    snapshots: Sequence[OddsSnapshot],
    required_markets: Sequence[str],
    decision_at: str | None,
) -> OddsCoverageEvent:
    first = snapshots[0]
    markets = tuple(sorted({snapshot.market for snapshot in snapshots}))
    captured = sorted(snapshot.captured_at for snapshot in snapshots if snapshot.captured_at)
    selections_by_market = {
        market: tuple(sorted({snapshot.selection for snapshot in snapshots if snapshot.market == market}))
        for market in markets
    }
    bookmakers_by_market = {
        market: tuple(sorted({snapshot.bookmaker for snapshot in snapshots if snapshot.market == market}))
        for market in markets
    }
    return OddsCoverageEvent(
        event_id=event_id,
        sport=first.sport,
        competition=first.competition,
        participant_1=first.participant_1,
        participant_2=first.participant_2,
        commence_time=first.commence_time,
        snapshot_count=len(snapshots),
        bookmaker_count=len({snapshot.bookmaker for snapshot in snapshots}),
        markets=markets,
        selections_by_market=selections_by_market,
        bookmakers_by_market=bookmakers_by_market,
        first_captured_at=captured[0] if captured else None,
        last_captured_at=captured[-1] if captured else None,
        completeness=assess_betting_completeness(
            snapshots,
            required_markets=required_markets,
            decision_at=decision_at,
        ),
    )