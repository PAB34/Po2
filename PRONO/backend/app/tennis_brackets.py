"""Tournament bracket sources for the PRONO tennis view.

Primary source: ESPN public bracket pages. They are not an official API, but they
are server-readable, cover ATP/WTA singles, and expose full round columns.
"""
from __future__ import annotations

import html
import re
import time
import unicodedata
import urllib.request
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

YEAR = datetime.now().year
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
ATP_SCHEDULE = "https://espndeportes.espn.com/tenis/schedule"
WTA_SCHEDULE = "https://www.espn.com/tennis/schedule/_/type/wta"
ESPN_BRACKET = "https://m.espn.com/general/tennis/bracket?id={event_id}&matchType={match_type}&src=desktop&year={year}"
LOW_LEVEL = re.compile(r"challenger|itf|utr|futures|davis cup|billie jean king", re.I)
DROP_WORDS = {
    "atp", "wta", "open", "ladies", "men", "women", "tennis", "pharmaceuticals",
    "presented", "classic", "championships", "generali", "bancomat", "unicredit",
    "plava", "laguna", "croatia", "swiss", "efg", "nordea", "vanda",
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


def _get(url: str, accept: str = "text/html") -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
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
            "event_id": event_id,
            "match_type": int(match_type),
            "year": int(year),
            "name": html.unescape(name),
            "location": html.unescape(location),
        })
    return events


def discover_espn_events() -> list[dict[str, Any]]:
    return _schedule_events(ATP_SCHEDULE, "ATP") + _schedule_events(WTA_SCHEDULE, "WTA")


def _match_event(feed_name: str, tour: str, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    target = norm(feed_name).replace(" wta", "").replace(" atp", "").strip()
    target_tokens = _tokens(target)
    candidates = [e for e in events if e["tour"] == tour]
    best = None
    best_score = 0
    for event in candidates:
        hay = norm(f"{event['name']} {event['location']}")
        hay_tokens = _tokens(hay)
        score = 0
        if target and target in hay:
            score += 8
        if hay and norm(event["name"]) in target:
            score += 5
        score += 2 * len(target_tokens & hay_tokens)
        # Helpful for feed labels like "Bastad" while ESPN uses "Nordea Open".
        if target_tokens and any(t in hay for t in target_tokens):
            score += 3
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
        "name": html.unescape(" ".join(name.split())),
        "seed": seed.get_text(" ", strip=True) if seed else "",
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
                "status": html.unescape(status),
                "player1": teams[0],
                "player2": teams[1],
                "winner": 1 if teams[0]["winner"] else 2 if teams[1]["winner"] else None,
                "match_id": match_id,
            })
        if matches:
            rounds.append({"name": html.unescape(round_name), "matches": matches})
    completed = sum(1 for r in rounds for m in r["matches"] if m["winner"])
    total = sum(len(r["matches"]) for r in rounds)
    return {
        "tour": event["tour"],
        "name": event["name"],
        "location": event.get("location", ""),
        "source": "espn",
        "source_url": url,
        "event_id": event["event_id"],
        "match_type": event["match_type"],
        "year": event["year"],
        "completed_matches": completed,
        "total_matches": total,
        "rounds": rounds,
    }


def build_brackets_from_matches(matches: list[dict[str, Any]]) -> dict[str, Any]:
    events = discover_espn_events()
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
            brackets.append(parse_espn_bracket(event))
            time.sleep(0.15)
        except Exception as exc:
            errors.append({"tour": event["tour"], "name": event["name"], "error": str(exc)})
    brackets.sort(key=lambda b: (b["tour"], b["name"]))
    return {
        "updated": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "source": "ESPN public bracket pages",
        "count": len(brackets),
        "tournaments": brackets,
        "errors": errors,
    }
