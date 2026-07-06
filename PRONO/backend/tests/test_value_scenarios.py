import unittest

from fastapi import HTTPException

from app.routes_value import football_scenario, router
from app.value.scenarios import (
    MatchScenarioInput,
    TeamScenarioInput,
    assert_no_odds_features,
    build_match_scenario,
    scenario_from_mapping,
)


class ScenarioEngineTests(unittest.TestCase):
    def test_open_match_scenario_from_sporting_data(self):
        report = build_match_scenario(MatchScenarioInput(
            home=TeamScenarioInput(
                team="Paris SG",
                ppg_recent=2.2,
                gf_recent=2.1,
                ga_recent=1.1,
                injuries_count=1,
                stakes_level="Moyen",
            ),
            away=TeamScenarioInput(
                team="Marseille",
                ppg_recent=1.4,
                gf_recent=1.6,
                ga_recent=1.3,
                injuries_count=2,
                stakes_level="Moyen",
            ),
        ))
        self.assertGreaterEqual(report.completeness_score, 90)
        self.assertIn("Over 1.5", report.coherent_markets)
        self.assertIn("BTTS", report.coherent_markets)
        self.assertIn("Match potentiellement ouvert", report.main_scenario)
        self.assertEqual(report.missing_data, ())

    def test_incomplete_data_degrades_completeness(self):
        report = build_match_scenario(MatchScenarioInput(
            home=TeamScenarioInput(team="A", ppg_recent=1.5),
            away=TeamScenarioInput(team="B"),
        ))
        self.assertLess(report.completeness_score, 60)
        self.assertEqual(report.confidence, "Faible")
        self.assertIn("Scenario incomplet", report.main_scenario)
        self.assertIn("away.gf_recent", report.missing_data)

    def test_volatile_context_adds_avoid_markets(self):
        report = build_match_scenario(MatchScenarioInput(
            home=TeamScenarioInput(team="Lens", ppg_recent=1.7, gf_recent=1.2, ga_recent=0.9, injuries_count=5, stakes_level="Fort", stakes_label="Europe"),
            away=TeamScenarioInput(team="Lille", ppg_recent=1.6, gf_recent=1.1, ga_recent=0.9, injuries_count=1, stakes_level="Moyen"),
            derby="Derby du Nord",
            break_detected=True,
            break_label="Reprise apres treve internationale",
        ))
        self.assertEqual(report.confidence, "A nuancer")
        self.assertIn("Handicap favori lourd", report.avoid_markets)
        self.assertIn("Confiance forte sans confirmation rythme/compos", report.avoid_markets)
        self.assertTrue(any("Lens" in factor for factor in report.factors))

    def test_rejects_odds_features_recursively(self):
        with self.assertRaisesRegex(ValueError, "Odds feature forbidden"):
            assert_no_odds_features({"home": {"team": "A"}, "nested": {"odds": 1.75}})

    def test_mapping_entrypoint_refuses_cotes(self):
        with self.assertRaisesRegex(ValueError, "Odds feature forbidden"):
            scenario_from_mapping({
                "home": {"team": "A", "ppg_recent": 2.0, "gf_recent": 1.8, "ga_recent": 1.0, "injuries_count": 1, "stakes_level": "Moyen"},
                "away": {"team": "B", "ppg_recent": 1.0, "gf_recent": 1.0, "ga_recent": 1.5, "injuries_count": 2, "stakes_level": "Faible"},
                "cote": 1.5,
            })

    def test_mapping_entrypoint_builds_report(self):
        report = scenario_from_mapping({
            "home": {"team": "A", "ppg_recent": 2.0, "gf_recent": 1.8, "ga_recent": 1.0, "injuries_count": 1, "stakes_level": "Moyen"},
            "away": {"team": "B", "ppg_recent": 1.0, "gf_recent": 1.5, "ga_recent": 1.2, "injuries_count": 2, "stakes_level": "Faible"},
            "manual_context": ["terrain neutre"],
        })
        self.assertIn("Note manuelle", " ".join(report.factors))
        self.assertIn("Double chance equipe en ascendant", report.coherent_markets)

    def test_weighted_completeness_marks_missing_identity_as_blocking(self):
        report = build_match_scenario(MatchScenarioInput(
            home=TeamScenarioInput(team="", ppg_recent=2.0, gf_recent=1.8, ga_recent=1.0, injuries_count=1, stakes_level="Moyen"),
            away=TeamScenarioInput(team="B", ppg_recent=1.0, gf_recent=1.1, ga_recent=1.4, injuries_count=2, stakes_level="Faible"),
        ))

        self.assertEqual(report.confidence, "Bloquee")
        self.assertIn("home.team", report.blocking_missing_data)
        self.assertIn("Scenario bloque", report.main_scenario)

    def test_missing_goal_profile_penalizes_more_than_context(self):
        missing_goal = build_match_scenario(MatchScenarioInput(
            home=TeamScenarioInput(team="A", ppg_recent=1.8, gf_recent=None, ga_recent=1.0, injuries_count=1, stakes_level="Moyen"),
            away=TeamScenarioInput(team="B", ppg_recent=1.2, gf_recent=1.3, ga_recent=1.2, injuries_count=2, stakes_level="Faible"),
        ))
        missing_context = build_match_scenario(MatchScenarioInput(
            home=TeamScenarioInput(team="A", ppg_recent=1.8, gf_recent=1.5, ga_recent=1.0, injuries_count=1, stakes_level=None),
            away=TeamScenarioInput(team="B", ppg_recent=1.2, gf_recent=1.3, ga_recent=1.2, injuries_count=2, stakes_level="Faible"),
        ))

        self.assertLess(missing_goal.completeness_score, missing_context.completeness_score)
        self.assertIn("home.gf_recent", missing_goal.degrading_missing_data)
        self.assertIn("BTTS/Over sans profil buts complet", missing_goal.avoid_markets)

    def test_missing_form_data_degrades_ascendant_reading(self):
        report = build_match_scenario(MatchScenarioInput(
            home=TeamScenarioInput(team="A", ppg_recent=None, gf_recent=1.8, ga_recent=1.0, injuries_count=1, stakes_level="Moyen"),
            away=TeamScenarioInput(team="B", ppg_recent=1.0, gf_recent=1.2, ga_recent=1.3, injuries_count=2, stakes_level="Faible"),
        ))

        self.assertIn("home.ppg_recent", report.degrading_missing_data)
        self.assertIn("Double chance ascendant sans forme recente complete", report.avoid_markets)
        self.assertNotIn("Double chance equipe en ascendant", report.coherent_markets)
class ScenarioRouteTests(unittest.TestCase):
    def test_router_exposes_private_football_scenario_endpoint(self):
        self.assertTrue(any(route.path.endswith("/scenarios/football") for route in router.routes))

    def test_football_scenario_endpoint_returns_report(self):
        response = football_scenario({
            "home": {
                "team": "Paris SG",
                "ppg_recent": 2.2,
                "gf_recent": 2.1,
                "ga_recent": 1.1,
                "injuries_count": 1,
                "stakes_level": "Moyen",
            },
            "away": {
                "team": "Marseille",
                "ppg_recent": 1.4,
                "gf_recent": 1.6,
                "ga_recent": 1.3,
                "injuries_count": 2,
                "stakes_level": "Moyen",
            },
        }, user={"id": 1})

        self.assertEqual(response["confidence"], "Moyenne")
        self.assertIn("Over 1.5", response["coherent_markets"])
        self.assertEqual(response["missing_data"], [])
        self.assertEqual(response["blocking_missing_data"], [])
        self.assertEqual(response["degrading_missing_data"], [])

    def test_football_scenario_endpoint_rejects_odds_features(self):
        with self.assertRaises(HTTPException) as ctx:
            football_scenario({
                "home": {"team": "A"},
                "away": {"team": "B"},
                "bookmaker": "forbidden",
            }, user={"id": 1})

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Odds feature forbidden", ctx.exception.detail)

if __name__ == "__main__":
    unittest.main()
