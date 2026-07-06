"""Normalize free/current odds sources into OddsSnapshot rows."""
from __future__ import annotations

import math
from typing import Iterable, Mapping

import pandas as pd

from .snapshots import OddsSnapshot, payload_hash


def _valid_odd(value: object) -> float | None:
    try:
        odd = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(odd) or odd <= 1.0:
        return None
    return odd


def _event_id(*parts: object) -> str:
    return "|".join(str(p).strip().lower() for p in parts if str(p or "").strip())


def snapshots_from_football_data_rows(
    rows: pd.DataFrame,
    captured_at: str,
    competition: str = "ligue1",
    source: str = "football-data-fixtures",
    bookmaker_columns: Mapping[str, Mapping[str, str]] | None = None,
) -> list[OddsSnapshot]:
    """Convert Football-Data fixture/history odds columns to snapshots.

    Football-Data rows do not expose bookmaker `last_update`; `captured_at` is
    therefore the time our app collected the file.
    """
    if bookmaker_columns is None:
        bookmaker_columns = {
            "Pinnacle": {"H": "PSH", "D": "PSD", "A": "PSA"},
            "Bet365": {"H": "B365H", "D": "B365D", "A": "B365A"},
            "MarketAverage": {"H": "AvgH", "D": "AvgD", "A": "AvgA"},
        }
    snapshots: list[OddsSnapshot] = []
    for _, row in rows.iterrows():
        home = str(row.get("HomeTeam", "")).strip()
        away = str(row.get("AwayTeam", "")).strip()
        kickoff = str(row.get("Kickoff", row.get("Date", ""))).strip()
        if not home or not away or not kickoff:
            continue
        event_id = _event_id("football", competition, kickoff, home, away)
        raw_hash = payload_hash({"source": source, "event_id": event_id, "row": row.to_dict()})
        for bookmaker, cols in bookmaker_columns.items():
            for outcome, selection in (("H", home), ("D", "Draw"), ("A", away)):
                odd = _valid_odd(row.get(cols.get(outcome, "")))
                if odd is None:
                    continue
                snapshots.append(OddsSnapshot(
                    sport="football",
                    competition=competition,
                    event_id=event_id,
                    participant_1=home,
                    participant_2=away,
                    market="1x2",
                    selection=selection,
                    bookmaker=bookmaker,
                    odd=odd,
                    captured_at=captured_at,
                    last_update=None,
                    commence_time=kickoff,
                    source=source,
                    raw_payload_hash=raw_hash,
                ))
    return snapshots


def snapshots_from_the_odds_api_events(
    events: Iterable[Mapping[str, object]],
    captured_at: str,
    sport: str,
    competition: str,
    source: str = "the-odds-api",
    allowed_markets: set[str] | None = None,
) -> list[OddsSnapshot]:
    """Convert The Odds API v4 event payloads to snapshots.

    Supports `h2h` for tennis and soccer-style head-to-head. For football 1X2,
    the draw outcome is preserved when present.
    """
    allowed = allowed_markets or {"h2h"}
    snapshots: list[OddsSnapshot] = []
    for event in events:
        event_id = str(event.get("id") or _event_id(source, event.get("commence_time"), event.get("home_team"), event.get("away_team")))
        home = str(event.get("home_team") or "").strip()
        away = str(event.get("away_team") or "").strip()
        commence_time = str(event.get("commence_time") or "").strip()
        if not home or not away or not commence_time:
            continue
        raw_hash = payload_hash(event)
        for bookmaker in event.get("bookmakers", []) or []:
            if not isinstance(bookmaker, Mapping):
                continue
            bookmaker_key = str(bookmaker.get("key") or bookmaker.get("title") or "unknown").strip()
            last_update = str(bookmaker.get("last_update") or "").strip() or None
            for market in bookmaker.get("markets", []) or []:
                if not isinstance(market, Mapping):
                    continue
                market_key = str(market.get("key") or "").strip()
                if market_key not in allowed:
                    continue
                normalized_market = "1x2" if sport == "football" and market_key == "h2h" else market_key
                for outcome in market.get("outcomes", []) or []:
                    if not isinstance(outcome, Mapping):
                        continue
                    odd = _valid_odd(outcome.get("price"))
                    selection = str(outcome.get("name") or "").strip()
                    if odd is None or not selection:
                        continue
                    snapshots.append(OddsSnapshot(
                        sport=sport,
                        competition=competition,
                        event_id=event_id,
                        participant_1=home,
                        participant_2=away,
                        market=normalized_market,
                        selection=selection,
                        bookmaker=bookmaker_key,
                        odd=odd,
                        captured_at=captured_at,
                        last_update=last_update,
                        commence_time=commence_time,
                        source=source,
                        raw_payload_hash=raw_hash,
                    ))
    return snapshots
