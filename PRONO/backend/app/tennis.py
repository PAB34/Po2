"""Donnees tennis pour PRONO.

Recupere un flux de matchs cotes, calcule une probabilite brute (Elo surface si
connu, sinon marche), puis applique la lentille coach: forme, H2H et fatigue
intra-tournoi. Les probabilites de sets sont derivees de la proba coach.
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from datetime import datetime

from app.tennis_brackets import build_brackets_from_matches
from app.tennis_coach import TennisCoach


FEED = "https://raw.githubusercontent.com/Mriganka-codes/tennis_data/main/matches.json"
LOW_LEVEL = re.compile(r"challenger|itf|utr|futures|davis cup|billie jean king", re.I)
CLAY = (
    "gstaad", "bastad", "kitzbuhel", "kitzbuehel", "hamburg", "umag", "cordenons",
    "monte carlo", "madrid", "rome", "roland", "french open", "barcelona",
    "munich", "estoril", "geneva", "lyon", "buenos aires", "rio",
    "santiago", "cordoba", "marrakech", "houston", "bucharest", "iasi",
    "palermo", "athens",
)
GRASS = (
    "wimbledon", "halle", "queens", "newport", "mallorca", "eastbourne",
    "stuttgart", "nottingham", "bad homburg",
)
_COACH: TennisCoach | None = None


def _coach() -> TennisCoach:
    global _COACH
    if _COACH is None:
        _COACH = TennisCoach()
    return _COACH


def _strip(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", str(value or ""))
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )


def _seedless(value: str) -> str:
    return re.sub(r"\s*\(\d+\)\s*$", "", str(value or "")).strip()


def _surface(tournament: str) -> str:
    normalized = _strip(tournament)
    if any(re.search(r"\b" + word + r"\b", normalized) for word in CLAY):
        return "Terre"
    if any(re.search(r"\b" + word + r"\b", normalized) for word in GRASS):
        return "Gazon"
    return "Dur"


def _set_probability(match_probability: float) -> float:
    lo, hi = 0.5, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if mid * mid * (3 - 2 * mid) < match_probability:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _market_probability(odds1: float, odds2: float) -> float:
    implied1, implied2 = 1 / odds1, 1 / odds2
    return implied1 / (implied1 + implied2)


def _round_pct(value: float) -> float:
    return round(value * 100, 1)


def _favorite_fields(match: dict, odds1: float, odds2: float, intel: dict) -> dict:
    p1 = intel["p1"]
    fav1 = p1 >= 0.5
    favorite_probability = p1 if fav1 else 1 - p1
    raw_fav = intel["raw_p1"] if fav1 else 1 - intel["raw_p1"]
    market_fav = intel["market_p1"] if fav1 else 1 - intel["market_p1"]
    set_probability = _set_probability(favorite_probability)
    favorite = match["player1"] if fav1 else match["player2"]
    favorite_odds = odds1 if fav1 else odds2
    cycle_fav = intel["cycle1"] if fav1 else intel["cycle2"]
    cycle_opp = intel["cycle2"] if fav1 else intel["cycle1"]
    return {
        "favori": _seedless(favorite),
        "proba": _round_pct(favorite_probability),
        "proba_brute": _round_pct(raw_fav),
        "proba_marche": _round_pct(market_fav),
        "ajustement": round((favorite_probability - raw_fav) * 100, 1),
        "cote": round(favorite_odds, 2),
        "p20": round(set_probability * set_probability * 100),
        "p21": round(2 * set_probability * set_probability * (1 - set_probability) * 100),
        "p3": round(2 * set_probability * (1 - set_probability) * 100),
        "cycle_favori": cycle_fav["label"],
        "fatigue_favori": cycle_fav["fatigue"],
        "cycle_adversaire": cycle_opp["label"],
        "fatigue_adversaire": cycle_opp["fatigue"],
    }


def _rows(matches: list[dict], tour: str) -> list[dict]:
    rows = []
    coach = _coach()
    for raw in matches:
        if raw.get("tour") != tour or not raw.get("odds1") or not raw.get("odds2"):
            continue
        if LOW_LEVEL.search(raw.get("tournament", "")):
            continue
        try:
            odds1, odds2 = float(raw["odds1"]), float(raw["odds2"])
        except (TypeError, ValueError):
            continue
        if odds1 <= 1 or odds2 <= 1:
            continue

        match = {
            "tournament": raw.get("tournament", ""),
            "time": raw.get("time", ""),
            "player1": _seedless(raw.get("player1")),
            "player2": _seedless(raw.get("player2")),
            "tour": tour,
            "surface": _surface(raw.get("tournament", "")),
        }
        market_p1 = _market_probability(odds1, odds2)
        intel = coach.enrich(match, market_p1)
        h2h = intel.get("h2h") or {}
        row = {
            "tournoi": match["tournament"],
            "heure": match["time"],
            "surface": match["surface"],
            "match": f"{match['player1']} vs {match['player2']}",
            "joueur1": match["player1"],
            "joueur2": match["player2"],
            "modele": intel.get("source"),
            "cycle1": intel["cycle1"]["label"],
            "cycle2": intel["cycle2"]["label"],
            "fatigue1": intel["cycle1"]["fatigue"],
            "fatigue2": intel["cycle2"]["fatigue"],
            "h2h": f"{h2h.get('wins1', 0)}-{h2h.get('wins2', 0)}",
            "alerte": h2h.get("alert"),
            "preuves": intel.get("proofs"),
        }
        row.update(_favorite_fields(match, odds1, odds2, intel))
        rows.append(row)
    rows.sort(key=lambda row: -row["proba"])
    return rows


def fetch_feed() -> dict:
    request = urllib.request.Request(FEED, headers={"User-Agent": "prono-tennis"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def build_tennis() -> dict:
    data = fetch_feed()
    matches = data.get("matches", [])
    return {
        "updated": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "feed_updated": data.get("last_updated", ""),
        "atp": _rows(matches, "ATP"),
        "wta": _rows(matches, "WTA"),
    }


def build_tennis_brackets() -> dict:
    data = fetch_feed()
    return build_brackets_from_matches(data.get("matches", []))