"""Backtest odds-blind scenario predictions against real football results."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import pandas as pd

from .scenario_predictions import ScenarioPrediction, stable_ligue1_event_id


@dataclass(frozen=True)
class ScenarioSignalResult:
    event_id: str
    kickoff: str
    home: str
    away: str
    signal: str
    expected: str
    actual: str
    success: bool


@dataclass(frozen=True)
class ScenarioBacktestResult:
    source: str
    n_predictions: int
    n_matched: int
    unmatched_count: int
    n_signals: int
    open_accuracy: float | None
    btts_accuracy: float | None
    ascendant_accuracy: float | None
    rows: tuple[ScenarioSignalResult, ...]


def run_scenario_backtest(
    predictions: Sequence[ScenarioPrediction],
    history: pd.DataFrame,
    source: str = "scenario_predictions",
) -> ScenarioBacktestResult:
    required = ["Kickoff", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
    missing = [column for column in required if column not in history.columns]
    if missing:
        raise ValueError(f"Missing scenario backtest column(s): {', '.join(missing)}")

    actuals = _actual_result_index(history)
    rows: list[ScenarioSignalResult] = []
    matched_events: set[str] = set()
    for prediction in predictions:
        actual = actuals.get(prediction.event_id) or actuals.get(
            stable_ligue1_event_id(prediction.kickoff, prediction.home, prediction.away)
        )
        if actual is None:
            continue
        matched_events.add(prediction.event_id)
        scenario = prediction.to_dict()["scenario"]
        rows.extend(_evaluate_prediction(prediction, scenario, actual))

    return ScenarioBacktestResult(
        source=source,
        n_predictions=len(predictions),
        n_matched=len(matched_events),
        unmatched_count=len(predictions) - len(matched_events),
        n_signals=len(rows),
        open_accuracy=_accuracy(rows, "open"),
        btts_accuracy=_accuracy(rows, "btts"),
        ascendant_accuracy=_accuracy(rows, "ascendant_double_chance"),
        rows=tuple(rows),
    )


def _actual_result_index(history: pd.DataFrame) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for _, row in history.iterrows():
        try:
            home_goals = int(row["FTHG"])
            away_goals = int(row["FTAG"])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(float(home_goals)) or not math.isfinite(float(away_goals)):
            continue
        home = str(row["HomeTeam"])
        away = str(row["AwayTeam"])
        kickoff = str(row["Kickoff"])
        event_id = stable_ligue1_event_id(kickoff, home, away)
        out[event_id] = {
            "home": home,
            "away": away,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "ftr": str(row["FTR"]),
        }
    return out


def _evaluate_prediction(
    prediction: ScenarioPrediction,
    scenario: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> list[ScenarioSignalResult]:
    rows: list[ScenarioSignalResult] = []
    markets = set(str(value) for value in scenario.get("coherent_markets", []))
    actual_text = _actual_text(actual)
    home_goals = int(actual["home_goals"])
    away_goals = int(actual["away_goals"])

    if "Over 1.5" in markets:
        rows.append(ScenarioSignalResult(
            event_id=prediction.event_id,
            kickoff=prediction.kickoff,
            home=prediction.home,
            away=prediction.away,
            signal="open",
            expected="total_goals >= 2",
            actual=actual_text,
            success=(home_goals + away_goals) >= 2,
        ))
    if "BTTS" in markets:
        rows.append(ScenarioSignalResult(
            event_id=prediction.event_id,
            kickoff=prediction.kickoff,
            home=prediction.home,
            away=prediction.away,
            signal="btts",
            expected="both teams score",
            actual=actual_text,
            success=home_goals > 0 and away_goals > 0,
        ))

    ascendant_team = _ascendant_team(scenario)
    if ascendant_team:
        rows.append(ScenarioSignalResult(
            event_id=prediction.event_id,
            kickoff=prediction.kickoff,
            home=prediction.home,
            away=prediction.away,
            signal="ascendant_double_chance",
            expected=f"{ascendant_team} does not lose",
            actual=actual_text,
            success=_team_did_not_lose(ascendant_team, prediction.home, prediction.away, str(actual["ftr"])),
        ))
    return rows


def _ascendant_team(scenario: Mapping[str, Any]) -> str | None:
    if "Double chance equipe en ascendant" not in set(str(v) for v in scenario.get("coherent_markets", [])):
        return None
    for factor in scenario.get("factors", []):
        text = str(factor)
        marker = "Ascendant recent cote "
        if marker in text:
            rest = text.split(marker, 1)[1]
            return rest.split(" (", 1)[0].strip() or None
    return None


def _team_did_not_lose(team: str, home: str, away: str, ftr: str) -> bool:
    if team == home:
        return ftr in {"H", "D"}
    if team == away:
        return ftr in {"A", "D"}
    return False


def _accuracy(rows: Sequence[ScenarioSignalResult], signal: str) -> float | None:
    scoped = [row for row in rows if row.signal == signal]
    if not scoped:
        return None
    return sum(1 for row in scoped if row.success) / len(scoped)


def _actual_text(actual: Mapping[str, Any]) -> str:
    return f"{actual['home_goals']}-{actual['away_goals']} ({actual['ftr']})"