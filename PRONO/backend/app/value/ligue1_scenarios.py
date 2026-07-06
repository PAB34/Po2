"""Ligue 1 payload adapter for odds-blind scenario generation.

The existing `/api/ligue1/journee` payload contains market probabilities and
picks for the current UI. This adapter deliberately reads only sporting fields
before calling the scenario engine.
"""
from __future__ import annotations

from typing import Any, Mapping

from .scenarios import ScenarioReport, scenario_from_mapping


def build_ligue1_journee_scenarios(payload: Mapping[str, Any]) -> dict[str, Any]:
    matches = payload.get("matches") or []
    if not isinstance(matches, list | tuple):
        raise ValueError("journee.matches must be a list.")

    break_info = _mapping(payload.get("break"))
    rows = []
    for match in matches:
        if not isinstance(match, Mapping):
            raise ValueError("journee.matches items must be objects.")
        rows.append(build_ligue1_match_scenario(match, break_info=break_info))

    return {
        "source": _optional_text(payload.get("source")),
        "updated": _optional_text(payload.get("updated")),
        "count": len(rows),
        "matches": rows,
    }


def build_ligue1_match_scenario(match: Mapping[str, Any], break_info: Mapping[str, Any] | None = None) -> dict[str, Any]:
    scenario_payload = ligue1_match_to_scenario_payload(match, break_info=break_info)
    report = scenario_from_mapping(scenario_payload)
    home = scenario_payload["home"]["team"]
    away = scenario_payload["away"]["team"]
    return {
        "kickoff": _optional_text(match.get("kickoff")),
        "home": home,
        "away": away,
        "scenario": scenario_report_to_dict(report),
    }


def ligue1_match_to_scenario_payload(
    match: Mapping[str, Any],
    break_info: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    home_block = _mapping(match.get("home_block"))
    away_block = _mapping(match.get("away_block"))
    break_block = _mapping(break_info)
    return {
        "home": _team_payload(match, "home", home_block),
        "away": _team_payload(match, "away", away_block),
        "derby": _optional_text(match.get("derby")),
        "break_detected": bool(break_block.get("detected", False)),
        "break_label": _optional_text(break_block.get("note")) or _optional_text(break_block.get("label")),
    }


def scenario_report_to_dict(report: ScenarioReport) -> dict[str, Any]:
    return {
        "completeness_score": report.completeness_score,
        "confidence": report.confidence,
        "main_scenario": report.main_scenario,
        "alternative_scenarios": list(report.alternative_scenarios),
        "coherent_markets": list(report.coherent_markets),
        "avoid_markets": list(report.avoid_markets),
        "missing_data": list(report.missing_data),
        "blocking_missing_data": list(report.blocking_missing_data),
        "degrading_missing_data": list(report.degrading_missing_data),
        "factors": list(report.factors),
    }


def _team_payload(match: Mapping[str, Any], side: str, block: Mapping[str, Any]) -> dict[str, Any]:
    stakes = _mapping(block.get("stakes"))
    return {
        "team": _optional_text(block.get("team")) or _optional_text(match.get(side)) or "",
        "ppg_recent": block.get("ppg_recent"),
        "gf_recent": block.get("gf_recent"),
        "ga_recent": block.get("ga_recent"),
        "injuries_count": block.get("injuries_count"),
        "stakes_level": _optional_text(stakes.get("level")),
        "stakes_label": _optional_text(stakes.get("enjeu_label")) or _optional_text(stakes.get("summary")),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
