"""Betting-layer data completeness, kept separate from sports scenarios."""
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from typing import Sequence

from .snapshots import OddsSnapshot

MARKET_MIN_SELECTIONS = {
    "1x2": 3,
    "h2h": 2,
    "over_1_5": 2,
    "btts": 2,
}


@dataclass(frozen=True)
class BettingCompletenessAssessment:
    score: int
    status: str
    snapshot_count: int
    decision_snapshot_count: int
    closing_snapshot_count: int
    bookmaker_count: int
    available_markets: tuple[str, ...]
    required_markets: tuple[str, ...]
    missing_data: tuple[str, ...]
    blocking_missing_data: tuple[str, ...]
    degrading_missing_data: tuple[str, ...]


def assess_betting_completeness(
    snapshots: Sequence[OddsSnapshot],
    required_markets: Sequence[str] = ("1x2",),
    decision_at: str | None = None,
) -> BettingCompletenessAssessment:
    """Score betting data readiness without feeding odds into the scenario engine."""
    normalized_required = tuple(_normalize_market(market) for market in required_markets if str(market).strip()) or ("1x2",)
    available_markets = tuple(sorted({_normalize_market(snapshot.market) for snapshot in snapshots}))
    bookmaker_count = len({snapshot.bookmaker for snapshot in snapshots if snapshot.bookmaker.strip()})
    missing: list[str] = []
    blocking: list[str] = []
    degrading: list[str] = []
    score = 100

    if not snapshots:
        missing.append("snapshots")
        blocking.append("snapshots")
        return _assessment(0, 0, 0, 0, 0, (), normalized_required, missing, blocking, degrading)

    decision_time = _parse_time(decision_at)
    if decision_time is None:
        score -= 15
        missing.append("decision_at")
        blocking.append("decision_at")

    parsed_snapshots = [(snapshot, _parse_time(snapshot.captured_at), _parse_time(snapshot.commence_time)) for snapshot in snapshots]
    decision_snapshots = [snapshot for snapshot, captured_at, _ in parsed_snapshots if decision_time is not None and captured_at is not None and captured_at <= decision_time]
    if decision_time is not None and not decision_snapshots:
        score -= 20
        missing.append("snapshot_before_decision")
        blocking.append("snapshot_before_decision")

    missing_markets = [market for market in normalized_required if market not in available_markets]
    if missing_markets:
        penalty = round(25 * (len(missing_markets) / len(normalized_required)))
        score -= penalty
        for market in missing_markets:
            item = f"market:{market}"
            missing.append(item)
            blocking.append(item)

    thin_markets = _thin_markets(snapshots, normalized_required)
    if thin_markets:
        penalty = round(10 * (len(thin_markets) / len(normalized_required)))
        score -= penalty
        for market in thin_markets:
            item = f"selection_depth:{market}"
            missing.append(item)
            degrading.append(item)

    if bookmaker_count == 0:
        score -= 10
        missing.append("bookmakers")
        blocking.append("bookmakers")
    elif bookmaker_count == 1:
        score -= 5
        missing.append("bookmaker_diversity")
        degrading.append("bookmaker_diversity")

    closing_snapshots = [
        snapshot for snapshot, captured_at, commence_time in parsed_snapshots
        if captured_at is not None and commence_time is not None and captured_at <= commence_time
    ]
    if not closing_snapshots:
        score -= 10
        missing.append("closing_snapshot")
        degrading.append("closing_snapshot")

    audited = any(snapshot.raw_payload_hash for snapshot in snapshots)
    if not audited:
        score -= 5
        missing.append("raw_payload_hash")
        degrading.append("raw_payload_hash")

    return _assessment(
        score,
        len(snapshots),
        len(decision_snapshots),
        len(closing_snapshots),
        bookmaker_count,
        available_markets,
        normalized_required,
        missing,
        blocking,
        degrading,
    )


def _assessment(
    score: int,
    snapshot_count: int,
    decision_snapshot_count: int,
    closing_snapshot_count: int,
    bookmaker_count: int,
    available_markets: tuple[str, ...],
    required_markets: tuple[str, ...],
    missing: list[str],
    blocking: list[str],
    degrading: list[str],
) -> BettingCompletenessAssessment:
    bounded = max(0, min(100, score))
    status = "blocked" if blocking else "complete" if bounded >= 85 and not degrading else "degraded"
    return BettingCompletenessAssessment(
        score=bounded,
        status=status,
        snapshot_count=snapshot_count,
        decision_snapshot_count=decision_snapshot_count,
        closing_snapshot_count=closing_snapshot_count,
        bookmaker_count=bookmaker_count,
        available_markets=available_markets,
        required_markets=required_markets,
        missing_data=tuple(_dedupe(missing)),
        blocking_missing_data=tuple(_dedupe(blocking)),
        degrading_missing_data=tuple(_dedupe(degrading)),
    )


def _thin_markets(snapshots: Sequence[OddsSnapshot], required_markets: tuple[str, ...]) -> list[str]:
    thin = []
    for market in required_markets:
        selections = {snapshot.selection for snapshot in snapshots if _normalize_market(snapshot.market) == market}
        minimum = MARKET_MIN_SELECTIONS.get(market, 2)
        if selections and len(selections) < minimum:
            thin.append(market)
    return thin


def _parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = dt.datetime.fromisoformat(text.replace(" ", "T"))
        except ValueError:
            return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed


def _normalize_market(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("over_1.5", "over_1_5")


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out