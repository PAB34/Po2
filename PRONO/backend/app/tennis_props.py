"""Player-level tennis prop estimates built from historical match statistics."""

from __future__ import annotations

import glob
import math
import re
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

TRAIN_START = 2021
TRAIN_END = 2024
SURFACE_PRIOR_GAMES = 24.0
BASE_PRIOR_GAMES = 16.0
ACE_LINES = {"ATP": (2.5, 4.5, 6.5, 8.5), "WTA": (1.5, 3.5, 5.5, 7.5)}
DF_LINES = (1.5, 2.5, 3.5, 4.5)
BAD_SCORE = re.compile(r"RET|W/O|WO\b|DEF|ABD", re.I)
TIEBREAK = re.compile(r"(?:7-6|6-7)")


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _surface(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"clay", "terre"}:
        return "clay"
    if text in {"grass", "gazon"}:
        return "grass"
    return "hard"


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", text).split())


def _short_key(value: Any) -> str:
    words = _norm(value).split()
    if len(words) < 2:
        return ""
    if len(words[-1]) == 1:
        return f"{words[0]}:{words[-1]}"
    return f"{words[-1]}:{words[0][0]}"


def _nb_probability_at_least(mean: float, dispersion: float, minimum: int) -> float:
    if mean <= 0:
        return 0.0
    dispersion = max(0.35, float(dispersion))
    p = dispersion / (dispersion + mean)
    cumulative = 0.0
    for count in range(max(0, minimum)):
        log_pmf = (
            math.lgamma(count + dispersion) - math.lgamma(dispersion) - math.lgamma(count + 1)
            + dispersion * math.log(p) + count * math.log1p(-p)
        )
        cumulative += math.exp(log_pmf)
    return max(0.0, min(1.0, 1 - cumulative))


def _nb_interval(mean: float, dispersion: float, low: float = 0.10, high: float = 0.90) -> list[int]:
    dispersion = max(0.35, float(dispersion))
    p = dispersion / (dispersion + max(mean, 1e-9))
    cumulative = 0.0
    bounds: list[int] = []
    for count in range(50):
        log_pmf = (
            math.lgamma(count + dispersion) - math.lgamma(dispersion) - math.lgamma(count + 1)
            + dispersion * math.log(p) + count * math.log1p(-p)
        )
        cumulative += math.exp(log_pmf)
        if not bounds and cumulative >= low:
            bounds.append(count)
        if cumulative >= high:
            bounds.append(count)
            break
    return (bounds + [max(1, int(round(mean * 2)))])[:2]


def _poisson_at_least_one(mean: float) -> float:
    return max(0.0, min(1.0, 1 - math.exp(-max(0.0, mean))))


def _confidence(surface_matches: int, total_matches: int) -> str:
    if surface_matches >= 20:
        return "elevee"
    if surface_matches >= 10 or total_matches >= 30:
        return "moyenne"
    return "faible"


class _PropsModel:
    def __init__(self, matches: list[dict[str, Any]]):
        self.matches = matches
        self.player: dict[tuple[str, str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.baseline: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.match_groups: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.aliases: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.dispersion: dict[tuple[str, str, str], float] = {}
        self._fit()

    @staticmethod
    def _add(bucket: dict[str, float], row: dict[str, Any]) -> None:
        bucket["matches"] += 1
        for key in (
            "service_games", "return_games", "aces", "aces_allowed", "double_faults",
            "breaks_conceded", "breaks_made",
        ):
            bucket[key] += float(row.get(key) or 0)

    def _fit(self) -> None:
        count_samples: dict[tuple[str, str, str], list[float]] = defaultdict(list)
        for match in self.matches:
            tour, surface = match["tour"], match["surface"]
            self.match_groups[(tour, surface)]["matches"] += 1
            self.match_groups[(tour, surface)]["tiebreaks"] += float(match["tiebreak"])
            for row in match["players"]:
                player_key = _norm(row["player"])
                if not player_key:
                    continue
                short = _short_key(row["player"])
                if short:
                    self.aliases[(tour, short)].add(player_key)
                for scope in (surface, "all"):
                    self._add(self.player[(tour, scope, player_key)], row)
                    self._add(self.baseline[(tour, scope)], row)
                count_samples[(tour, surface, "aces")].append(row["aces"])
                count_samples[(tour, surface, "double_faults")].append(row["double_faults"])
        for key, values in count_samples.items():
            mean = sum(values) / len(values) if values else 0.0
            variance = sum((value - mean) ** 2 for value in values) / max(1, len(values) - 1)
            dispersion = mean * mean / (variance - mean) if variance > mean + 1e-6 else 20.0
            self.dispersion[key] = max(0.5, min(20.0, dispersion))

    def _resolve(self, tour: str, player: str) -> str | None:
        full = _norm(player)
        if (tour, "all", full) in self.player:
            return full
        aliases = self.aliases.get((tour, _short_key(player)), set())
        return next(iter(aliases)) if len(aliases) == 1 else None

    def _baseline_rate(self, tour: str, surface: str, numerator: str, denominator: str) -> float:
        bucket = self.baseline.get((tour, surface)) or self.baseline.get((tour, "all")) or {}
        den = float(bucket.get(denominator) or 0)
        return float(bucket.get(numerator) or 0) / den if den else 0.0

    def _rate(self, tour: str, surface: str, player_key: str, numerator: str, denominator: str) -> tuple[float, int, int]:
        base = self._baseline_rate(tour, surface, numerator, denominator)
        global_bucket = self.player.get((tour, "all", player_key), {})
        global_den = float(global_bucket.get(denominator) or 0)
        global_rate = ((float(global_bucket.get(numerator) or 0) + BASE_PRIOR_GAMES * base) /
                       (global_den + BASE_PRIOR_GAMES)) if global_den or base else 0.0
        surface_bucket = self.player.get((tour, surface, player_key), {})
        surface_den = float(surface_bucket.get(denominator) or 0)
        rate = ((float(surface_bucket.get(numerator) or 0) + SURFACE_PRIOR_GAMES * global_rate) /
                (surface_den + SURFACE_PRIOR_GAMES)) if surface_den or global_rate else 0.0
        return rate, int(surface_bucket.get("matches") or 0), int(global_bucket.get("matches") or 0)

    def _expected_service_games(self, tour: str, surface: str) -> float:
        bucket = self.baseline.get((tour, surface)) or self.baseline.get((tour, "all")) or {}
        matches = float(bucket.get("matches") or 0)
        return max(7.0, min(16.0, float(bucket.get("service_games") or 0) / matches)) if matches else 10.5

    def _player_prediction(self, tour: str, surface: str, player: str, opponent: str) -> dict[str, Any] | None:
        player_key, opponent_key = self._resolve(tour, player), self._resolve(tour, opponent)
        if not player_key:
            return None
        base_ace = self._baseline_rate(tour, surface, "aces", "service_games")
        ace_rate, surface_matches, total_matches = self._rate(tour, surface, player_key, "aces", "service_games")
        if opponent_key:
            allowed_rate, _, _ = self._rate(tour, surface, opponent_key, "aces_allowed", "return_games")
            ace_rate = math.sqrt(max(ace_rate, 1e-6) * max(allowed_rate, 1e-6))
        elif not ace_rate:
            ace_rate = base_ace

        df_rate, _, _ = self._rate(tour, surface, player_key, "double_faults", "service_games")
        conceded_rate, _, _ = self._rate(tour, surface, player_key, "breaks_conceded", "service_games")
        created_rate, _, _ = self._rate(tour, surface, player_key, "breaks_made", "return_games")
        if opponent_key:
            opponent_created, _, _ = self._rate(tour, surface, opponent_key, "breaks_made", "return_games")
            opponent_conceded, _, _ = self._rate(tour, surface, opponent_key, "breaks_conceded", "service_games")
            conceded_rate = math.sqrt(max(conceded_rate, 1e-6) * max(opponent_created, 1e-6))
            created_rate = math.sqrt(max(created_rate, 1e-6) * max(opponent_conceded, 1e-6))

        service_games = self._expected_service_games(tour, surface)
        ace_mean = max(0.0, min(20.0, ace_rate * service_games))
        df_mean = max(0.0, min(12.0, df_rate * service_games))
        conceded_mean = max(0.0, min(6.0, conceded_rate * service_games))
        created_mean = max(0.0, min(6.0, created_rate * service_games))
        ace_dispersion = self.dispersion.get((tour, surface, "aces"), 5.0)
        df_dispersion = self.dispersion.get((tour, surface, "double_faults"), 5.0)
        return {
            "player": player,
            "sample_surface": surface_matches,
            "sample_total": total_matches,
            "confidence": _confidence(surface_matches, total_matches),
            "service_games_expected": round(service_games, 1),
            "aces_expected": round(ace_mean, 1),
            "aces_interval": _nb_interval(ace_mean, ace_dispersion),
            "aces_thresholds": [
                {"line": line, "over": round(_nb_probability_at_least(ace_mean, ace_dispersion, int(line + 0.5)) * 100)}
                for line in ACE_LINES.get(tour, ACE_LINES["ATP"])
            ],
            "double_faults_expected": round(df_mean, 1),
            "double_faults_interval": _nb_interval(df_mean, df_dispersion),
            "double_faults_thresholds": [
                {"line": line, "over": round(_nb_probability_at_least(df_mean, df_dispersion, int(line + 0.5)) * 100)}
                for line in DF_LINES
            ],
            "hold_probability": round((1 - conceded_rate) * 100, 1),
            "broken_probability": round(_poisson_at_least_one(conceded_mean) * 100),
            "breaks_expected": round(created_mean, 1),
            "break_probability": round(_poisson_at_least_one(created_mean) * 100),
        }

    def predict(self, tour: str, surface: str, player1: str, player2: str) -> dict[str, Any]:
        tour, surface = str(tour or "ATP").upper(), _surface(surface)
        p1 = self._player_prediction(tour, surface, player1, player2)
        p2 = self._player_prediction(tour, surface, player2, player1)
        baseline_hold = 1 - self._baseline_rate(tour, surface, "breaks_conceded", "service_games")
        group = self.match_groups.get((tour, surface), {})
        group_matches = int(group.get("matches") or 0)
        baseline_tb = float(group.get("tiebreaks") or 0) / group_matches if group_matches else 0.20
        if p1 and p2:
            average_hold = (p1["hold_probability"] + p2["hold_probability"]) / 200
            tiebreak = baseline_tb * math.exp(4.0 * (average_hold - baseline_hold))
        else:
            tiebreak = baseline_tb
        return {
            "surface": surface,
            "players": [p1, p2],
            "tiebreak_probability": round(max(0.03, min(0.65, tiebreak)) * 100),
            "sample": group_matches,
            "source": "historique match par match",
        }

    def baseline_prediction(self, tour: str, surface: str) -> dict[str, float]:
        tour, surface = str(tour).upper(), _surface(surface)
        games = self._expected_service_games(tour, surface)
        ace_mean = self._baseline_rate(tour, surface, "aces", "service_games") * games
        df_mean = self._baseline_rate(tour, surface, "double_faults", "service_games") * games
        break_mean = self._baseline_rate(tour, surface, "breaks_conceded", "service_games") * games
        ace_dispersion = self.dispersion.get((tour, surface, "aces"), 5.0)
        df_dispersion = self.dispersion.get((tour, surface, "double_faults"), 5.0)
        group = self.match_groups.get((tour, surface), {})
        group_matches = int(group.get("matches") or 0)
        ace_minimum = 5 if tour == "ATP" else 4
        return {
            "aces_reference": _nb_probability_at_least(ace_mean, ace_dispersion, ace_minimum),
            "double_faults_3_plus": _nb_probability_at_least(df_mean, df_dispersion, 3),
            "broken": _poisson_at_least_one(break_mean),
            "break_1_plus": _poisson_at_least_one(break_mean),
            "tiebreak": float(group.get("tiebreaks") or 0) / group_matches if group_matches else 0.2,
        }


class TennisPropsEngine:
    def __init__(self, dataset_dir: Path):
        self.dataset_dir = Path(dataset_dir)
        self.matches = self._load_matches()
        self.model = _PropsModel(self.matches)
        self._validation_cache: dict[int, dict[str, Any]] = {}

    def _load_matches(self) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        columns = {
            "tourney_date", "surface", "winner_name", "loser_name", "score",
            "w_ace", "w_df", "w_SvGms", "w_bpSaved", "w_bpFaced",
            "l_ace", "l_df", "l_SvGms", "l_bpSaved", "l_bpFaced",
        }
        for tour, directory in (("ATP", "tml"), ("WTA", "tml_wta")):
            for path in glob.glob(str(self.dataset_dir / directory / "*.csv")):
                try:
                    frame = pd.read_csv(path, usecols=lambda column: column in columns, dtype=str)
                except (OSError, ValueError):
                    continue
                for row in frame.to_dict("records"):
                    parsed = self._parse_match(tour, row)
                    if parsed:
                        matches.append(parsed)
        return matches

    @staticmethod
    def _parse_match(tour: str, row: dict[str, Any]) -> dict[str, Any] | None:
        score = str(row.get("score") or "")
        if not score or BAD_SCORE.search(score):
            return None
        values = {key: _float(row.get(key)) for key in (
            "w_ace", "w_df", "w_SvGms", "w_bpSaved", "w_bpFaced",
            "l_ace", "l_df", "l_SvGms", "l_bpSaved", "l_bpFaced",
        )}
        if any(values[key] is None for key in ("w_ace", "w_df", "w_SvGms", "l_ace", "l_df", "l_SvGms")):
            return None
        if values["w_SvGms"] <= 0 or values["l_SvGms"] <= 0:
            return None
        winner_breaks = max(0.0, (values["w_bpFaced"] or 0) - (values["w_bpSaved"] or 0))
        loser_breaks = max(0.0, (values["l_bpFaced"] or 0) - (values["l_bpSaved"] or 0))
        try:
            date_i = int(float(row.get("tourney_date") or 0))
        except (TypeError, ValueError):
            date_i = 0
        if date_i > int(date.today().strftime("%Y%m%d")):
            return None
        winner, loser = str(row.get("winner_name") or "").strip(), str(row.get("loser_name") or "").strip()
        if not winner or not loser:
            return None
        return {
            "year": date_i // 10000,
            "date": date_i,
            "tour": tour,
            "surface": _surface(row.get("surface")),
            "tiebreak": bool(TIEBREAK.search(score)),
            "players": [
                {
                    "player": winner, "service_games": values["w_SvGms"], "return_games": values["l_SvGms"],
                    "aces": values["w_ace"], "aces_allowed": values["l_ace"], "double_faults": values["w_df"],
                    "breaks_conceded": winner_breaks, "breaks_made": loser_breaks,
                },
                {
                    "player": loser, "service_games": values["l_SvGms"], "return_games": values["w_SvGms"],
                    "aces": values["l_ace"], "aces_allowed": values["w_ace"], "double_faults": values["l_df"],
                    "breaks_conceded": loser_breaks, "breaks_made": winner_breaks,
                },
            ],
        }

    def predict(self, tour: str, surface: str, player1: str, player2: str) -> dict[str, Any]:
        prediction = self.model.predict(tour, surface, player1, player2)
        prediction["validation"] = self.validation_report(2025)["markets"]
        return prediction

    def validation_report(self, year: int = 2025) -> dict[str, Any]:
        if year in self._validation_cache:
            return self._validation_cache[year]
        training = [match for match in self.matches if TRAIN_START <= match["year"] <= TRAIN_END]
        testing = [match for match in self.matches if match["year"] == year]
        model = _PropsModel(training)
        errors: dict[str, list[float]] = defaultdict(list)
        baseline_errors: dict[str, list[float]] = defaultdict(list)
        coverage = 0
        for match in testing:
            p1_name, p2_name = match["players"][0]["player"], match["players"][1]["player"]
            prediction = model.predict(match["tour"], match["surface"], p1_name, p2_name)
            baseline = model.baseline_prediction(match["tour"], match["surface"])
            players = prediction["players"]
            if all(players):
                coverage += 1
                for actual, predicted in zip(match["players"], players):
                    ace_line = 4.5 if match["tour"] == "ATP" else 3.5
                    ace_minimum = 5 if match["tour"] == "ATP" else 4
                    events = {
                        "aces_reference": float(actual["aces"] >= ace_minimum),
                        "double_faults_3_plus": float(actual["double_faults"] >= 3),
                        "broken": float(actual["breaks_conceded"] >= 1),
                        "break_1_plus": float(actual["breaks_made"] >= 1),
                    }
                    probabilities = {
                        "aces_reference": next(item["over"] for item in predicted["aces_thresholds"] if item["line"] == ace_line) / 100,
                        "double_faults_3_plus": next(item["over"] for item in predicted["double_faults_thresholds"] if item["line"] == 2.5) / 100,
                        "broken": predicted["broken_probability"] / 100,
                        "break_1_plus": predicted["break_probability"] / 100,
                    }
                    for key, actual_value in events.items():
                        errors[key].append((probabilities[key] - actual_value) ** 2)
                        baseline_errors[key].append((baseline[key] - actual_value) ** 2)
            tie_actual = float(match["tiebreak"])
            tie_prediction = prediction["tiebreak_probability"] / 100
            errors["tiebreak"].append((tie_prediction - tie_actual) ** 2)
            baseline_errors["tiebreak"].append((baseline["tiebreak"] - tie_actual) ** 2)
        markets = {}
        for key in ("aces_reference", "double_faults_3_plus", "broken", "break_1_plus", "tiebreak"):
            model_error = sum(errors[key]) / len(errors[key]) if errors[key] else None
            baseline_error = sum(baseline_errors[key]) / len(baseline_errors[key]) if baseline_errors[key] else None
            markets[key] = {
                "sample": len(errors[key]),
                "brier": round(model_error, 4) if model_error is not None else None,
                "baseline_brier": round(baseline_error, 4) if baseline_error is not None else None,
                "validated": bool(model_error is not None and baseline_error is not None and model_error <= baseline_error),
            }
        report = {"year": year, "matches": len(testing), "covered_matches": coverage, "markets": markets}
        self._validation_cache[year] = report
        return report