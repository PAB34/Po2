import copy
import json
import unittest
from unittest.mock import patch

from app.routes_value import ligue1_journee_scenarios, router
from app.value.ligue1_scenarios import (
    build_ligue1_journee_scenarios,
    build_ligue1_match_scenario,
    ligue1_match_to_scenario_payload,
)


def sample_match():
    return {
        "kickoff": "2026-08-14 20:45:00",
        "home": "Paris SG",
        "away": "Marseille",
        "p_home": 61.2,
        "p_draw": 22.0,
        "p_away": 16.8,
        "pick": "Paris SG",
        "pick_outcome": "H",
        "pick_proba": 61.2,
        "confidence": "Moyenne",
        "bookmaker": "ignored test field",
        "derby": "Classique",
        "home_block": {
            "team": "Paris SG",
            "ppg_recent": 2.2,
            "gf_recent": 2.1,
            "ga_recent": 1.1,
            "injuries_count": 1,
            "stakes": {
                "level": "Moyen",
                "enjeu_label": "Europe",
            },
        },
        "away_block": {
            "team": "Marseille",
            "ppg_recent": 1.4,
            "gf_recent": 1.6,
            "ga_recent": 1.3,
            "injuries_count": 2,
            "stakes": {
                "level": "Moyen",
                "enjeu_label": "Europe",
            },
        },
    }


def sample_journee():
    return {
        "source": "test",
        "updated": "06/07/2026 10:00",
        "odds_source": ["Pinnacle"],
        "break": {"detected": True, "label": "Reprise apres treve", "note": "12 jours sans match"},
        "matches": [sample_match()],
    }


class Ligue1ScenarioAdapterTests(unittest.TestCase):
    def test_ligue1_match_to_scenario_payload_uses_only_sporting_fields(self):
        payload = ligue1_match_to_scenario_payload(sample_match(), break_info=sample_journee()["break"])

        self.assertEqual(payload["home"]["team"], "Paris SG")
        self.assertEqual(payload["away"]["team"], "Marseille")
        self.assertEqual(payload["derby"], "Classique")
        self.assertTrue(payload["break_detected"])
        serialized = json.dumps(payload)
        self.assertNotIn("p_home", serialized)
        self.assertNotIn("pick_proba", serialized)
        self.assertNotIn("bookmaker", serialized)
        self.assertNotIn("Pinnacle", serialized)

    def test_market_fields_do_not_change_scenario(self):
        clean = sample_match()
        contaminated = copy.deepcopy(clean)
        contaminated.update({
            "p_home": 1.0,
            "p_draw": 98.0,
            "p_away": 1.0,
            "pick_proba": 98.0,
            "bookmaker": "Other bookmaker",
            "odds": {"home": 9.99},
            "ev": 0.42,
        })

        expected = build_ligue1_match_scenario(clean, break_info=sample_journee()["break"])
        actual = build_ligue1_match_scenario(contaminated, break_info=sample_journee()["break"])

        self.assertEqual(actual, expected)

    def test_build_ligue1_journee_scenarios_returns_reports_without_market_values(self):
        response = build_ligue1_journee_scenarios(sample_journee())

        self.assertEqual(response["count"], 1)
        report = response["matches"][0]["scenario"]
        self.assertIn("Over 1.5", report["coherent_markets"])
        serialized = json.dumps(response)
        self.assertNotIn("p_home", serialized)
        self.assertNotIn("pick_proba", serialized)
        self.assertNotIn("Pinnacle", serialized)

    def test_router_exposes_ligue1_journee_scenario_endpoint(self):
        self.assertTrue(any(route.path.endswith("/scenarios/ligue1/journee") for route in router.routes))

    def test_ligue1_journee_scenario_route_uses_existing_service_payload(self):
        with patch("app.routes_value.ligue1_service.build_journee", return_value=sample_journee()) as mocked:
            response = ligue1_journee_scenarios(refresh=1, user={"id": 1})

        mocked.assert_called_once_with(force=True)
        self.assertEqual(response["count"], 1)
        self.assertEqual(response["matches"][0]["home"], "Paris SG")


if __name__ == "__main__":
    unittest.main()