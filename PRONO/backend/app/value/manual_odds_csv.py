"""Manual bookmaker CSV normalization into odds snapshots.

This is intentionally generic: Winamax can be one bookmaker value, but the
pipeline should also accept other manually exported/free bookmaker rows.
"""
from __future__ import annotations

import csv
from io import StringIO
from typing import Mapping

from .collectors import _valid_odd
from .snapshots import OddsSnapshot, payload_hash


COLUMN_ALIASES = {
    "sport": ("sport",),
    "competition": ("competition", "league", "competition_key"),
    "event_id": ("event_id", "event", "match_id"),
    "participant_1": ("participant_1", "home", "home_team", "team1"),
    "participant_2": ("participant_2", "away", "away_team", "team2"),
    "market": ("market", "market_key"),
    "selection": ("selection", "outcome", "pick"),
    "bookmaker": ("bookmaker", "book", "operator"),
    "odd": ("odd", "odds", "price", "cote"),
    "captured_at": ("captured_at", "captured", "snapshot_at"),
    "commence_time": ("commence_time", "kickoff", "start_time", "match_time"),
    "last_update": ("last_update", "updated_at"),
}


def snapshots_from_manual_csv(
    csv_text: str,
    captured_at: str,
    default_bookmaker: str = "manual",
    default_sport: str = "football",
    default_competition: str = "ligue1",
    source: str = "manual-csv",
) -> list[OddsSnapshot]:
    rows = list(csv.DictReader(StringIO(csv_text.strip())))
    snapshots: list[OddsSnapshot] = []
    for row in rows:
        normalized = {_normalize_key(key): value for key, value in row.items()}
        sport = _value(normalized, "sport") or default_sport
        competition = _value(normalized, "competition") or default_competition
        participant_1 = _value(normalized, "participant_1")
        participant_2 = _value(normalized, "participant_2")
        market = _normalize_market(_value(normalized, "market") or "1x2")
        selection = _value(normalized, "selection")
        bookmaker = _value(normalized, "bookmaker") or default_bookmaker
        odd = _valid_odd(_value(normalized, "odd"))
        commence_time = _value(normalized, "commence_time")
        row_captured_at = _value(normalized, "captured_at") or captured_at
        last_update = _value(normalized, "last_update")
        if not participant_1 or not participant_2 or not selection or odd is None or not commence_time:
            continue
        event_id = _value(normalized, "event_id") or _event_id(source, sport, competition, commence_time, participant_1, participant_2)
        snapshots.append(OddsSnapshot(
            sport=sport,
            competition=competition,
            event_id=event_id,
            participant_1=participant_1,
            participant_2=participant_2,
            market=market,
            selection=_normalize_selection(selection, participant_1, participant_2),
            bookmaker=bookmaker,
            odd=odd,
            captured_at=row_captured_at,
            last_update=last_update,
            commence_time=commence_time,
            source=source,
            raw_payload_hash=payload_hash({"source": source, "row": row}),
        ))
    return snapshots


def _value(row: Mapping[str, object], canonical: str) -> str | None:
    for alias in COLUMN_ALIASES[canonical]:
        value = row.get(alias)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _event_id(*parts: object) -> str:
    return "|".join(str(part).strip().lower() for part in parts if str(part or "").strip())


def _normalize_key(key: object) -> str:
    return str(key or "").strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_market(value: str) -> str:
    market = value.strip().lower().replace(" ", "_").replace("over_1.5", "over_1_5")
    if market in {"h2h", "1n2", "1x2"}:
        return "1x2" if market == "1n2" else market
    return market


def _normalize_selection(selection: str, participant_1: str, participant_2: str) -> str:
    text = selection.strip()
    lowered = text.lower()
    if lowered in {"draw", "nul", "n"}:
        return "Draw"
    if lowered in {"home", "1", "h"}:
        return participant_1
    if lowered in {"away", "2", "a"}:
        return participant_2
    return text