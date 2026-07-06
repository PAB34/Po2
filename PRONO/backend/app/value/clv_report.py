"""CLV reports computed from captured odds snapshots."""
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from collections import defaultdict
from typing import Iterable

from .clv import clv
from .snapshots import OddsSnapshot


@dataclass(frozen=True)
class SnapshotClvRow:
    event_id: str
    market: str
    selection: str
    bookmaker: str
    decision_odd: float
    closing_odd: float
    decision_captured_at: str
    closing_captured_at: str
    commence_time: str
    clv: float


@dataclass(frozen=True)
class SnapshotClvReport:
    decision_at: str
    rows: tuple[SnapshotClvRow, ...]
    skipped_groups: int


def _parse_time(value: str) -> dt.datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Timestamp is required.")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def build_snapshot_clv_report(snapshots: Iterable[OddsSnapshot], decision_at: str) -> SnapshotClvReport:
    """Compare the decision snapshot to the latest snapshot before kickoff.

    Group key is event/market/selection/bookmaker, because CLV must compare the
    same selection at the same bookmaker.
    """
    decision_time = _parse_time(decision_at)
    groups: dict[tuple[str, str, str, str], list[OddsSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        groups[(snapshot.event_id, snapshot.market, snapshot.selection, snapshot.bookmaker)].append(snapshot)

    rows: list[SnapshotClvRow] = []
    skipped = 0
    for (_event_id, _market, _selection, _bookmaker), items in groups.items():
        valid_items = []
        for item in items:
            try:
                captured = _parse_time(item.captured_at)
                commence = _parse_time(item.commence_time)
            except ValueError:
                continue
            valid_items.append((item, captured, commence))
        if not valid_items:
            skipped += 1
            continue

        decision_candidates = [(item, captured, commence) for item, captured, commence in valid_items if captured <= decision_time]
        if not decision_candidates:
            skipped += 1
            continue
        decision_snapshot, _, commence_time = max(decision_candidates, key=lambda x: x[1])

        closing_candidates = [
            (item, captured, commence)
            for item, captured, commence in valid_items
            if captured < commence and captured >= decision_time
        ]
        if not closing_candidates:
            closing_candidates = [(item, captured, commence) for item, captured, commence in valid_items if captured < commence]
        if not closing_candidates:
            skipped += 1
            continue
        closing_snapshot, _, _ = max(closing_candidates, key=lambda x: x[1])

        rows.append(SnapshotClvRow(
            event_id=decision_snapshot.event_id,
            market=decision_snapshot.market,
            selection=decision_snapshot.selection,
            bookmaker=decision_snapshot.bookmaker,
            decision_odd=decision_snapshot.odd,
            closing_odd=closing_snapshot.odd,
            decision_captured_at=decision_snapshot.captured_at,
            closing_captured_at=closing_snapshot.captured_at,
            commence_time=decision_snapshot.commence_time,
            clv=clv(decision_snapshot.odd, closing_snapshot.odd),
        ))

    rows.sort(key=lambda row: (row.event_id, row.market, row.selection, row.bookmaker))
    return SnapshotClvReport(decision_at=decision_at, rows=tuple(rows), skipped_groups=skipped)
