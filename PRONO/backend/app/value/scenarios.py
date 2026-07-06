"""Odds-blind football scenario engine.

This module must never use betting odds, bookmaker prices, CLV, boosts, or EV as
input features. It turns sporting/context data into match scenarios that can be
compared to odds later by the betting layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

FORBIDDEN_ODDS_FEATURES = {
    "odd",
    "odds",
    "cote",
    "cotes",
    "price",
    "bookmaker",
    "book_margin",
    "market_probability",
    "implied_probability",
    "ev",
    "clv",
    "boost",
}

COMPLETENESS_WEIGHTS = {
    "home.team": 10,
    "away.team": 10,
    "home.ppg_recent": 8,
    "away.ppg_recent": 8,
    "home.gf_recent": 11,
    "home.ga_recent": 11,
    "away.gf_recent": 11,
    "away.ga_recent": 11,
    "home.injuries_count": 7,
    "away.injuries_count": 7,
    "home.stakes_level": 3,
    "away.stakes_level": 3,
}

BLOCKING_MISSING_FIELDS = {"home.team", "away.team"}
GOAL_PROFILE_FIELDS = {"home.gf_recent", "home.ga_recent", "away.gf_recent", "away.ga_recent"}
FORM_FIELDS = {"home.ppg_recent", "away.ppg_recent"}


@dataclass(frozen=True)
class TeamScenarioInput:
    team: str
    ppg_recent: float | None = None
    gf_recent: float | None = None
    ga_recent: float | None = None
    injuries_count: int | None = None
    stakes_level: str | None = None
    stakes_label: str | None = None


@dataclass(frozen=True)
class MatchScenarioInput:
    home: TeamScenarioInput
    away: TeamScenarioInput
    derby: str | None = None
    break_detected: bool = False
    break_label: str | None = None
    manual_context: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CompletenessAssessment:
    score: int
    missing_data: tuple[str, ...]
    blocking_missing_data: tuple[str, ...]
    degrading_missing_data: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioReport:
    completeness_score: int
    confidence: str
    main_scenario: str
    alternative_scenarios: tuple[str, ...]
    coherent_markets: tuple[str, ...]
    avoid_markets: tuple[str, ...]
    missing_data: tuple[str, ...]
    factors: tuple[str, ...]
    blocking_missing_data: tuple[str, ...] = field(default_factory=tuple)
    degrading_missing_data: tuple[str, ...] = field(default_factory=tuple)


def assert_no_odds_features(payload: Mapping[str, Any], path: str = "input") -> None:
    """Reject odds/betting features before scenario generation."""
    for key, value in payload.items():
        normalized = str(key).strip().lower()
        if normalized in FORBIDDEN_ODDS_FEATURES:
            raise ValueError(f"Odds feature forbidden in scenario engine: {path}.{key}")
        if isinstance(value, Mapping):
            assert_no_odds_features(value, f"{path}.{key}")
        elif isinstance(value, list | tuple):
            for index, item in enumerate(value):
                if isinstance(item, Mapping):
                    assert_no_odds_features(item, f"{path}.{key}[{index}]")


def scenario_from_mapping(payload: Mapping[str, Any]) -> ScenarioReport:
    """Convenience entrypoint for JSON-like inputs."""
    assert_no_odds_features(payload)
    home = payload.get("home") or {}
    away = payload.get("away") or {}
    if not isinstance(home, Mapping) or not isinstance(away, Mapping):
        raise ValueError("home and away must be objects.")
    return build_match_scenario(MatchScenarioInput(
        home=_team_from_mapping(home),
        away=_team_from_mapping(away),
        derby=_optional_str(payload.get("derby")),
        break_detected=bool(payload.get("break_detected", False)),
        break_label=_optional_str(payload.get("break_label")),
        manual_context=tuple(str(x) for x in payload.get("manual_context", ()) if str(x).strip()),
    ))


def _team_from_mapping(payload: Mapping[str, Any]) -> TeamScenarioInput:
    return TeamScenarioInput(
        team=str(payload.get("team", "")).strip(),
        ppg_recent=_optional_float(payload.get("ppg_recent")),
        gf_recent=_optional_float(payload.get("gf_recent")),
        ga_recent=_optional_float(payload.get("ga_recent")),
        injuries_count=_optional_int(payload.get("injuries_count")),
        stakes_level=_optional_str(payload.get("stakes_level")),
        stakes_label=_optional_str(payload.get("stakes_label")),
    )


def build_match_scenario(match: MatchScenarioInput) -> ScenarioReport:
    completeness = assess_completeness(match)
    factors: list[str] = []
    coherent: list[str] = []
    avoid: list[str] = []
    alternatives: list[str] = []

    profile = _goal_profile(match.home, match.away)
    form_edge = _form_edge(match.home, match.away)

    if profile == "open":
        factors.append("Les deux equipes ont un profil recent compatible avec un match ouvert.")
        coherent += ["Over 1.5", "BTTS", "Equipe favorite marque"]
        alternatives.append("Scenario alternatif : match ouvert avec but des deux equipes.")
    elif profile == "closed":
        factors.append("Les donnees recentes pointent vers un rythme offensif limite.")
        coherent += ["Under 3.5", "Nul mi-temps a surveiller"]
        avoid += ["Over agressif", "Handicap lourd"]
        alternatives.append("Scenario alternatif : premiere periode fermee, decision tardive.")
    else:
        factors.append("Profil buts incomplet ou equilibre : rester prudent sur les marches de total.")
        avoid += ["Over/Under agressif sans donnees supplementaires"]

    if GOAL_PROFILE_FIELDS.intersection(completeness.missing_data):
        avoid += ["BTTS/Over sans profil buts complet"]
    if FORM_FIELDS.intersection(completeness.missing_data):
        avoid += ["Double chance ascendant sans forme recente complete"]

    if form_edge:
        factors.append(form_edge)
        coherent.append("Double chance equipe en ascendant")
    else:
        alternatives.append("Scenario alternatif : match equilibre, eviter une lecture trop directionnelle.")

    risk_count = 0
    if match.derby:
        risk_count += 1
        factors.append(f"Derby/rivalite : {match.derby}.")
        avoid += ["Handicap favori lourd", "Lecture cote basse = securite"]
    if match.break_detected:
        risk_count += 1
        factors.append(match.break_label or "Reprise apres coupure calendrier.")
        avoid.append("Confiance forte sans confirmation rythme/compos")
    for team in (match.home, match.away):
        if (team.injuries_count or 0) >= 4:
            risk_count += 1
            factors.append(f"{team.team} a un volume d'absences a surveiller ({team.injuries_count}).")
            avoid.append(f"Ticket joueur / handicap {team.team} sans validation compo")
        if (team.stakes_level or "").lower() == "fort":
            factors.append(f"Enjeu fort pour {team.team} : {team.stakes_label or 'enjeu important'}.")

    for note in match.manual_context:
        factors.append(f"Note manuelle : {note}")

    main = _main_scenario(match, profile, form_edge, risk_count, list(completeness.missing_data), completeness.blocking_missing_data)
    confidence = _confidence(completeness.score, risk_count, completeness.blocking_missing_data)
    return ScenarioReport(
        completeness_score=completeness.score,
        confidence=confidence,
        main_scenario=main,
        alternative_scenarios=_dedupe(alternatives),
        coherent_markets=_dedupe(coherent),
        avoid_markets=_dedupe(avoid),
        missing_data=completeness.missing_data,
        factors=tuple(factors),
        blocking_missing_data=completeness.blocking_missing_data,
        degrading_missing_data=completeness.degrading_missing_data,
    )


def assess_completeness(match: MatchScenarioInput) -> CompletenessAssessment:
    missing = tuple(_missing_data(match))
    missing_weight = sum(COMPLETENESS_WEIGHTS.get(field_name, 0) for field_name in missing)
    score = max(0, 100 - missing_weight)
    blocking = tuple(field_name for field_name in missing if field_name in BLOCKING_MISSING_FIELDS)
    degrading = tuple(field_name for field_name in missing if field_name not in BLOCKING_MISSING_FIELDS)
    return CompletenessAssessment(
        score=score,
        missing_data=missing,
        blocking_missing_data=blocking,
        degrading_missing_data=degrading,
    )


def _missing_data(match: MatchScenarioInput) -> list[str]:
    missing: list[str] = []
    for side, team in (("home", match.home), ("away", match.away)):
        if not team.team:
            missing.append(f"{side}.team")
        for field_name in ("ppg_recent", "gf_recent", "ga_recent", "injuries_count", "stakes_level"):
            if getattr(team, field_name) is None:
                missing.append(f"{side}.{field_name}")
    return missing


def _goal_profile(home: TeamScenarioInput, away: TeamScenarioInput) -> str:
    values = (home.gf_recent, home.ga_recent, away.gf_recent, away.ga_recent)
    if any(value is None for value in values):
        return "unknown"
    avg_for = ((home.gf_recent or 0.0) + (away.gf_recent or 0.0)) / 2.0
    avg_against = ((home.ga_recent or 0.0) + (away.ga_recent or 0.0)) / 2.0
    if avg_for >= 1.4 and avg_against >= 1.0:
        return "open"
    if avg_for <= 1.0 and avg_against <= 1.0:
        return "closed"
    return "mixed"


def _form_edge(home: TeamScenarioInput, away: TeamScenarioInput) -> str | None:
    if home.ppg_recent is None or away.ppg_recent is None:
        return None
    diff = home.ppg_recent - away.ppg_recent
    if diff >= 0.6:
        return f"Ascendant recent cote {home.team} (ecart forme {diff:.2f} pts/match)."
    if diff <= -0.6:
        return f"Ascendant recent cote {away.team} (ecart forme {abs(diff):.2f} pts/match)."
    return None


def _main_scenario(
    match: MatchScenarioInput,
    profile: str,
    form_edge: str | None,
    risk_count: int,
    missing: list[str],
    blocking_missing: tuple[str, ...],
) -> str:
    if blocking_missing:
        return "Scenario bloque : donnees d'identite match insuffisantes."
    if missing and len(missing) >= 5:
        return "Scenario incomplet : donnees sportives insuffisantes pour qualifier fortement le match."
    tone = {
        "open": "Match potentiellement ouvert",
        "closed": "Match potentiellement ferme",
        "mixed": "Match au profil intermediaire",
        "unknown": "Match a profil buts incertain",
    }[profile]
    if form_edge:
        tone += f", avec {form_edge[0].lower() + form_edge[1:]}"
    else:
        tone += ", sans ascendant recent net"
    if risk_count >= 2:
        tone += ". Contexte volatil : privilegier des tickets prudents ou conditionnels."
    else:
        tone += "."
    return tone


def _confidence(completeness: int, risk_count: int, blocking_missing: tuple[str, ...]) -> str:
    if blocking_missing:
        return "Bloquee"
    if completeness < 60:
        return "Faible"
    if risk_count >= 2:
        return "A nuancer"
    if completeness >= 85 and risk_count == 0:
        return "Moyenne"
    return "Prudente"


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen = set()
    out = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None