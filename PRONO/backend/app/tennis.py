"""Donnees tennis pour PRONO.

Le scoreboard ATP/WTA est la source de verite des confrontations a venir. Le
flux de cotes reste utile seulement s'il porte exactement les deux memes joueurs;
sinon le match est affiche sans cote pour eviter les affiches de tour precedent.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import unicodedata
import urllib.request
from contextlib import closing
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app import tennis_coherence, tennis_journal
from app.tennis_brackets import build_brackets_from_matches
from app.tennis_coach import TennisCoach
from app.tennis_decision_calibration import run_from_sqlite, status_summary_for_row


FEED = "https://raw.githubusercontent.com/Mriganka-codes/tennis_data/main/matches.json"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/tennis/{league}/scoreboard?region=us&lang=en&dates={dates}&limit=1000"
# TennisExplorer daily schedule = source de cotes couvrant aussi les tournois 250/Challenger
# a J+1/J+2 (le flux GitHub ne publie que le jour meme). On l'utilise pour coter les
# affiches ESPN a venir, faute de quoi elles seraient masquees (filtered_unpriced).
TE_MATCHES_URL = "https://www.tennisexplorer.com/matches/?type=all&year={year}&month={month:02d}&day={day:02d}"
TE_TOUR = {"atp-men": "ATP", "wta-women": "WTA"}
_TE_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
_TE_HEAD_RE = re.compile(r'class="head flags"')
_TE_HEADCAT_RE = re.compile(r'<td class="t-name"[^>]*>\s*<a href="/[^"]*?/\d{4}/([a-z-]+)/', re.S)
_TE_PLAYER_RE = re.compile(r'<td class="t-name"[^>]*>\s*<a href="/player/[^"]*">([^<]+)</a>', re.S)
_TE_COURSE_RE = re.compile(r'<td class="course"[^>]*>\s*([0-9]+\.[0-9]+)\s*</td>', re.S)
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
    past = not raw.get("live") and kickoff < now - PAST_MATCH_GRACE
    too_far = kickoff > now + FUTURE_MATCH_HORIZON
    label = _date_label(kickoff, now)
    return {
        "kickoff": kickoff,
        "past": past,
        "too_far": too_far,
        "display": f"En cours - {kickoff.strftime('%H:%M')}" if raw.get("live") else f"{label} {kickoff.strftime('%H:%M')}",
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


def _market_item(key: str, label: str, pick: str, probability: float | None, detail: str, source: str, confidence: str, sample: int, signal: str | None = None) -> dict:
    return {
        "key": key,
        "label": label,
        "pick": pick,
        "prob": round(probability * 100) if probability is not None else None,
        # Cote juste = 1/p : c'est le seuil au-dessus duquel le prix du book devient
        # jouable. Sans elle, une probabilite affichee ne se compare a rien.
        "fair_odds": round(1 / probability, 2) if probability else None,
        "force": _signal_strength(probability),
        "source": source,
        "confidence": confidence,
        "sample": sample,
        "detail": detail,
        # Ecart de frequence mesure par backtests/backtest_marches_outsider.py entre
        # divergence et concordance Elo/marche. Renseigne uniquement sur les marches
        # reellement mesures : ailleurs il resterait une impression, pas un chiffre.
        "signal": signal,
    }


def _calibrated_pick(probability: float, positive: str, negative: str) -> tuple[str, float | None]:
    if probability >= 0.58:
        return positive, probability
    if probability <= 0.42:
        return negative, 1 - probability
    return "Pas d'avantage statistique", None


def _prop_validation_note(props: dict, key: str) -> str:
    result = (props.get("validation") or {}).get(key) or {}
    if result.get("brier") is None:
        return "validation indisponible"
    status = "valide" if result.get("validated") else "experimental"
    return f"{status} sur 2025: Brier {result['brier']:.3f} vs baseline {result['baseline_brier']:.3f}, n={result.get('sample', 0)}"


def _central_threshold(items: list[dict], expected: float) -> dict | None:
    return min(items or [], key=lambda item: abs((float(item.get("line") or 0) + 0.5) - expected), default=None)


def _props_confidence(players: list[dict]) -> str:
    levels = {"faible": 0, "moyenne": 1, "elevee": 2}
    return min((player.get("confidence", "faible") for player in players), key=lambda value: levels.get(value, 0), default="faible")


def _outsider_markets(outsider: str | None, favorite_probability: float, calibration: dict) -> list[dict]:
    """Les trois marches que le backtest place loin devant, tous portes par l'outsider.

    Pourquoi ceux-la et pas les totaux : backtest_marches_outsider.py mesure, sur 33 119
    matchs, l'ecart de frequence entre divergence et concordance Elo/marche. Les marches
    joueur captent +8.0 a +10.5 pt, les totaux de jeux +2.5 a +3.3 pt seulement. La page
    mettait jusqu'ici en avant les seconds.

    Piege mesure, a ne pas "optimiser" : combiner "prend un set" avec un over fait TOMBER
    le signal de +9.5 a +6.9 pt. L'over est probable mais pas discriminant -- il dilue.
    Ces trois marches restent donc secs.

    Aucune cote historique n'existe sur eux : ce sont des frequences, pas un ROI. La cote
    juste dit a partir de quel prix le pari devient jouable ; seul le journal des decisions
    dira si le book se trompe vraiment.
    """
    rates = calibration["rates"]
    sample = calibration["sample"]
    confidence = calibration["confidence"]
    name = outsider or "Outsider"
    # Ancrage marche pour le 2-0, coherent avec la colonne "Fav 2-0" de la table : prendre
    # le taux brut du bin ignorerait la cote du jour.
    favorite_2_0 = favorite_probability * (1 - rates["favorite_2_1_share"])
    return [
        _market_item(
            "outsider_takes_a_set", "Outsider prend un set", f"{name} >= 1 set",
            1 - favorite_2_0,
            f"= 1 - P(favori 2-0) {favorite_2_0:.0%}, ancree sur la cote du jour",
            "ancrage marche", confidence, sample, signal="+9.5 pt en divergence Elo",
        ),
        _market_item(
            "outsider_games_3_5", "Outsider +3.5 jeux", f"{name} +3.5",
            1 - rates["favorite_cover_3_5"],
            f"= 1 - P(favori l'emporte de 4 jeux ou plus) {rates['favorite_cover_3_5']:.0%}",
            "historique calibre", confidence, sample, signal="+10.5 pt en divergence Elo",
        ),
        _market_item(
            "outsider_set_1", "Outsider gagne le set 1", f"{name} set 1",
            1 - rates["favorite_wins_set_1"],
            f"= 1 - P(favori gagne la manche d'ouverture) {rates['favorite_wins_set_1']:.0%}",
            "historique calibre", confidence, sample, signal="+8.0 pt en divergence Elo",
        ),
    ]


def _secondary_markets(match: dict, intel: dict, favorite_probability: float, calibration: dict, outsider: str | None = None) -> list[dict]:
    rates = calibration["rates"]
    sample = calibration["sample"]
    confidence = calibration["confidence"]
    training = calibration["training"]
    source = "historique calibre"
    suffix = f"echantillon {sample}, apprentissage {training}, confiance {confidence}"

    total_pick, total_prob = _calibrated_pick(rates["over_22_5"], "Over 22.5 jeux", "Under 22.5 jeux")
    handicap_pick, handicap_prob = _calibrated_pick(rates["favorite_cover_2_5"], "Favori -2.5 jeux", "Adversaire +2.5 jeux")
    # Les marches a signal passent en tete : l'ordre de la liste est l'ordre d'affichage.
    markets = _outsider_markets(outsider, favorite_probability, calibration)
    markets += [
        _market_item("total_games", "Total jeux", total_pick, total_prob, f"P(Over) {rates['over_22_5']:.0%}; {suffix}", source, confidence, sample, signal="+2.5 pt seulement"),
        _market_item("handicap_games", "Handicap", handicap_pick, handicap_prob, f"P(favori -2.5) {rates['favorite_cover_2_5']:.0%}; {suffix}", source, confidence, sample),
    ]

    props = intel.get("props") or {}
    prop_players = [player for player in props.get("players", []) if player]
    tie_probability = float(props.get("tiebreak_probability") or round(rates["tiebreak"] * 100)) / 100
    tiebreak_pick, tiebreak_prob = _calibrated_pick(tie_probability, "Tie-break oui", "Tie-break non")
    tie_source = "modele tenue de service" if len(prop_players) == 2 else source
    tie_detail = f"P(au moins un tie-break) {tie_probability:.0%}; {_prop_validation_note(props, 'tiebreak')}"
    markets.append(_market_item("tiebreak", "Tie-break", tiebreak_pick, tiebreak_prob, tie_detail, tie_source, confidence, int(props.get("sample") or sample)))

    if prop_players:
        prop_confidence = _props_confidence(prop_players)
        prop_sample = sum(int(player.get("sample_surface") or 0) for player in prop_players)
        ace_parts, df_parts, hold_parts, break_parts = [], [], [], []
        for player in prop_players:
            name = _seedless(player.get("player") or "Joueur")
            ace_threshold = _central_threshold(player.get("aces_thresholds") or [], float(player.get("aces_expected") or 0))
            df_threshold = _central_threshold(player.get("double_faults_thresholds") or [], float(player.get("double_faults_expected") or 0))
            ace_suffix = f"; O{ace_threshold['line']} {ace_threshold['over']}%" if ace_threshold else ""
            df_suffix = f"; O{df_threshold['line']} {df_threshold['over']}%" if df_threshold else ""
            ace_parts.append(f"{name} {player.get('aces_expected')} [{'-'.join(map(str, player.get('aces_interval') or []))}]{ace_suffix}")
            df_parts.append(f"{name} {player.get('double_faults_expected')} [{'-'.join(map(str, player.get('double_faults_interval') or []))}]{df_suffix}")
            hold_parts.append(f"{name} {player.get('hold_probability')}%")
            break_parts.append(f"{name} {player.get('breaks_expected')} ({player.get('break_probability')}% 1+)")
        markets.extend([
            _market_item("aces", "Aces joueur", " | ".join(ace_parts), None, _prop_validation_note(props, "aces_reference"), "modele joueur/surface", prop_confidence, prop_sample),
            _market_item("double_faults", "Doubles fautes", " | ".join(df_parts), None, _prop_validation_note(props, "double_faults_3_plus"), "modele joueur/surface", prop_confidence, prop_sample),
            _market_item("hold", "Tenue service", " | ".join(hold_parts), None, _prop_validation_note(props, "broken"), "modele service/retour", prop_confidence, prop_sample),
            _market_item("breaks", "Breaks joueur", " | ".join(break_parts), None, _prop_validation_note(props, "break_1_plus"), "modele service/retour", prop_confidence, prop_sample),
        ])
    else:
        for key, label in (("aces", "Aces joueur"), ("double_faults", "Doubles fautes"), ("hold", "Tenue service"), ("breaks", "Breaks joueur")):
            markets.append(_market_item(key, label, "Profil indisponible", None, "joueurs non retrouves dans l'historique statistique", "donnees insuffisantes", "faible", 0))
    return markets

def _valid_odds(odds1, odds2) -> tuple[float | None, float | None]:
    try:
        left, right = float(odds1), float(odds2)
    except (TypeError, ValueError):
        return None, None
    if left <= 1 or right <= 1:
        return None, None
    return left, right


DERIVED_ANCHOR_KEYS = ("p20", "p21", "p3", "total_games", "handicap")
ANCHOR_SPREAD_MIN = 3  # en dessous, fourchette inutile: valeur unique (evite le bruit visuel)


def _anchor_values(favorite_probability: float, calibration: dict) -> dict:
    """Indicateurs derives a partir d'une ancre (proba du favori marche) parametrable.

    Aucune lecture de proba_marche en dur: le modele de distribution est inchange,
    seule l'ancre passe en argument. Supporte une proba < 0.5 (cas conflit d'identite
    du favori: l'Elo donne le favori marche perdant). Avec l'ancre = marche, reproduit
    exactement les formules historiques (non-regression a l'arrondi pres).
    """
    rates = calibration["rates"]
    share = rates["favorite_2_1_share"]
    return {
        "p20": round(favorite_probability * (1 - share) * 100),
        "p21": round(favorite_probability * share * 100),
        "p3": round(rates["three_sets"] * 100),
        "total_games": round(rates["over_22_5"] * 100),
        "handicap": round(rates["favorite_cover_2_5"] * 100),
    }


def _dual_anchor(value_market: int, value_elo: int | None) -> dict:
    """Restitue un indicateur derive sous forme double ancrage + fourchette."""
    if value_elo is None:
        return {
            "value_market": value_market, "value_elo": None, "value_ref": value_market,
            "range_min": value_market, "range_max": value_market, "spread": None, "single": True,
        }
    low, high = (value_market, value_elo) if value_market <= value_elo else (value_elo, value_market)
    spread = high - low
    return {
        "value_market": value_market, "value_elo": value_elo, "value_ref": value_market,
        "range_min": low, "range_max": high, "spread": spread, "single": spread < ANCHOR_SPREAD_MIN,
    }


def _strength_bin(favorite_probability: float) -> int:
    return sum(favorite_probability >= threshold for threshold in (0.60, 0.70, 0.80, 0.90))


def _apply_sampling_uncertainty(derived: dict, sample: int) -> None:
    """Elargit la fourchette de chaque indicateur par une bande binomiale ~80% liee a
    l'echantillon du bin de force. Concentre naturellement l'incertitude sur les bins
    peu peuples (gros favoris), sans valeur arbitraire. Non-regression: sur les bins
    denses (n de milliers) la marge est < 1 pt, la fourchette reste quasi inchangee.
    """
    n_eff = max(int(sample or 0), 25)
    for key in DERIVED_ANCHOR_KEYS:
        cell = derived[key]
        p = max(min((cell["value_market"] or 0) / 100.0, 0.99), 0.01)
        half = round(1.28 * math.sqrt(p * (1 - p) / n_eff) * 100)  # bande ~80%
        cell["uncertainty_pts"] = half
        cell["range_min"] = max(0, min(cell["range_min"], cell["value_market"] - half))
        cell["range_max"] = min(100, max(cell["range_max"], cell["value_market"] + half))
        cell["single"] = (cell["range_max"] - cell["range_min"]) < ANCHOR_SPREAD_MIN


def _build_derived_anchors(tour: str, surface: str, favorite_probability: float, market_calibration: dict, elo_favorite: float | None) -> dict:
    market_vals = _anchor_values(favorite_probability, market_calibration)
    if elo_favorite is not None:
        elo_vals = _anchor_values(elo_favorite, _coach().market_priors(tour, surface, elo_favorite))
    else:
        elo_vals = {key: None for key in DERIVED_ANCHOR_KEYS}
    derived = {key: _dual_anchor(market_vals[key], elo_vals[key]) for key in DERIVED_ANCHOR_KEYS}
    sample = int(market_calibration.get("sample") or 0)
    _apply_sampling_uncertainty(derived, sample)
    derived["anchor_recommended"] = "market"
    derived["calibration_flag"] = "en attente"
    derived["elo_available"] = elo_favorite is not None
    derived["favorite_conflict"] = bool(elo_favorite is not None and elo_favorite < 0.5)
    derived["split_sample"] = sample
    strength_bin = _strength_bin(favorite_probability)
    derived["strength_bin"] = strength_bin
    # Confiance pilotee par l'echantillon PUIS bridee aux bins de force extreme:
    # meme avec n correct, le split 2-0 des tres gros favoris est biaise (mesure OOS).
    split_confidence = market_calibration.get("confidence") or "faible"
    if strength_bin >= 4 or sample < 100:
        split_confidence = "faible"
    elif strength_bin >= 3 and split_confidence == "elevee":
        split_confidence = "moyenne"
    derived["split_confidence"] = split_confidence
    if strength_bin >= 3:
        note = "Favori tres fort : split 2-0 moins fiable (echantillon limite), fourchette elargie"
        if str(tour).upper() == "WTA":
            note += " ; la domination des gros favoris WTA est historiquement sous-estimee"
        derived["reliability_note"] = note
    return derived


def _favorite_fields(match: dict, odds1: float | None, odds2: float | None, intel: dict) -> dict:
    market_p1 = intel["market_p1"]
    fav1 = market_p1 >= 0.5
    favorite_probability = market_p1 if fav1 else 1 - market_p1
    favorite = match["player1"] if fav1 else match["player2"]
    favorite_odds = odds1 if fav1 else odds2
    outsider = match["player2"] if fav1 else match["player1"]
    outsider_odds = odds2 if fav1 else odds1
    elo_p1 = intel.get("elo_p1")
    surface_elo_p1 = intel.get("surface_elo_p1")
    global_elo_p1 = intel.get("global_elo_p1")
    elo_favorite = (elo_p1 if fav1 else 1 - elo_p1) if elo_p1 is not None else None
    surface_elo_favorite = (surface_elo_p1 if fav1 else 1 - surface_elo_p1) if surface_elo_p1 is not None else None
    global_elo_favorite = (global_elo_p1 if fav1 else 1 - global_elo_p1) if global_elo_p1 is not None else None
    decision = intel["decision"]
    low_p1, high_p1 = decision["range_p1"]
    range_favorite = (low_p1, high_p1) if fav1 else (1 - high_p1, 1 - low_p1)
    cycle_fav = intel["cycle1"] if fav1 else intel["cycle2"]
    cycle_opp = intel["cycle2"] if fav1 else intel["cycle1"]
    tour = match.get("tour", "ATP")
    surface = match.get("surface", "Dur")
    calibration = _coach().market_priors(tour, surface, favorite_probability)
    rates = calibration["rates"]
    p21_share = rates["favorite_2_1_share"]
    derived_anchors = _build_derived_anchors(tour, surface, favorite_probability, calibration, elo_favorite)
    market_vals = {key: derived_anchors[key]["value_market"] for key in DERIVED_ANCHOR_KEYS}
    decision_reasons = decision.get("reasons") or []
    return {
        "favori": _seedless(favorite),
        "outsider": _seedless(outsider),
        # Compatibility: proba now explicitly equals the market reference.
        "proba": _round_pct(favorite_probability),
        "proba_marche": _round_pct(favorite_probability),
        "proba_elo": _round_pct(elo_favorite) if elo_favorite is not None else None,
        "proba_elo_surface": _round_pct(surface_elo_favorite) if surface_elo_favorite is not None else None,
        "proba_elo_global": _round_pct(global_elo_favorite) if global_elo_favorite is not None else None,
        "elo_reference": intel.get("elo_reference"),
        "elo_detail": intel.get("elo_missing_reason"),
        "proba_brute": _round_pct(elo_favorite) if elo_favorite is not None else None,
        "ecart_elo": round((elo_favorite - favorite_probability) * 100, 1) if elo_favorite is not None else None,
        "ajustement": None,
        "decision": decision["label"],
        "decision_level": decision["level"],
        "impact_contexte": decision["context_label"],
        "score_contexte": decision["context_score"],
        "decision_detail": " ; ".join(decision_reasons) if decision_reasons else "aucun facteur contextuel discriminant",
        "props": intel.get("props"),
        "levels": intel.get("levels") or [],
        "concordance": (intel.get("concordance") or {}).get("label"),
        "concordance_level": (intel.get("concordance") or {}).get("level"),
        "concordance_detail": (intel.get("concordance") or {}).get("detail"),
        "fourchette_min": _round_pct(range_favorite[0]),
        "fourchette_max": _round_pct(range_favorite[1]),
        "cote": round(favorite_odds, 2) if favorite_odds else None,
        "cote_outsider": round(outsider_odds, 2) if outsider_odds else None,
        "p20": market_vals["p20"],
        "p21": market_vals["p21"],
        "p3": market_vals["p3"],
        "derived_anchors": derived_anchors,
        "markets": _secondary_markets(match, intel, favorite_probability, calibration, _seedless(outsider)),
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
        # Detail manche par manche, vu du vainqueur. Les agregats ci-dessous ne
        # permettent pas de trancher "gagne le set 1" : il faut la premiere paire.
        "sets": [list(pair) for pair in pairs],
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
                    is_live = status.get("state") == "in" or status.get("name") == "STATUS_IN_PROGRESS"
                    if is_completed:
                        if kickoff >= now - timedelta(days=14):
                            row = _completed_scoreboard_row(competition, tour, tournament, kickoff)
                            if row:
                                completed.append(row)
                        continue
                    if (not is_live and kickoff < now - PAST_MATCH_GRACE) or kickoff > now + FUTURE_MATCH_HORIZON:
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
                        "live": is_live,
                        "status": status.get("description") or status.get("detail"),
                        "round": ((competition.get("round") or {}).get("displayName") or "").strip(),
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
            "tour": tour,
            "tournoi": match["tournament"],
            "heure": match["time"],
            "kickoff": timing["kickoff"].isoformat() if timing["kickoff"] else None,
            "date_label": timing["label"],
            "live": bool(raw.get("live")),
            "round": raw.get("round") or "",
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


def _pending_final_rows(matches: list[dict], feed_updated: datetime, now: datetime) -> list[dict]:
    rows = []
    for raw in matches:
        if str(raw.get("round") or "").strip().lower() != "final":
            continue
        odds1, odds2 = _valid_odds(raw.get("odds1"), raw.get("odds2"))
        if odds1 and odds2:
            continue
        timing = _match_timing(raw, feed_updated, now)
        if timing["past"] or timing["too_far"]:
            continue
        tour = str(raw.get("tour") or "").upper()
        player1, player2 = _seedless(raw.get("player1")), _seedless(raw.get("player2"))
        if tour not in {"ATP", "WTA"} or not player1 or not player2:
            continue
        surface = _surface(raw.get("tournament", ""))
        rows.append({
            "tour": tour,
            "tournoi": raw.get("tournament", ""),
            "heure": timing["display"],
            "kickoff": timing["kickoff"].isoformat() if timing["kickoff"] else None,
            "surface": surface,
            "round": raw.get("round") or "Final",
            "live": bool(raw.get("live")),
            "match": f"{player1} vs {player2}",
            "joueur1": player1,
            "joueur2": player2,
            "match_source": raw.get("source") or "ESPN",
            "odds_status": "en_attente",
            "props": _coach().props.predict(tour, surface, player1, player2),
            "levels": [_coach().level_profile(player1, tour, surface), _coach().level_profile(player2, tour, surface)],
        })
    rows.sort(key=lambda row: (row.get("kickoff") or "9999", row["tournoi"], row["match"]))
    return rows


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


def _parse_te_day(html: str) -> list[dict]:
    """Extrait les affiches ATP/WTA simples avec cotes d'une page journaliere TennisExplorer.

    Chaque match occupe deux lignes: la premiere porte le joueur 1 et les deux cotes
    (`td.course`, rowspan=2), la seconde porte le joueur 2. Les doubles (`/doubles-team/`)
    et les matchs sans cote sont ignores. Le tour vient de l'en-tete de tournoi.
    """
    matches: list[dict] = []
    current_tour: str | None = None
    pending: tuple | None = None
    for row_match in _TE_ROW_RE.finditer(html):
        inner = row_match.group(1)
        if _TE_HEAD_RE.search(row_match.group(0)):
            category = _TE_HEADCAT_RE.search(inner)
            current_tour = TE_TOUR.get(category.group(1)) if category else None
            pending = None
            continue
        player_match = _TE_PLAYER_RE.search(inner)
        if not player_match:
            continue
        name = player_match.group(1).strip()
        if pending is None:
            odds = _TE_COURSE_RE.findall(inner)
            if current_tour and len(odds) >= 2:
                pending = (current_tour, name, odds[0], odds[1])
            else:
                pending = ("__skip__", None, None, None)
            continue
        tour, player1, odds1, odds2 = pending
        pending = None
        if tour == "__skip__":
            continue
        try:
            matches.append({
                "tour": tour,
                "player1": player1,
                "player2": name,
                "odds1": float(odds1),
                "odds2": float(odds2),
                "source": "tennisexplorer",
            })
        except (TypeError, ValueError):
            continue
    return matches


def _fetch_te_day(day) -> str:
    url = TE_MATCHES_URL.format(year=day.year, month=day.month, day=day.day)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (prono-tennis)"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", "ignore")


def fetch_tennisexplorer_odds(now: datetime | None = None) -> list[dict]:
    """Cotes TennisExplorer sur la fenetre [aujourd'hui .. +FUTURE_MATCH_HORIZON].

    Complete le flux GitHub (limite au jour meme) pour coter les affiches futures.
    Robuste: une journee en echec est ignoree, le reste est conserve.
    """
    now = now or _now_paris()
    out: list[dict] = []
    seen: set[tuple] = set()
    for offset in range(0, FUTURE_MATCH_HORIZON.days + 1):
        day = (now + timedelta(days=offset)).date()
        try:
            html = _fetch_te_day(day)
        except Exception:
            continue
        for raw in _parse_te_day(html):
            key = (raw["tour"], _player_pair_key(raw["player1"], raw["player2"]))
            if key in seen:
                continue
            seen.add(key)
            out.append(raw)
    return out


def _storage_pair(player1: str, player2: str) -> str:
    return "|".join(sorted(_player_pair_key(player1, player2)))


def _match_identity(tour: Any, tournament: Any, pair_key: str) -> str:
    """Identifiant stable d'un match, INDEPENDANT de l'horaire.

    Le bug corrige ici : l'ancienne cle de dedup incluait le kickoff a la minute, or
    l'horaire estime derive d'un snapshot a l'autre (un match reste "a venir" plusieurs
    jours, avec une estimation qui bouge). Chaque derive creait une nouvelle cle, donc le
    meme match etait recompte -- jusqu'a 5 fois observe en prod. On identifie desormais un
    match par (circuit, tournoi, paire de joueurs) : en simple a elimination directe, deux
    joueurs ne se rencontrent qu'une fois par tournoi, ces trois champs sont stables entre
    snapshots, et la paire est deja normalisee et triee.
    """
    normalized_tournament = " ".join(str(tournament or "").lower().split())
    return "|".join((str(tour or "").upper(), normalized_tournament, str(pair_key or "")))


def _record_decision_history(rows: list[dict], completed: list[dict], calculated_at: datetime) -> bool:
    root = os.environ.get("PRONO_DATA_DIR")
    if not root:
        return False
    path = Path(root) / "tennis" / "decision_history.sqlite3"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, timeout=10)) as db, db:
            pragma = db.execute("PRAGMA journal_mode=WAL")
            pragma.fetchone()
            pragma.close()
            db.execute("""
                CREATE TABLE IF NOT EXISTS tennis_decisions (
                    id INTEGER PRIMARY KEY,
                    calculated_at TEXT NOT NULL,
                    kickoff TEXT,
                    tour TEXT NOT NULL,
                    tournament TEXT,
                    pair_key TEXT NOT NULL,
                    player1 TEXT NOT NULL,
                    player2 TEXT NOT NULL,
                    favorite TEXT,
                    favorite_odds REAL,
                    market_probability REAL,
                    elo_probability REAL,
                    elo_gap REAL,
                    decision TEXT,
                    decision_level TEXT,
                    context_label TEXT,
                    quality TEXT,
                    range_min REAL,
                    range_max REAL,
                    result_winner TEXT,
                    result_recorded_at TEXT,
                    payload_json TEXT NOT NULL,
                    UNIQUE(calculated_at, tour, kickoff, pair_key)
                )
            """)
            existing = {row[1] for row in db.execute("PRAGMA table_info(tennis_decisions)")}
            def _ensure_column(name: str, ddl: str) -> None:
                if name not in existing:
                    db.execute(f"ALTER TABLE tennis_decisions ADD COLUMN {name} {ddl}")
                    existing.add(name)
            _ensure_column("surface", "TEXT")
            _ensure_column("concordance", "TEXT")
            _ensure_column("concordance_level", "TEXT")
            _ensure_column("cycle_favorite", "TEXT")
            _ensure_column("fatigue_favorite", "TEXT")
            _ensure_column("cycle_opponent", "TEXT")
            _ensure_column("fatigue_opponent", "TEXT")
            _ensure_column("outsider_odds", "REAL")
            _ensure_column("match_id", "TEXT")

            # Retro-remplissage des lignes ecrites avant l'introduction du match_id, pour
            # que la dedup fonctionne aussi sur l'historique existant. Ne touche que les
            # lignes NULL : apres le premier passage, c'est un COUNT a vide.
            legacy = db.execute(
                "SELECT id, tour, tournament, pair_key FROM tennis_decisions WHERE match_id IS NULL"
            ).fetchall()
            for legacy_id, legacy_tour, legacy_tournament, legacy_pair in legacy:
                db.execute(
                    "UPDATE tennis_decisions SET match_id = ? WHERE id = ?",
                    (_match_identity(legacy_tour, legacy_tournament, legacy_pair), legacy_id),
                )

            stamp = calculated_at.isoformat(timespec="minutes")
            for row in rows:
                pair_key = _storage_pair(row.get("joueur1", ""), row.get("joueur2", ""))
                db.execute("""
                    INSERT OR IGNORE INTO tennis_decisions (
                        calculated_at, kickoff, tour, tournament, pair_key, player1, player2,
                        favorite, favorite_odds, market_probability, elo_probability, elo_gap,
                        decision, decision_level, context_label, quality, range_min, range_max,
                        surface, concordance, concordance_level, cycle_favorite, fatigue_favorite,
                        cycle_opponent, fatigue_opponent, outsider_odds, match_id, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stamp, row.get("kickoff"), row.get("tour"), row.get("tournoi"),
                    pair_key,
                    row.get("joueur1"), row.get("joueur2"), row.get("favori"), row.get("cote"),
                    row.get("proba_marche"), row.get("proba_elo"), row.get("ecart_elo"),
                    row.get("decision"), row.get("decision_level"), row.get("impact_contexte"),
                    row.get("qualite"), row.get("fourchette_min"), row.get("fourchette_max"),
                    row.get("surface"), row.get("concordance"), row.get("concordance_level"),
                    row.get("cycle_favori"), row.get("fatigue_favori"), row.get("cycle_adversaire"),
                    row.get("fatigue_adversaire"), row.get("cote_outsider"),
                    _match_identity(row.get("tour"), row.get("tournoi"), pair_key),
                    json.dumps(row, ensure_ascii=True, separators=(",", ":")),
                ))
            for result in completed:
                pair_key = _storage_pair(result.get("winner", ""), result.get("loser", ""))
                # Reglage garde la cle pair_key : le nom de tournoi peut differer entre le
                # scoreboard ESPN et le flux de cotes de secours, si bien qu'un scope par
                # match_id risquerait de ne rien regler. Le rare recouvrement entre deux
                # tournois d'une meme paire dans la fenetre reste un defaut mineur separe.
                db.execute("""
                    UPDATE tennis_decisions
                    SET result_winner = ?, result_recorded_at = ?
                    WHERE pair_key = ? AND result_winner IS NULL
                """, (result.get("winner"), stamp, pair_key))
        db.close()
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return False

    # Registre des marches secondaires, dans la meme base. Il vit a part parce qu'il a une
    # autre maille : une ligne par marche et par match, la ou tennis_decisions en a une par
    # match. Un echec ici ne doit pas invalider l'enregistrement des decisions ci-dessus.
    try:
        tennis_journal.record_market_picks(rows, stamp, _storage_pair)
        tennis_journal.settle_from_results(completed, _storage_pair, stamp)
    except (OSError, sqlite3.Error, TypeError, ValueError):
        pass
    return True


def _decision_history_path() -> Path | None:
    root = os.environ.get("PRONO_DATA_DIR")
    if not root:
        return None
    return Path(root) / "tennis" / "decision_history.sqlite3"


def build_decision_calibration(min_sample: int = 50) -> dict:
    path = _decision_history_path()
    if not path or not path.exists():
        return {"record_count": 0, "bucket_count": 0, "buckets": [], "primary": [], "decisive": [], "min_sample": min_sample, "status": "no_history"}
    try:
        report = run_from_sqlite(path, min_sample=min_sample)
        report["status"] = "ok" if report.get("record_count") else "empty"
        return report
    except Exception as exc:
        return {"record_count": 0, "bucket_count": 0, "buckets": [], "primary": [], "decisive": [], "min_sample": min_sample, "status": "error", "error": str(exc)}


def _annotate_decision_calibration(rows: list[dict], report: dict | None) -> None:
    for row in rows:
        summary = status_summary_for_row(row, report, min_sample=int((report or {}).get("min_sample") or 50))
        if summary:
            row["decision_calibration"] = summary


def _set_anchor_ref(row: dict, derived: dict, anchor: str) -> None:
    """Bascule value_ref (et les scalaires retro-compat p20/p21/p3) sur l'ancre choisie."""
    for key in DERIVED_ANCHOR_KEYS:
        cell = derived[key]
        chosen = cell["value_elo"] if anchor == "elo" else cell["value_market"]
        if chosen is not None:
            cell["value_ref"] = chosen
    for key in ("p20", "p21", "p3"):
        value = derived[key]["value_ref"]
        if value is not None:
            row[key] = value


_COHERENCE_PICK_LABELS = {
    "Over 22.5 jeux": ("over_22_5", "yes"), "Under 22.5 jeux": ("over_22_5", "no"),
    "Favori -2.5 jeux": ("favorite_cover_2_5", "yes"), "Adversaire +2.5 jeux": ("favorite_cover_2_5", "no"),
    "Tie-break oui": ("tiebreak", "yes"), "Tie-break non": ("tiebreak", "no"),
}


def _row_active_picks(row: dict) -> list[tuple[str, str]]:
    """Picks 'actifs' du match: directions choisies (total, handicap, tie-break) + score modal."""
    picks: list[tuple[str, str]] = []
    for market in row.get("markets") or []:
        spec = _COHERENCE_PICK_LABELS.get(market.get("pick"))
        if spec:
            picks.append((spec[0], 1 if spec[1] == "yes" else 0))
    scores = {"favorite_2_0": row.get("p20"), "favorite_2_1": row.get("p21"), "three_sets": row.get("p3")}
    scores = {market: value for market, value in scores.items() if isinstance(value, (int, float))}
    if scores:
        picks.append((max(scores, key=scores.get), 1))
    return picks


def _annotate_coherence(rows: list[dict], matrix: dict | None) -> None:
    if not matrix:
        return
    for row in rows:
        row["coherence_flags"] = tennis_coherence.coherence_flags(_row_active_picks(row), circuit=row.get("tour", "ATP"), matrix=matrix)


def _apply_anchor_recommendations(rows: list[dict], report: dict | None, min_sample: int = 50) -> None:
    """Choisit l'ancre recommandee par match selon le verdict du backtest (bucket decision x concordance).

    Regle: n >= min_sample et conclusion decisive -> ancre au meilleur Brier (Elo si mieux calibre,
    sinon marche). 'bruit_probable' (donnees presentes, delta non significatif) -> 'indetermine'.
    Bucket non concluant / n trop faible / Elo indisponible -> 'market' par defaut + flag.
    """
    for row in rows:
        derived = row.get("derived_anchors")
        if not derived:
            continue
        if not derived.get("elo_available"):
            derived["anchor_recommended"] = "market"
            derived["calibration_flag"] = "elo indisponible"
            continue
        summary = status_summary_for_row(row, report, min_sample=min_sample)
        stats = (summary or {}).get("bucket_stats")
        sample = int((summary or {}).get("n") or 0)
        conclusion = (summary or {}).get("conclusion")
        if not stats or sample < min_sample or conclusion in (None, "non_concluant"):
            derived["anchor_recommended"] = "market"
            derived["calibration_flag"] = "calibration insuffisante"
            continue
        if conclusion == "bruit_probable":
            derived["anchor_recommended"] = "indetermine"
            derived["calibration_flag"] = "delta non significatif"
            continue
        brier_market = stats.get("brier_market")
        brier_elo = stats.get("brier_elo")
        if brier_elo is not None and brier_market is not None and brier_elo < brier_market:
            derived["anchor_recommended"] = "elo"
            derived["calibration_flag"] = "ok"
            _set_anchor_ref(row, derived, "elo")
        else:
            derived["anchor_recommended"] = "market"
            derived["calibration_flag"] = "ok"


def build_tennis() -> dict:
    data = fetch_feed()
    odds_matches = data.get("matches", [])
    now = _now_paris()
    feed_updated = _parse_feed_updated(data.get("last_updated"))
    try:
        scoreboard_matches, completed_results = fetch_scoreboard_snapshot(now)
    except Exception:
        scoreboard_matches, completed_results = [], []
    try:
        te_odds = fetch_tennisexplorer_odds(now)
    except Exception:
        te_odds = []
    _coach().set_live_results(completed_results)
    scoreboard_odds = list(odds_matches) + te_odds
    matches = _attach_odds(scoreboard_matches, scoreboard_odds) if scoreboard_matches else odds_matches
    atp, atp_filtered, atp_unpriced = _rows(matches, "ATP", feed_updated, now)
    wta, wta_filtered, wta_unpriced = _rows(matches, "WTA", feed_updated, now)
    pending_odds = _pending_final_rows(matches, feed_updated, now)
    external_sources = sorted({source for row in atp + wta for source in row.get("external_sources", [])})
    history_recorded = _record_decision_history(atp + wta, completed_results, now)
    decision_calibration_report = build_decision_calibration()
    _annotate_decision_calibration(atp + wta, decision_calibration_report)
    _apply_anchor_recommendations(atp + wta, decision_calibration_report, min_sample=int(decision_calibration_report.get("min_sample") or 50))
    _annotate_coherence(atp + wta, tennis_coherence.load_matrix())
    return {
        "updated": now.strftime("%d/%m/%Y %H:%M"),
        "feed_updated": data.get("last_updated", ""),
        "feed_age_hours": round((now - feed_updated).total_seconds() / 3600, 1),
        "scoreboard_source": "ESPN" if scoreboard_matches else "market-feed-fallback",
        "scoreboard_count": len(scoreboard_matches),
        "scoreboard_completed_count": len(completed_results),
        "te_odds_count": len(te_odds),
        "calibration": {"training": "2021-2024", "validation": "2025 hors echantillon", "method": "frequences hierarchiques ATP/WTA par surface et force du favori"},
        "props_validation": _coach().props.validation_report(2025),
        "filtered_past": atp_filtered + wta_filtered,
        "filtered_unpriced": atp_unpriced + wta_unpriced,
        "pending_odds": pending_odds,
        "time_policy": "Matchs cotes et statuts live: ESPN ATP/WTA. Les finales confirmees sans cote sont signalees separement, sans probabilite de marche.",
        "external_sources": external_sources,
        "decision_history_recorded": history_recorded,
        "decision_calibration": {"status": decision_calibration_report.get("status"), "record_count": decision_calibration_report.get("record_count"), "min_sample": decision_calibration_report.get("min_sample"), "decisive_count": len(decision_calibration_report.get("decisive", []))},
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
