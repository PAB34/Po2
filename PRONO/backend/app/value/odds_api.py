"""The Odds API client for free/current snapshot collection.

Historical odds are not part of the free plan. This client is only for collecting
current/upcoming odds into our own timestamped store.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.the-odds-api.com/v4"


class OddsApiNotConfigured(RuntimeError):
    """Raised when PRONO_ODDS_API_KEY is missing."""


@dataclass(frozen=True)
class OddsApiRequest:
    sport_key: str
    regions: str = "eu"
    markets: str = "h2h"
    odds_format: str = "decimal"
    date_format: str = "iso"
    bookmakers: str | None = None


def api_key_from_env() -> str:
    return os.environ.get("PRONO_ODDS_API_KEY", "").strip()


def build_odds_url(request: OddsApiRequest, api_key: str) -> str:
    if not request.sport_key.strip():
        raise ValueError("sport_key is required.")
    if not api_key.strip():
        raise OddsApiNotConfigured("PRONO_ODDS_API_KEY is required to call The Odds API.")
    params: dict[str, str] = {
        "apiKey": api_key.strip(),
        "regions": request.regions,
        "markets": request.markets,
        "oddsFormat": request.odds_format,
        "dateFormat": request.date_format,
    }
    if request.bookmakers:
        params["bookmakers"] = request.bookmakers
    return f"{BASE_URL}/sports/{request.sport_key.strip()}/odds/?{urlencode(params)}"


def fetch_odds_events(request: OddsApiRequest, api_key: str | None = None, timeout: int = 20) -> list[dict[str, Any]]:
    key = api_key if api_key is not None else api_key_from_env()
    url = build_odds_url(request, key)
    req = Request(url, headers={"User-Agent": "PRONO/1.0"})
    with urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Unexpected The Odds API payload: expected a list of events.")
    return payload
