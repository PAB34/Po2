"""Historically calibrated best-of-3 tennis market estimates."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

import pandas as pd

RANK_MODEL = {"ATP": (0.0287, 0.6527), "WTA": (0.0610, 0.6621)}
TRAIN_START = 2021
TRAIN_END = 2024
SMOOTHING_MATCHES = 100
BAD_SCORE = re.compile(r"RET|W/O|WO\b|DEF|ABD", re.I)
SET_SCORE = re.compile(r"^(\d+)-(\d+)")
OUTCOMES = (
    "over_18_5", "over_19_5", "over_22_5",
    "favorite_cover_2_5", "three_sets", "tiebreak", "favorite_2_0", "favorite_2_1",
)


def _surface(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"clay", "terre"}:
        return "clay"
    if text in {"grass", "gazon"}:
        return "grass"
    return "hard"


def _probability_bin(probability: float) -> int:
    return sum(probability >= threshold for threshold in (0.60, 0.70, 0.80, 0.90))


def _rank_probability(tour: str, winner_points: Any, loser_points: Any) -> tuple[float, bool] | None:
    try:
        winner_points = float(winner_points)
        loser_points = float(loser_points)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(winner_points) or not math.isfinite(loser_points) or winner_points <= 0 or loser_points <= 0:
        return None
    intercept, slope = RANK_MODEL.get(tour, RANK_MODEL["ATP"])
    p = 1 / (1 + math.exp(-(intercept + slope * abs(math.log(winner_points / loser_points)))))
    return p, winner_points >= loser_points


def _score_outcomes(score: Any, favorite_won: bool) -> dict[str, float] | None:
    text = str(score or "").strip()
    if not text or BAD_SCORE.search(text):
        return None
    sets = []
    for token in text.split():
        match = SET_SCORE.match(token)
        if not match:
            continue
        left, right = int(match.group(1)), int(match.group(2))
        if left > 20 or right > 20:
            continue
        sets.append((left, right))
    winner_sets = sum(left > right for left, right in sets)
    loser_sets = sum(right > left for left, right in sets)
    if winner_sets != 2 or loser_sets not in {0, 1}:
        return None
    winner_games = sum(left for left, _ in sets)
    loser_games = sum(right for _, right in sets)
    favorite_margin = (winner_games - loser_games) if favorite_won else (loser_games - winner_games)
    total_games = winner_games + loser_games
    return {
        # Trois seuils de total jeux : 22.5 est le marche bookmaker usuel ; 18.5 et 19.5
        # sont les seuils reellement joues sur les tickets "prend un set + over", qui
        # etaient jusqu'ici evalues sans jamais etre mesures.
        "over_18_5": float(total_games > 18.5),
        "over_19_5": float(total_games > 19.5),
        "over_22_5": float(total_games > 22.5),
        "favorite_cover_2_5": float(favorite_margin > 2.5),
        "three_sets": float(len(sets) == 3),
        "tiebreak": float(any({left, right} == {6, 7} for left, right in sets)),
        "favorite_2_0": float(favorite_won and loser_sets == 0),
        "favorite_2_1": float(favorite_won and loser_sets == 1),
    }


class HistoricalCalibration:
    def __init__(self, history: pd.DataFrame):
        self.records = self._records(history)
        self.global_rates: dict[str, dict[str, float]] = {}
        self.groups: dict[tuple[str, str, int], dict[str, Any]] = {}
        self._fit()

    @staticmethod
    def _records(history: pd.DataFrame) -> list[dict[str, Any]]:
        records = []
        if history is None or history.empty:
            return records
        for row in history.itertuples(index=False):
            date_i = int(getattr(row, "date_i", 0) or 0)
            year = date_i // 10000
            tour = str(getattr(row, "tour", "ATP") or "ATP").upper()
            rank = _rank_probability(tour, getattr(row, "winner_rank_points", None), getattr(row, "loser_rank_points", None))
            if rank is None:
                continue
            probability, favorite_won = rank
            outcomes = _score_outcomes(getattr(row, "score", None), favorite_won)
            if outcomes is None:
                continue
            records.append({"year": year, "tour": tour, "surface": _surface(getattr(row, "surface", None)), "bin": _probability_bin(probability), "probability": probability, **outcomes})
        return records

    def _fit(self) -> None:
        training = [row for row in self.records if TRAIN_START <= row["year"] <= TRAIN_END]
        by_tour: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_group: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
        for row in training:
            by_tour[row["tour"]].append(row)
            by_group[(row["tour"], row["surface"], row["bin"])].append(row)
        for tour, rows in by_tour.items():
            self.global_rates[tour] = {key: sum(row[key] for row in rows) / len(rows) for key in OUTCOMES}
        for key, rows in by_group.items():
            baseline = self.global_rates[key[0]]
            rates = {
                outcome: (sum(row[outcome] for row in rows) + SMOOTHING_MATCHES * baseline[outcome]) / (len(rows) + SMOOTHING_MATCHES)
                for outcome in OUTCOMES
            }
            self.groups[key] = {"rates": rates, "sample": len(rows)}

    def estimate(self, tour: str, surface: str, favorite_probability: float) -> dict[str, Any]:
        tour = str(tour or "ATP").upper()
        key = (tour, _surface(surface), _probability_bin(float(favorite_probability)))
        group = self.groups.get(key)
        rates = dict((group or {}).get("rates") or self.global_rates.get(tour) or {outcome: 0.5 for outcome in OUTCOMES})
        sample = int((group or {}).get("sample") or 0)
        confidence = "elevee" if sample >= 300 else "moyenne" if sample >= 100 else "faible"
        favorite_win_rate = rates["favorite_2_0"] + rates["favorite_2_1"]
        rates["favorite_2_1_share"] = rates["favorite_2_1"] / favorite_win_rate if favorite_win_rate else 0.38
        return {"rates": rates, "sample": sample, "confidence": confidence, "training": f"{TRAIN_START}-{TRAIN_END}"}

    def report(self, test_year: int = 2025) -> dict[str, Any]:
        rows = [row for row in self.records if row["year"] == test_year]
        report: dict[str, Any] = {"year": test_year, "count": len(rows), "markets": {}}
        for outcome in ("over_22_5", "favorite_cover_2_5", "three_sets", "tiebreak", "favorite_2_0"):
            model_errors, baseline_errors = [], []
            for row in rows:
                prediction = self.estimate(row["tour"], row["surface"], row["probability"])["rates"][outcome]
                baseline = self.global_rates.get(row["tour"], {}).get(outcome, 0.5)
                model_errors.append((prediction - row[outcome]) ** 2)
                baseline_errors.append((baseline - row[outcome]) ** 2)
            report["markets"][outcome] = {
                "brier": round(sum(model_errors) / len(model_errors), 4) if model_errors else None,
                "baseline_brier": round(sum(baseline_errors) / len(baseline_errors), 4) if baseline_errors else None,
            }
        return report
