"""Donnees tennis pour PRONO.

Le scoreboard ATP/WTA est la source de verite des confrontations a venir. Le
flux de cotes reste utile seulement s'il porte exactement les deux memes joueurs;
sinon le match est affiche sans cote pour eviter les affiches de tour precedent.
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.tennis_brackets import build_brackets_from_matches
from app.tennis_coach import TennisCoach


FEED = "https://raw.githubusercontent.com/Mriganka-codes/tennis_data/main/matches.json"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/tennis/{league}/scoreboard?region=us&lang=en&dates={dates}&limit=1000"
LOW_LEVEL = re.compile(r"challenger|itf|utr|futures|davis cup|billie jean king", re.I)
CLAY = (
    "gstaad", "bastad", "nordea", "swedish open", "efg swiss", "kitzbuhel", "kitzbuehel", "generali open", "hamburg", "umag", "plava laguna", "cordenons",
    "monte carlo", "madrid", "rome", "roland", "french open", "barcelona",
    "munich", "estoril", "geneva", "lyon", "buenos aires", "rio",
    "santiago", "cordoba", "marrakech", "houston", "bucharest", "iasi",
    "palermo", "athens",
)
GRASS = (
    "wimbledon", "halle", "queens", "newport", "mallorca", "eastbourne",
    "stuttgart", "nottingham", "bad homburg",
)
PARIS_TZ = ZoneInfo("Europe/Paris")
PAST_MATCH_GRACE = timedelta(minutes=30)
FUTURE_MATCH_HORIZON = timedelta(days=4)
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


def _norm_words(value: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", _strip(_seedless(value))).split()


def _seedless(value: str) -> str:
    return re.sub(r"\s*\(\d+\)\s*$", "", str(value or "")).strip()


def _surface(tournament: str) -> str:
    normalized = _strip(tournament)
    if any(re.search(r"\b" + word + r"\b", normalized) for word in CLAY):
        return "Terre"
    if any(re.search(r"\b" + word + r"\b", normalized) for word in GRASS):
        return "Gazon"
    return "Dur"


def _now_paris() -> datetime:
    return datetime.now(PARIS_TZ)


def _parse_feed_updated(value: str | None) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = _now_paris()
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=PARIS_TZ)
    return parsed.astimezone(PARIS_TZ)


def _parse_match_clock(value: str | None) -> time | None:
    match = re.search(r"(\d{1,2})[:h](\d{2})", str(value or ""))
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute, tzinfo=PARIS_TZ)


def _infer_kickoff(raw: dict, feed_updated: datetime) -> datetime | None:
    if raw.get("kickoff"):
        parsed = _parse_feed_updated(raw.get("kickoff"))
        return parsed
    clock = _parse_match_clock(raw.get("time"))
    if not clock:
        return None
    kickoff = datetime.combine(feed_updated.date(), clock, tzinfo=PARIS_TZ)
    if kickoff < feed_updated - timedelta(hours=2):
        kickoff += timedelta(days=1)
    return kickoff


def _date_label(kickoff: datetime, now: datetime) -> str:
    delta = (kickoff.date() - now.date()).days
    if delta == 0:
        return "Aujourd'hui"
    if delta == 1:
        return "Demain"
    if delta == -1:
        return "Hier"
    return kickoff.strftime("%d/%m")


def _match_timing(raw: dict, feed_updated: datetime, now: datetime) -> dict:
    kickoff = _infer_kickoff(raw, feed_updated)
    if not kickoff:
        return {"kickoff": None, "past": False, "too_far": False, "display": raw.get("time", ""), "label": ""}
    past = kickoff < now - PAST_MATCH_GRACE
    too_far = kickoff > now + FUTURE_MATCH_HORIZON
    label = _date_label(kickoff, now)
    return {
        "kickoff": kickoff,
        "past": past,
        "too_far": too_far,
        "display": f"{label} {kickoff.strftime('%H:%M')}",
        "label": label,
    }


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


def _valid_odds(odds1, odds2) -> tuple[float | None, float | None]:
    try:
        left, right = float(odds1), float(odds2)
    except (TypeError, ValueError):
        return None, None
    if left <= 1 or right <= 1:
        return None, None
    return left, right


def _favorite_fields(match: dict, odds1: float | None, odds2: float | None, intel: dict) -> dict:
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
        "cote": round(favorite_odds, 2) if favorite_odds else None,
        "p20": round(set_probability * set_probability * 100),
        "p21": round(2 * set_probability * set_probability * (1 - set_probability) * 100),
        "p3": round(2 * set_probability * (1 - set_probability) * 100),
        "cycle_favori": cycle_fav["label"],
        "fatigue_favori": cycle_fav["fatigue"],
        "cycle_adversaire": cycle_opp["label"],
        "fatigue_adversaire": cycle_opp["fatigue"],
    }


def _player_signature(name: str) -> str:
    words = _norm_words(name)
    if not words:
        return ""
    if len(words) == 1:
        return words[0]
    return f"{words[-1]}:{words[0][0]}"


def _player_pair_key(player1: str, player2: str) -> frozenset[str]:
    return frozenset(sig for sig in (_player_signature(player1), _player_signature(player2)) if sig)


def _odds_index(matches: list[dict]) -> dict[tuple[str, frozenset[str]], list[dict]]:
    index: dict[tuple[str, frozenset[str]], list[dict]] = {}
    for raw in matches:
        odds1, odds2 = _valid_odds(raw.get("odds1"), raw.get("odds2"))
        if not odds1 or not odds2:
            continue
        key = (str(raw.get("tour") or "").upper(), _player_pair_key(raw.get("player1", ""), raw.get("player2", "")))
        if len(key[1]) != 2:
            continue
        index.setdefault(key, []).append(raw)
    return index


def _attach_odds(scoreboard: list[dict], odds_matches: list[dict]) -> list[dict]:
    indexed = _odds_index(odds_matches)
    out = []
    for match in scoreboard:
        item = dict(match)
        key = (str(item.get("tour") or "").upper(), _player_pair_key(item.get("player1", ""), item.get("player2", "")))
        candidates = indexed.get(key) or []
        if candidates:
            candidate = candidates[0]
            odds1, odds2 = _valid_odds(candidate.get("odds1"), candidate.get("odds2"))
            c1 = _player_signature(candidate.get("player1", ""))
            s1 = _player_signature(item.get("player1", ""))
            if c1 == s1:
                item.update({"odds1": odds1, "odds2": odds2, "odds_source": "market-feed"})
            else:
                item.update({"odds1": odds2, "odds2": odds1, "odds_source": "market-feed"})
        out.append(item)
    return out


def _competitor_name(competitor: dict) -> str:
    athlete = competitor.get("athlete") or {}
    return str(athlete.get("displayName") or athlete.get("name") or competitor.get("displayName") or "").strip()


def _parse_espn_date(value: str | None) -> datetime | None:
    text = str(value or "").replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=PARIS_TZ)
    return parsed.astimezone(PARIS_TZ)


def _fetch_espn_scoreboard(league: str, dates: str) -> dict:
    url = ESPN_SCOREBOARD.format(league=league, dates=dates)
    request = urllib.request.Request(url, headers={"User-Agent": "prono-tennis"})
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_scoreboard_matches(now: datetime | None = None) -> list[dict]:
    now = now or _now_paris()
    start = now.strftime("%Y%m%d")
    end = (now + FUTURE_MATCH_HORIZON).strftime("%Y%m%d")
    dates = f"{start}-{end}"
    rows = []
    wanted = {"ATP": "Men's Singles", "WTA": "Women's Singles"}
    for league, tour in (("atp", "ATP"), ("wta", "WTA")):
        data = _fetch_espn_scoreboard(league, dates)
        for event in data.get("events", []):
            tournament = event.get("name") or event.get("shortName") or ""
            if LOW_LEVEL.search(tournament):
                continue
            for grouping in event.get("groupings", []):
                grouping_name = ((grouping.get("grouping") or {}).get("displayName") or "").strip()
                if grouping_name != wanted[tour]:
                    continue
                for competition in grouping.get("competitions", []):
                    status = ((competition.get("status") or {}).get("type") or {})
                    if status.get("state") == "post" or status.get("completed"):
                        continue
                    kickoff = _parse_espn_date(competition.get("startDate") or competition.get("date"))
                    if not kickoff or kickoff < now - PAST_MATCH_GRACE or kickoff > now + FUTURE_MATCH_HORIZON:
                        continue
                    names = [_competitor_name(c) for c in competition.get("competitors", [])]
                    names = [name for name in names if name]
                    if len(names) != 2 or any(_strip(name) in {"tbd", "bye"} for name in names):
                        continue
                    rows.append({
                        "tour": tour,
                        "tournament": tournament,
                        "time": kickoff.isoformat(),
                        "kickoff": kickoff.isoformat(),
                        "player1": names[0],
                        "player2": names[1],
                        "source": "ESPN",
                    })
    seen = set()
    unique = []
    for row in sorted(rows, key=lambda r: (r["kickoff"], r["tour"], r["tournament"], r["player1"], r["player2"])):
        key = (row["tour"], row["kickoff"], _player_pair_key(row["player1"], row["player2"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _rows(matches: list[dict], tour: str, feed_updated: datetime, now: datetime) -> tuple[list[dict], int]:
    rows = []
    filtered_past = 0
    coach = _coach()
    for raw in matches:
        if raw.get("tour") != tour:
            continue
        if LOW_LEVEL.search(raw.get("tournament", "")):
            continue
        timing = _match_timing(raw, feed_updated, now)
        if timing["past"] or timing["too_far"]:
            filtered_past += 1
            continue
        odds1, odds2 = _valid_odds(raw.get("odds1"), raw.get("odds2"))

        match = {
            "tournament": raw.get("tournament", ""),
            "time": timing["display"],
            "player1": _seedless(raw.get("player1")),
            "player2": _seedless(raw.get("player2")),
            "tour": tour,
            "surface": _surface(raw.get("tournament", "")),
        }
        market_p1 = _market_probability(odds1, odds2) if odds1 and odds2 else 0.5
        intel = coach.enrich(match, market_p1)
        h2h = intel.get("h2h") or {}
        row = {
            "tournoi": match["tournament"],
            "heure": match["time"],
            "kickoff": timing["kickoff"].isoformat() if timing["kickoff"] else None,
            "date_label": timing["label"],
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
            "external_sources": intel.get("external_sources", []),
            "match_source": raw.get("source") or "market-feed",
            "odds_source": raw.get("odds_source") or None,
            "odds_status": "ok" if odds1 and odds2 else "indisponibles",
        }
        row.update(_favorite_fields(match, odds1, odds2, intel))
        rows.append(row)
    rows.sort(key=lambda row: (row.get("kickoff") or "9999", row["tournoi"], -row["proba"]))
    return rows, filtered_past


def _upcoming_matches(matches: list[dict], feed_updated: datetime, now: datetime) -> list[dict]:
    upcoming = []
    for raw in matches:
        timing = _match_timing(raw, feed_updated, now)
        if timing["past"] or timing["too_far"]:
            continue
        upcoming.append(raw)
    return upcoming


def fetch_feed() -> dict:
    request = urllib.request.Request(FEED, headers={"User-Agent": "prono-tennis"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def build_tennis() -> dict:
    data = fetch_feed()
    odds_matches = data.get("matches", [])
    now = _now_paris()
    feed_updated = _parse_feed_updated(data.get("last_updated"))
    try:
        scoreboard_matches = fetch_scoreboard_matches(now)
    except Exception:
        scoreboard_matches = []
    matches = _attach_odds(scoreboard_matches, odds_matches) if scoreboard_matches else odds_matches
    atp, atp_filtered = _rows(matches, "ATP", feed_updated, now)
    wta, wta_filtered = _rows(matches, "WTA", feed_updated, now)
    external_sources = sorted({source for row in atp + wta for source in row.get("external_sources", [])})
    return {
        "updated": now.strftime("%d/%m/%Y %H:%M"),
        "feed_updated": data.get("last_updated", ""),
        "feed_age_hours": round((now - feed_updated).total_seconds() / 3600, 1),
        "scoreboard_source": "ESPN" if scoreboard_matches else "market-feed-fallback",
        "scoreboard_count": len(scoreboard_matches),
        "filtered_past": atp_filtered + wta_filtered,
        "time_policy": "Confrontations a venir: scoreboard ESPN ATP/WTA; cotes rattachees seulement sur le meme duo de joueurs.",
        "external_sources": external_sources,
        "atp": atp,
        "wta": wta,
    }


def build_tennis_brackets() -> dict:
    data = fetch_feed()
    now = _now_paris()
    feed_updated = _parse_feed_updated(data.get("last_updated"))
    try:
        matches = fetch_scoreboard_matches(now)
    except Exception:
        matches = _upcoming_matches(data.get("matches", []), feed_updated, now)
    return build_brackets_from_matches(matches)