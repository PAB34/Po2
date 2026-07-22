"""Tournament bracket sources for the PRONO tennis view.

ESPN blocks some server IPs with HTTP 403, including the current VPS. The
production path therefore uses TennisDB for ATP draws and the official WTA JSON
API for WTA draws, while keeping ESPN helpers available as a last-resort source.
"""
from __future__ import annotations

import html
import json
import re
import time
import unicodedata
import urllib.request
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

YEAR = datetime.now().year
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

TENNISDB_BASE = "https://tennis-db.com"
WTA_DRAW_API = "https://api.wtatennis.com/tennis/tournaments/{tournament_id}/{year}/draw"

ATP_SCHEDULE = "https://espndeportes.espn.com/tenis/schedule"
WTA_SCHEDULE = "https://www.espn.com/tennis/schedule/_/type/wta"
ESPN_BRACKET = "https://m.espn.com/general/tennis/bracket?id={event_id}&matchType={match_type}&src=desktop&year={year}"

LOW_LEVEL = re.compile(r"challenger|itf|utr|futures|davis cup|billie jean king", re.I)

TENNISDB_ATP_EVENTS = [
    {
        "tour": "ATP",
        "source_kind": "tennisdb",
        "name": "EFG Swiss Open Gstaad",
        "location": "Gstaad, Switzerland",
        "path": "/tournaments/257/efg-swiss-open-gstaad?view=draw",
    },
    {
        "tour": "ATP",
        "source_kind": "tennisdb",
        "name": "Nordea Open",
        "location": "Bastad, Sweden",
        "path": "/tournaments/258/nordea-open?view=draw",
    },
    {
        "tour": "ATP",
        "source_kind": "tennisdb",
        "name": "Plava Laguna Croatia Open Umag",
        "location": "Umag, Croatia",
        "path": "/tournaments/259/plava-laguna-croatia-open-umag?view=draw",
    },
]

WTA_EVENTS = [
    {
        "tour": "WTA",
        "source_kind": "wta",
        "name": "Unicredit Iasi Open",
        "location": "Iasi, Romania",
        "tournament_id": "2063",
    },
    {
        "tour": "WTA",
        "source_kind": "wta",
        "name": "Vanda Pharmaceuticals Athens Open",
        "location": "Athens, Greece",
        "tournament_id": "1175",
    },
    {
        "tour": "WTA",
        "source_kind": "wta",
        "name": "Generali Open Ladies Kitzbuhel",
        "location": "Kitzbuhel, Austria",
        "tournament_id": "1162",
    },
    {
        "tour": "WTA",
        "source_kind": "wta",
        "name": "ATV Bancomat Tennis Open",
        "location": "Rome, Italy",
        "tournament_id": "1130",
    },
]

ESPN_FALLBACK_EVENTS = [
    {"tour": "ATP", "source_kind": "espn", "event_id": "7", "match_type": 1, "year": YEAR, "name": "EFG Swiss Open Gstaad", "location": "Gstaad, Switzerland"},
    {"tour": "ATP", "source_kind": "espn", "event_id": "306", "match_type": 1, "year": YEAR, "name": "Nordea Open", "location": "Bastad, Sweden"},
    {"tour": "ATP", "source_kind": "espn", "event_id": "22", "match_type": 1, "year": YEAR, "name": "Plava Laguna Croatia Open Umag", "location": "Umag, Croatia"},
    {"tour": "WTA", "source_kind": "espn", "event_id": "874", "match_type": 2, "year": YEAR, "name": "Unicredit Iasi Open", "location": "Iasi, Romania"},
    {"tour": "WTA", "source_kind": "espn", "event_id": "1069", "match_type": 2, "year": YEAR, "name": "Vanda Pharmaceuticals Athens Open", "location": "Athens, Greece"},
    {"tour": "WTA", "source_kind": "espn", "event_id": "1072", "match_type": 2, "year": YEAR, "name": "Generali Open Ladies Kitzbuhel", "location": "Kitzbuhel, Austria"},
    {"tour": "WTA", "source_kind": "espn", "event_id": "1017", "match_type": 2, "year": YEAR, "name": "ATV Bancomat Tennis Open", "location": "Rome, Italy"},
]

DROP_WORDS = {
    "atp", "wta", "open", "ladies", "men", "women", "tennis", "pharmaceuticals",
    "presented", "classic", "championships", "generali", "bancomat", "unicredit",
    "plava", "laguna", "croatia", "swiss", "efg", "nordea", "vanda",
}

WTA_ROUNDS = {
    7: "Round of 128",
    6: "Round of 64",
    5: "Round of 32",
    4: "Round of 16",
    3: "Quarterfinals",
    2: "Semifinals",
    1: "Final",
}


def norm(value: Any) -> str:
    return " ".join(
        unicodedata.normalize("NFKD", str(value or ""))
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .replace("&", " ")
        .replace("-", " ")
        .replace(".", " ")
        .split()
    )


def _tokens(value: Any) -> set[str]:
    return {t for t in norm(value).split() if len(t) >= 3 and t not in DROP_WORDS}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _clean(value: Any) -> str:
    return html.unescape(" ".join(str(value or "").split()))


def _get(url: str, accept: str = "text/html") -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=35) as resp:
        raw = resp.read()
    return raw.decode("utf-8", "replace")


def _schedule_events(url: str, tour: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(_get(url), "html.parser")
    events = []
    seen = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        m = re.search(r"(?:eventId|idEvento)/(\d+)-(\d{4})/(?:competitionType|tipo)/(\d+)", href)
        if not m:
            continue
        event_id, year, match_type = m.groups()
        if int(year) != YEAR:
            continue
        row = link.find_parent("tr") or link.parent
        name_el = link.select_one(".eventAndLocation__tournamentLink") or link.find("p")
        loc_el = row.select_one(".eventAndLocation__tournamentLocation") if row else None
        name = name_el.get_text(" ", strip=True) if name_el else link.get_text(" ", strip=True)
        location = loc_el.get_text(" ", strip=True) if loc_el else ""
        key = (tour, event_id, match_type)
        if key in seen or not name:
            continue
        seen.add(key)
        events.append({
            "tour": tour,
            "source_kind": "espn",
            "event_id": event_id,
            "match_type": int(match_type),
            "year": int(year),
            "name": html.unescape(name),
            "location": html.unescape(location),
        })
    return events


def discover_espn_events() -> list[dict[str, Any]]:
    events = []
    for url, tour in ((ATP_SCHEDULE, "ATP"), (WTA_SCHEDULE, "WTA")):
        try:
            events.extend(_schedule_events(url, tour))
        except Exception:
            pass
    known = {(e["tour"], str(e.get("event_id")), int(e.get("match_type") or 0), int(e.get("year") or YEAR)) for e in events}
    for event in ESPN_FALLBACK_EVENTS:
        key = (event["tour"], str(event["event_id"]), int(event["match_type"]), int(event["year"]))
        if key not in known:
            events.append(dict(event))
            known.add(key)
    return events


def bracket_event_catalog() -> list[dict[str, Any]]:
    events = [dict(e) for e in TENNISDB_ATP_EVENTS + WTA_EVENTS]
    seen = {(e["tour"], norm(e["name"]), e["source_kind"]) for e in events}
    for event in discover_espn_events():
        key = (event["tour"], norm(event["name"]), event["source_kind"])
        if key not in seen:
            events.append(event)
            seen.add(key)
    return events


def _match_event(feed_name: str, tour: str, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    target = norm(feed_name).replace(" wta", "").replace(" atp", "").strip()
    target_tokens = _tokens(target)
    candidates = [e for e in events if e["tour"] == tour]
    best = None
    best_score = 0
    for event in candidates:
        hay = norm(f"{event['name']} {event.get('location', '')}")
        hay_tokens = _tokens(hay)
        score = 0
        if target and target in hay:
            score += 8
        if hay and norm(event["name"]) in target:
            score += 5
        score += 2 * len(target_tokens & hay_tokens)
        if target_tokens and any(t in hay for t in target_tokens):
            score += 3
        if event.get("source_kind") in {"tennisdb", "wta"}:
            score += 1
        if score > best_score:
            best_score = score
            best = event
    return best if best_score >= 3 else None


def _team(node) -> dict[str, Any]:
    name_el = node.select_one(".team-name")
    score_el = node.select_one(".score")
    seed = node.select_one(".seed")
    name = name_el.get_text(" ", strip=True) if name_el else ""
    scores = [s.get_text("", strip=True) for s in score_el.find_all("span")] if score_el else []
    return {
        "name": _clean(name),
        "seed": _clean(seed.get_text(" ", strip=True)) if seed else "",
        "score": scores,
        "winner": "winner" in (node.get("class") or []),
    }


def parse_espn_bracket(event: dict[str, Any]) -> dict[str, Any]:
    url = ESPN_BRACKET.format(event_id=event["event_id"], match_type=event["match_type"], year=event["year"])
    soup = BeautifulSoup(_get(url), "html.parser")
    rounds = []
    for col in soup.select(".column-inner-wrap"):
        header = col.select_one(".round-header")
        round_name = header.get_text(" ", strip=True) if header else "Round"
        matches = []
        for game in col.select(".game"):
            teams = [_team(t) for t in game.select(".team")]
            if len(teams) < 2:
                continue
            status_el = game.select_one(".subheader")
            status = status_el.get_text(" ", strip=True) if status_el else ""
            match_id = None
            link = game.find("a", href=True)
            if link:
                m = re.search(r"matchId=(\d+)", link["href"])
                match_id = m.group(1) if m else None
            matches.append({
                "order": int(game.get("data-draw-order") or len(matches) + 1),
                "status": _clean(status),
                "player1": teams[0],
                "player2": teams[1],
                "winner": 1 if teams[0]["winner"] else 2 if teams[1]["winner"] else None,
                "match_id": match_id,
            })
        if matches:
            rounds.append({"name": _clean(round_name), "matches": matches})
    return _bracket_payload(event, "ESPN", url, rounds)


def _tennisdb_team(slot) -> dict[str, Any]:
    name_el = (
        slot.select_one(".bracket-name")
        or slot.select_one(".bracket-player")
        or slot.select_one(".player-name")
    )
    seed_el = slot.select_one(".bracket-seed") or slot.select_one(".seed")
    score_el = slot.select_one(".bracket-score") or slot.select_one(".score")
    name = name_el.get_text(" ", strip=True) if name_el else ""
    if not name:
        cloned = BeautifulSoup(str(slot), "html.parser")
        for score in cloned.select(".bracket-score,.score,.bracket-seed,.seed"):
            score.decompose()
        name = cloned.get_text(" ", strip=True)
    classes = " ".join(slot.get("class") or [])
    scores = score_el.get_text(" ", strip=True).split() if score_el else []
    return {
        "name": _clean(name),
        "seed": _clean(seed_el.get_text(" ", strip=True)) if seed_el else "",
        "score": scores,
        "winner": "winner" in classes,
    }


def parse_tennisdb_bracket(event: dict[str, Any]) -> dict[str, Any]:
    url = TENNISDB_BASE + event["path"]
    soup = BeautifulSoup(_get(url), "html.parser")
    rounds = []
    for col in soup.select(".bracket-round"):
        header = col.select_one(".bracket-round-header")
        round_name = header.get_text(" ", strip=True) if header else "Round"
        matches = []
        for game in col.select(".bracket-match"):
            slots = game.select(".bracket-slot")
            if len(slots) < 2:
                continue
            player1 = _tennisdb_team(slots[0])
            player2 = _tennisdb_team(slots[1])
            if not player1["name"] and not player2["name"]:
                continue
            matches.append({
                "order": len(matches) + 1,
                "status": "FINAL" if player1["winner"] or player2["winner"] else "",
                "player1": player1,
                "player2": player2,
                "winner": 1 if player1["winner"] else 2 if player2["winner"] else None,
                "match_id": None,
            })
        if matches:
            rounds.append({"name": _clean(round_name), "matches": matches})
    return _bracket_payload(event, "TennisDB", url, rounds)


def _wta_player(player: dict[str, Any], winner_id: str, score: list[str]) -> dict[str, Any]:
    player_id = str(player.get("id") or player.get("playerTeamId") or "")
    return {
        "name": _clean(player.get("PTDisplayLine") or player.get("displayName") or player.get("name")),
        "seed": _clean(player.get("seed") or player.get("Seed")),
        "score": score,
        "winner": bool(winner_id and player_id == winner_id),
    }


def _wta_scores(match: dict[str, Any]) -> tuple[list[str], list[str]]:
    score = ((match.get("Result") or {}).get("Score") or {})
    sets = _as_list(score.get("Set"))
    player1, player2 = [], []
    for item in sets:
        p1 = item.get("sA")
        p2 = item.get("sB")
        if p1 in (None, "") and p2 in (None, ""):
            continue
        tb1 = item.get("tbA")
        tb2 = item.get("tbB")
        player1.append(str(p1) + (f"({tb1})" if tb1 not in (None, "", "0", 0) else ""))
        player2.append(str(p2) + (f"({tb2})" if tb2 not in (None, "", "0", 0) else ""))
    return player1, player2


def _wta_draw_payload(data: dict[str, Any]) -> dict[str, Any]:
    draw_info = data.get("drawInfo")
    if isinstance(draw_info, list) and draw_info:
        raw = draw_info[0]
    else:
        raw = draw_info
    return json.loads(raw) if isinstance(raw, str) else raw


def parse_wta_bracket(event: dict[str, Any]) -> dict[str, Any]:
    url = WTA_DRAW_API.format(tournament_id=event["tournament_id"], year=YEAR)
    data = json.loads(_get(url, accept="application/json"))
    payload = _wta_draw_payload(data) or {}
    events = _as_list(((payload.get("Draws") or {}).get("Events") or {}).get("Event"))
    draw_event = next((e for e in events if e.get("EventTypeCode") == "LS"), events[0] if events else {})
    api_rounds = _as_list(((draw_event.get("Results") or {}).get("Round")))
    rounds = []
    for round_data in sorted(api_rounds, key=lambda r: int(r.get("roundId") or 0), reverse=True):
        round_id = int(round_data.get("roundId") or 0)
        matches = []
        seen_matches = set()
        for game in _as_list(round_data.get("Match")):
            match_id = str(game.get("Id") or "")
            if match_id and not match_id.startswith("LS"):
                continue
            if match_id in seen_matches:
                continue
            seen_matches.add(match_id)
            players = _as_list(((game.get("Players") or {}).get("PT")))
            if len(players) < 2:
                continue
            score1, score2 = _wta_scores(game)
            winner_id = str(game.get("winnerPTId") or "")
            player1 = _wta_player(players[0], winner_id, score1)
            player2 = _wta_player(players[1], winner_id, score2)
            status = "FINAL" if str(game.get("finished") or "") == "1" else _clean(game.get("mState"))
            matches.append({
                "order": len(matches) + 1,
                "status": status,
                "player1": player1,
                "player2": player2,
                "winner": 1 if player1["winner"] else 2 if player2["winner"] else None,
                "match_id": match_id or None,
            })
        if matches:
            rounds.append({"name": WTA_ROUNDS.get(round_id, f"Round {round_id}"), "matches": matches})
    return _bracket_payload(event, "WTA", url, rounds)


def _bracket_payload(event: dict[str, Any], source: str, url: str, rounds: list[dict[str, Any]]) -> dict[str, Any]:
    completed = sum(1 for r in rounds for m in r["matches"] if m["winner"])
    total = sum(len(r["matches"]) for r in rounds)
    if not total:
        raise ValueError(f"No bracket matches parsed from {source}")
    return {
        "tour": event["tour"],
        "name": event["name"],
        "location": event.get("location", ""),
        "source": source,
        "source_url": url,
        "event_id": event.get("event_id") or event.get("tournament_id") or event.get("path"),
        "match_type": event.get("match_type"),
        "year": event.get("year") or YEAR,
        "completed_matches": completed,
        "total_matches": total,
        "rounds": rounds,
    }


def parse_bracket(event: dict[str, Any]) -> dict[str, Any]:
    source = event.get("source_kind")
    if source == "tennisdb":
        return parse_tennisdb_bracket(event)
    if source == "wta":
        return parse_wta_bracket(event)
    return parse_espn_bracket(event)


def build_brackets_from_matches(matches: list[dict[str, Any]]) -> dict[str, Any]:
    events = bracket_event_catalog()
    wanted = []
    seen = set()
    for match in matches:
        tournament = match.get("tournament") or match.get("tournoi") or ""
        tour = match.get("tour") or "ATP"
        if not tournament or LOW_LEVEL.search(tournament):
            continue
        key = (tour, norm(tournament))
        if key in seen:
            continue
        seen.add(key)
        event = _match_event(tournament, tour, events)
        if event:
            wanted.append(event)
    brackets = []
    errors = []
    for event in wanted:
        try:
            brackets.append(parse_bracket(event))
            time.sleep(0.15)
        except Exception as exc:
            errors.append({"tour": event["tour"], "name": event["name"], "source": event.get("source_kind"), "error": str(exc)})
    brackets.sort(key=lambda b: (b["tour"], b["name"]))
    return {
        "updated": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "source": "TennisDB ATP, official WTA API, ESPN fallback",
        "count": len(brackets),
        "tournaments": brackets,
        "errors": errors,
    }
