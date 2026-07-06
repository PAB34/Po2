"""Scenario-driven ticket families without player markets or betting advice."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .betting_completeness import BettingCompletenessAssessment
from .scenario_predictions import ScenarioPrediction


@dataclass(frozen=True)
class TicketFamilyCandidate:
    family: str
    event_id: str
    kickoff: str
    home: str
    away: str
    markets: tuple[str, ...]
    rationale: str
    risk_level: str
    readiness: str
    sporting_completeness_score: int
    betting_completeness_score: int | None = None
    blocking_reasons: tuple[str, ...] = ()
    degrading_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class TicketFamilyReport:
    source: str
    n_predictions: int
    n_candidates: int
    min_sporting_completeness: int
    candidates: tuple[TicketFamilyCandidate, ...]
    warnings: tuple[str, ...]


def build_ticket_family_candidates(
    predictions: Sequence[ScenarioPrediction],
    betting_completeness_by_event: Mapping[str, BettingCompletenessAssessment] | None = None,
    min_sporting_completeness: int = 70,
    require_betting_ready: bool = False,
    source: str = "scenario_predictions",
) -> TicketFamilyReport:
    candidates: list[TicketFamilyCandidate] = []
    betting_map = betting_completeness_by_event or {}
    for prediction in predictions:
        scenario = prediction.to_dict()["scenario"]
        if int(scenario.get("completeness_score", 0)) < min_sporting_completeness:
            continue
        if scenario.get("blocking_missing_data"):
            continue
        betting = betting_map.get(prediction.event_id)
        if require_betting_ready and (betting is None or betting.status == "blocked"):
            continue
        candidates.extend(_families_for_prediction(prediction, scenario, betting))
    return TicketFamilyReport(
        source=source,
        n_predictions=len(predictions),
        n_candidates=len(candidates),
        min_sporting_completeness=min_sporting_completeness,
        candidates=tuple(candidates),
        warnings=(
            "Ticket families are research groupings only; they do not use odds as sports features and do not imply profitability.",
            "Player markets are excluded from this MVP.",
        ),
    )


def _families_for_prediction(
    prediction: ScenarioPrediction,
    scenario: Mapping[str, Any],
    betting: BettingCompletenessAssessment | None,
) -> list[TicketFamilyCandidate]:
    markets = set(str(value) for value in scenario.get("coherent_markets", []))
    avoid = set(str(value) for value in scenario.get("avoid_markets", []))
    out: list[TicketFamilyCandidate] = []
    score = int(scenario.get("completeness_score", 0))

    if "Double chance equipe en ascendant" in markets and "Double chance ascendant sans forme recente complete" not in avoid:
        out.append(_candidate(
            prediction,
            scenario,
            betting,
            family="safe",
            markets=("Double chance equipe en ascendant",),
            rationale="Scenario avec ascendant recent et lecture directionnelle prudente.",
            risk_level="low",
            score=score,
        ))

    if {"Over 1.5", "BTTS"}.intersection(markets) and "BTTS/Over sans profil buts complet" not in avoid:
        selected = tuple(market for market in ("Over 1.5", "BTTS") if market in markets)
        out.append(_candidate(
            prediction,
            scenario,
            betting,
            family="buts",
            markets=selected,
            rationale="Scenario ouvert ou compatible avec un marche buts simple.",
            risk_level="medium",
            score=score,
        ))

    fun_markets = []
    if "Equipe favorite marque" in markets:
        fun_markets.append("Equipe favorite marque")
    if "Under 3.5" in markets:
        fun_markets.append("Under 3.5")
    if fun_markets:
        out.append(_candidate(
            prediction,
            scenario,
            betting,
            family="fun_simple",
            markets=tuple(fun_markets),
            rationale="Lecture exploratoire simple issue du scenario, sans live.",
            risk_level="high",
            score=score,
        ))
    return out


def _candidate(
    prediction: ScenarioPrediction,
    scenario: Mapping[str, Any],
    betting: BettingCompletenessAssessment | None,
    family: str,
    markets: tuple[str, ...],
    rationale: str,
    risk_level: str,
    score: int,
) -> TicketFamilyCandidate:
    blocking = list(str(value) for value in scenario.get("blocking_missing_data", []))
    degrading = list(str(value) for value in scenario.get("degrading_missing_data", []))
    readiness = "sporting_ready"
    betting_score = None
    if betting is not None:
        betting_score = betting.score
        if betting.status == "blocked":
            readiness = "betting_blocked"
            blocking.extend(f"betting:{value}" for value in betting.blocking_missing_data)
        elif betting.status == "degraded":
            readiness = "betting_degraded"
            degrading.extend(f"betting:{value}" for value in betting.degrading_missing_data)
        else:
            readiness = "betting_ready"
    return TicketFamilyCandidate(
        family=family,
        event_id=prediction.event_id,
        kickoff=prediction.kickoff,
        home=prediction.home,
        away=prediction.away,
        markets=markets,
        rationale=rationale,
        risk_level=risk_level,
        readiness=readiness,
        sporting_completeness_score=score,
        betting_completeness_score=betting_score,
        blocking_reasons=tuple(_dedupe(blocking)),
        degrading_reasons=tuple(_dedupe(degrading)),
    )


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out