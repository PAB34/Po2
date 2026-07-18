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


def _market_probability(odds1: float, odds2: float) -> float:
    implied1, implied2 = 1 / odds1, 1 / odds2
    return implied1 / (implied1 + implied2)


def _round_pct(value: float) -> float:
    return round(value * 100, 1)


def _profile_number(profile: dict, key: str) -> float | None:
    try:
        value = profile.get(key)
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _signal_strength(probability: float | None) -> str:
    if probability is None:
        return "info"
    edge = abs(probability - 0.5)
    if edge >= 0.14:
        return "fort"
    if edge >= 0.07:
        return "moyen"
    return "faible"


def _market_item(key: str, label: str, pick: str, probability: float | None, detail: str, source: str, confidence: str, sample: int) -> dict:
    return {
        "key": key,
        "label": label,
        "pick": pick,
        "prob": round(probability * 100) if probability is not None else None,
        "force": _signal_strength(probability),
        "source": source,
        "confidence": confidence,
        "sample": sample,
        "detail": detail,
    }


def _calibrated_pick(probability: float, positive: str, negative: str) -> tuple[str, float | None]:
    if probability >= 0.58:
        return positive, probability
    if probability <= 0.42:
        return negative, 1 - probability
    return "Pas d'avantage statistique", None


def _secondary_markets(match: dict, intel: dict, favorite_probability: float, calibration: dict) -> list[dict]:
    rates = calibration["rates"]
    sample = calibration["sample"]
    confidence = calibration["confidence"]
    training = calibration["training"]
    source = "historique calibre"
    suffix = f"echantillon {sample}, apprentissage {training}, confiance {confidence}"

    total_pick, total_prob = _calibrated_pick(rates["over_22_5"], "Over 22.5 jeux", "Under 22.5 jeux")
    handicap_pick, handicap_prob = _calibrated_pick(rates["favorite_cover_2_5"], "Favori -2.5 jeux", "Adversaire +2.5 jeux")
    tiebreak_pick, tiebreak_prob = _calibrated_pick(rates["tiebreak"], "Tie-break oui", "Tie-break non")
    markets = [
        _market_item("total_games", "Total jeux", total_pick, total_prob, f"P(Over) {rates['over_22_5']:.0%}; {suffix}", source, confidence, sample),
        _market_item("handicap_games", "Handicap", handicap_pick, handicap_prob, f"P(favori -2.5) {rates['favorite_cover_2_5']:.0%}; {suffix}", source, confidence, sample),
        _market_item("tiebreak", "Tie-break", tiebreak_pick, tiebreak_prob, f"P(au moins un tie-break) {rates['tiebreak']:.0%}; {suffix}", source, confidence, sample),
    ]

    serve1, serve2 = intel.get("serve1") or {}, intel.get("serve2") or {}
    ace1, ace2 = _profile_number(serve1, "ace_pct"), _profile_number(serve2, "ace_pct")
    sample1, sample2 = int(_profile_number(serve1, "sample") or 0), int(_profile_number(serve2, "sample") or 0)
    if ace1 is not None and ace2 is not None:
        ace_confidence = "elevee" if min(sample1, sample2) >= 20 else "moyenne" if min(sample1, sample2) >= 10 else "faible"
        markets.append(_market_item(
            "aces", "Aces", f"Profil combine {ace1 + ace2:.1f}%", None,
            f"Taux d'aces observes, {sample1}+{sample2} matchs; aucune ligne bookmaker disponible",
            "stats joueurs observees", ace_confidence, sample1 + sample2,
        ))
    else:
        markets.append(_market_item(
            "aces", "Aces", "Profil indisponible", None,
            "Une probabilite d'Over/Under aces exige une ligne bookmaker et les profils des deux joueurs",
            "donnees insuffisantes", "faible", sample1 + sample2,
        ))
    return markets

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
    favorite = match["player1"] if fav1 else match["player2"]
    favorite_odds = odds1 if fav1 else odds2
    cycle_fav = intel["cycle1"] if fav1 else intel["cycle2"]
    cycle_opp = intel["cycle2"] if fav1 else intel["cycle1"]
    calibration = _coach().market_priors(match.get("tour", "ATP"), match.get("surface", "Dur"), favorite_probability)
    rates = calibration["rates"]
    p21_share = rates["favorite_2_1_share"]
    return {
        "favori": _seedless(favorite),
        "proba": _round_pct(favorite_probability),
        "proba_brute": _round_pct(raw_fav),
        "proba_marche": _round_pct(market_fav),
        "ajustement": round((favorite_probability - raw_fav) * 100, 1),
        "cote": round(favorite_odds, 2) if favorite_odds else None,
        "p20": round(favorite_probability * (1 - p21_share) * 100),
        "p21": round(favorite_probability * p21_share * 100),
        "p3": round(rates["three_sets"] * 100),
        "markets": _secondary_markets(match, intel, favorite_probability, calibration),
        "market_calibration": {"sample": calibration["sample"], "confidence": calibration["confidence"], "training": calibration["training"]},
        "cycle_favori": cycle_fav["label"],
        "fatigue_favori": cycle_fav["fatigue"],
        "cycle_adversaire": cycle_opp["label"],
        "fatigue_adversaire": cycle_opp["fatigue"],
    }

def _player_signatures(name: str) -> set[str]:
    words = _norm_words(name)
    if not words:
        return set()
    if len(words) == 1:
        return {words[0]}
    aliases = set()
    if len(words[-1]) == 1:
        initial = words[-1][0]
        aliases.add(f"{words[0]}:{initial}")
        if len(words) > 2:
            aliases.add(f"{words[-2]}:{initial}")
    else:
        initial = words[0][0]
        aliases.add(f"{words[-1]}:{initial}")
        if len(words) > 2:
            aliases.add(f"{words[-2]}:{initial}")
    return aliases


def _player_signature(name: str) -> str:
    aliases = sorted(_player_signatures(name))
    return aliases[0] if aliases else ""


def _player_pair_key(player1: str, player2: str) -> frozenset[str]:
    return frozenset(sig for sig in (_player_signature(player1), _player_signature(player2)) if sig)


def _player_pair_keys(player1: str, player2: str) -> list[frozenset[str]]:
    left, right = _player_signatures(player1), _player_signatures(player2)
    return [frozenset((a, b)) for a in left for b in right if a and b and a != b]


def _odds_index(matches: list[dict]) -> dict[tuple[str, frozenset[str]], list[dict]]:
    index: dict[tuple[str, frozenset[str]], list[dict]] = {}
    for raw in matches:
        odds1, odds2 = _valid_odds(raw.get("odds1"), raw.get("odds2"))
        if not odds1 or not odds2:
            continue
        tour = str(raw.get("tour") or "").upper()
        for pair_key in _player_pair_keys(raw.get("player1", ""), raw.get("player2", "")):
            if len(pair_key) != 2:
                continue
            index.setdefault((tour, pair_key), []).append(raw)
    return index


def _find_odds_candidate(index: dict[tuple[str, frozenset[str]], list[dict]], match: dict) -> dict | None:
    tour = str(match.get("tour") or "").upper()
    for pair_key in _player_pair_keys(match.get("player1", ""), match.get("player2", "")):
        candidates = index.get((tour, pair_key)) or []
        if candidates:
            return candidates[0]
    return None


def _attach_odds(scoreboard: list[dict], odds_matches: list[dict]) -> list[dict]:
    indexed = _odds_index(odds_matches)
    out = []
    for match in scoreboard:
        item = dict(match)
        candidate = _find_odds_candidate(indexed, item)
        if candidate:
            odds1, odds2 = _valid_odds(candidate.get("odds1"), candidate.get("odds2"))
            candidate_left = _player_signatures(candidate.get("player1", ""))
            scoreboard_left = _player_signatures(item.get("player1", ""))
            if candidate_left & scoreboard_left:
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


def _score_value(line: dict) -> int | None:
    value = str(line.get("value") if line.get("value") is not None else line.get("displayValue") or "").strip()
    match = re.match(r"\d+", value)
    return int(match.group()) if match else None


def _completed_scoreboard_row(competition: dict, tour: str, tournament: str, kickoff: datetime) -> dict | None:
    competitors = competition.get("competitors", [])
    if len(competitors) != 2:
        return None
    winner = next((entry for entry in competitors if entry.get("winner") is True), None)
    loser = next((entry for entry in competitors if entry is not winner), None)
    if winner is None or loser is None:
        return None
    winner_name, loser_name = _competitor_name(winner), _competitor_name(loser)
    if not winner_name or not loser_name:
        return None
    winner_games = [_score_value(line) for line in winner.get("linescores", [])]
    loser_games = [_score_value(line) for line in loser.get("linescores", [])]
    pairs = [(left, right) for left, right in zip(winner_games, loser_games) if left is not None and right is not None]
    if not pairs:
        return None
    return {
        "date": kickoff.date().isoformat(),
        "tour": tour,
        "tournament": tournament,
        "winner": winner_name,
        "loser": loser_name,
        "sets_w": sum(left > right for left, right in pairs),
        "sets_l": sum(right > left for left, right in pairs),
        "games_w": sum(left for left, _ in pairs),
        "games_l": sum(right for _, right in pairs),
        "tiebreaks": sum({left, right} == {6, 7} for left, right in pairs),
        "odds_w": None,
        "odds_l": None,
        "source": "ESPN",
    }


def fetch_scoreboard_snapshot(now: datetime | None = None) -> tuple[list[dict], list[dict]]:
    now = now or _now_paris()
    dates = f"{(now - timedelta(days=14)).strftime('%Y%m%d')}-{(now + FUTURE_MATCH_HORIZON).strftime('%Y%m%d')}"
    upcoming, completed = [], []
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
                    kickoff = _parse_espn_date(competition.get("startDate") or competition.get("date"))
                    if not kickoff:
                        continue
                    status = ((competition.get("status") or {}).get("type") or {})
                    is_completed = status.get("state") == "post" or status.get("completed")
                    if is_completed:
                        if kickoff >= now - timedelta(days=14):
                            row = _completed_scoreboard_row(competition, tour, tournament, kickoff)
                            if row:
                                completed.append(row)
                        continue
                    if kickoff < now - PAST_MATCH_GRACE or kickoff > now + FUTURE_MATCH_HORIZON:
                        continue
                    names = [_competitor_name(entry) for entry in competition.get("competitors", [])]
                    names = [name for name in names if name]
                    if len(names) != 2 or any(_strip(name) in {"tbd", "bye"} for name in names):
                        continue
                    upcoming.append({
                        "tour": tour,
                        "tournament": tournament,
                        "time": kickoff.isoformat(),
                        "kickoff": kickoff.isoformat(),
                        "player1": names[0],
                        "player2": names[1],
                        "source": "ESPN",
                    })
    seen, unique = set(), []
    for row in sorted(upcoming, key=lambda item: (item["kickoff"], item["tour"], item["tournament"], item["player1"], item["player2"])):
        key = (row["tour"], row["kickoff"], _player_pair_key(row["player1"], row["player2"]))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    completed_seen, completed_unique = set(), []
    for row in completed:
        key = (row["date"], row["tour"], row["tournament"], _player_pair_key(row["winner"], row["loser"]))
        if key not in completed_seen:
            completed_seen.add(key)
            completed_unique.append(row)
    return unique, completed_unique


def fetch_scoreboard_matches(now: datetime | None = None) -> list[dict]:
    return fetch_scoreboard_snapshot(now)[0]

def _rows(matches: list[dict], tour: str, feed_updated: datetime, now: datetime) -> tuple[list[dict], int, int]:
    rows = []
    filtered_past = 0
    filtered_unpriced = 0
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
        if not odds1 or not odds2:
            filtered_unpriced += 1
            continue

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
            "qualite": intel.get("quality"),
            "qualite_score": intel.get("quality_score"),
            "incertitude_pts": intel.get("uncertainty_pts"),
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
    return rows, filtered_past, filtered_unpriced


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
        scoreboard_matches, completed_results = fetch_scoreboard_snapshot(now)
    except Exception:
        scoreboard_matches, completed_results = [], []
    _coach().set_live_results(completed_results)
    matches = _attach_odds(scoreboard_matches, odds_matches) if scoreboard_matches else odds_matches
    atp, atp_filtered, atp_unpriced = _rows(matches, "ATP", feed_updated, now)
    wta, wta_filtered, wta_unpriced = _rows(matches, "WTA", feed_updated, now)
    external_sources = sorted({source for row in atp + wta for source in row.get("external_sources", [])})
    return {
        "updated": now.strftime("%d/%m/%Y %H:%M"),
        "feed_updated": data.get("last_updated", ""),
        "feed_age_hours": round((now - feed_updated).total_seconds() / 3600, 1),
        "scoreboard_source": "ESPN" if scoreboard_matches else "market-feed-fallback",
        "scoreboard_count": len(scoreboard_matches),
        "scoreboard_completed_count": len(completed_results),
        "calibration": {"training": "2021-2024", "validation": "2025 hors echantillon", "method": "frequences hierarchiques ATP/WTA par surface et force du favori"},
        "filtered_past": atp_filtered + wta_filtered,
        "filtered_unpriced": atp_unpriced + wta_unpriced,
        "time_policy": "Confrontations a venir: scoreboard ESPN ATP/WTA; seuls les matchs avec cote rattachee au meme duo de joueurs sont affiches.",
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
