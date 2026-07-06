import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from app.routes_value import ligue1_scenario_backtest, router
from app.value.scenario_backtest import run_scenario_backtest
from app.value.scenario_predictions import ScenarioPrediction, stable_ligue1_event_id
from app.value.service import run_ligue1_scenario_backtest


def prediction(
    home="Paris SG",
    away="Marseille",
    kickoff="2026-08-14 20:45:00",
    coherent_markets=None,
    factors=None,
):
    scenario = {
        "completeness_score": 100,
        "confidence": "Moyenne",
        "main_scenario": "Match potentiellement ouvert",
        "alternative_scenarios": [],
        "coherent_markets": coherent_markets or ["Over 1.5", "BTTS"],
        "avoid_markets": [],
        "missing_data": [],
        "factors": factors or [],
    }
    sporting_input = {
        "home": {"team": home},
        "away": {"team": away},
    }
    return ScenarioPrediction(
        sport="football",
        competition="ligue1",
        event_id=stable_ligue1_event_id(kickoff, home, away),
        home=home,
        away=away,
        kickoff=kickoff,
        predicted_at="2026-07-06T10:00:00Z",
        source="test",
        input_hash="hash",
        sporting_input_json=json.dumps(sporting_input, sort_keys=True),
        scenario_json=json.dumps(scenario, sort_keys=True),
    )


def history():
    return pd.DataFrame([
        {
            "Kickoff": "2026-08-14 20:45:00",
            "HomeTeam": "Paris SG",
            "AwayTeam": "Marseille",
            "FTHG": 2,
            "FTAG": 1,
            "FTR": "H",
        },
        {
            "Kickoff": "2026-08-15 19:00:00",
            "HomeTeam": "Lens",
            "AwayTeam": "Lille",
            "FTHG": 1,
            "FTAG": 1,
            "FTR": "D",
        },
    ])


class ScenarioBacktestTests(unittest.TestCase):
    def test_open_and_btts_signals_are_measured_against_real_score(self):
        result = run_scenario_backtest([prediction()], history())

        self.assertEqual(result.n_predictions, 1)
        self.assertEqual(result.n_matched, 1)
        self.assertEqual(result.n_signals, 2)
        self.assertEqual(result.open_accuracy, 1.0)
        self.assertEqual(result.btts_accuracy, 1.0)
        self.assertIsNone(result.ascendant_accuracy)

    def test_ascendant_double_chance_signal_uses_real_result(self):
        pred = prediction(
            home="Lens",
            away="Lille",
            kickoff="2026-08-15 19:00:00",
            coherent_markets=["Double chance equipe en ascendant"],
            factors=["Ascendant recent cote Lens (ecart forme 0.80 pts/match)."],
        )
        result = run_scenario_backtest([pred], history())

        self.assertEqual(result.n_signals, 1)
        self.assertEqual(result.ascendant_accuracy, 1.0)
        self.assertEqual(result.rows[0].expected, "Lens does not lose")

    def test_unmatched_predictions_are_counted(self):
        pred = prediction(home="A", away="B", kickoff="2026-01-01 20:00:00")
        result = run_scenario_backtest([pred], history())

        self.assertEqual(result.n_predictions, 1)
        self.assertEqual(result.n_matched, 0)
        self.assertEqual(result.unmatched_count, 1)
        self.assertEqual(result.n_signals, 0)

    def test_service_uses_store_predictions_and_history(self):
        store = SimpleNamespace(list_predictions=lambda: [prediction()])
        result = run_ligue1_scenario_backtest(store=store, history=history())

        self.assertEqual(result.source, "ligue1-scenario-predictions")
        self.assertEqual(result.n_matched, 1)

    def test_router_exposes_ligue1_scenario_backtest_endpoint(self):
        self.assertTrue(any(route.path.endswith("/backtests/ligue1/scenarios") for route in router.routes))

    def test_ligue1_scenario_backtest_route_returns_warning_and_rows(self):
        row = SimpleNamespace(
            event_id="event",
            kickoff="2026-08-14",
            home="A",
            away="B",
            signal="open",
            expected="total_goals >= 2",
            actual="2-1 (H)",
            success=True,
        )
        result = SimpleNamespace(
            source="test",
            n_predictions=1,
            n_matched=1,
            unmatched_count=0,
            n_signals=1,
            open_accuracy=1.0,
            btts_accuracy=None,
            ascendant_accuracy=None,
            rows=(row,),
        )
        with patch("app.routes_value.service.run_ligue1_scenario_backtest", return_value=result):
            response = ligue1_scenario_backtest(user={"id": 1})

        self.assertEqual(response["n_signals"], 1)
        self.assertIn("does not use odds", response["warning"])
        self.assertEqual(response["rows"][0]["signal"], "open")


if __name__ == "__main__":
    unittest.main()