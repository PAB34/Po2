import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.routes_value import ligue1_ticket_families, router
from app.value.betting_completeness import BettingCompletenessAssessment
from app.value.scenario_predictions import ScenarioPrediction
from app.value.service import build_ligue1_ticket_family_report
from app.value.ticket_families import build_ticket_family_candidates


def prediction(score=95, markets=None, avoid=None, factors=None):
    scenario = {
        "completeness_score": score,
        "confidence": "Moyenne",
        "main_scenario": "Match potentiellement ouvert",
        "alternative_scenarios": [],
        "coherent_markets": markets or ["Over 1.5", "BTTS", "Equipe favorite marque", "Double chance equipe en ascendant"],
        "avoid_markets": avoid or [],
        "missing_data": [],
        "blocking_missing_data": [],
        "degrading_missing_data": [],
        "factors": factors or ["Ascendant recent cote Paris SG (ecart forme 0.80 pts/match)."],
    }
    return ScenarioPrediction(
        sport="football",
        competition="ligue1",
        event_id="event-1",
        home="Paris SG",
        away="Marseille",
        kickoff="2026-08-14 20:45:00",
        predicted_at="2026-08-14T10:00:00Z",
        source="test",
        input_hash="hash",
        sporting_input_json=json.dumps({"home": {"team": "Paris SG"}, "away": {"team": "Marseille"}}, sort_keys=True),
        scenario_json=json.dumps(scenario, sort_keys=True),
    )


def betting(status="complete"):
    return BettingCompletenessAssessment(
        score=100 if status == "complete" else 60,
        status=status,
        snapshot_count=6,
        decision_snapshot_count=6 if status != "blocked" else 0,
        closing_snapshot_count=6,
        bookmaker_count=2,
        available_markets=("1x2",),
        required_markets=("1x2",),
        missing_data=() if status == "complete" else ("snapshot_before_decision",),
        blocking_missing_data=("snapshot_before_decision",) if status == "blocked" else (),
        degrading_missing_data=("bookmaker_diversity",) if status == "degraded" else (),
    )


class TicketFamilyTests(unittest.TestCase):
    def test_builds_safe_buts_and_fun_simple_families(self):
        report = build_ticket_family_candidates([prediction()])

        self.assertEqual(report.n_predictions, 1)
        self.assertEqual({candidate.family for candidate in report.candidates}, {"safe", "buts", "fun_simple"})
        self.assertTrue(all("joueurs" not in candidate.rationale.lower() for candidate in report.candidates))
        self.assertIn("research groupings", report.warnings[0])

    def test_filters_low_sporting_completeness(self):
        report = build_ticket_family_candidates([prediction(score=55)], min_sporting_completeness=70)

        self.assertEqual(report.n_candidates, 0)

    def test_avoid_markets_prevent_unsupported_goal_family(self):
        report = build_ticket_family_candidates([
            prediction(markets=["Over 1.5", "BTTS"], avoid=["BTTS/Over sans profil buts complet"])
        ])

        self.assertEqual(report.n_candidates, 0)

    def test_betting_readiness_can_block_candidates(self):
        report = build_ticket_family_candidates(
            [prediction()],
            betting_completeness_by_event={"event-1": betting(status="blocked")},
            require_betting_ready=True,
        )

        self.assertEqual(report.n_candidates, 0)

    def test_degraded_betting_marks_candidate_readiness(self):
        report = build_ticket_family_candidates(
            [prediction(markets=["Over 1.5"])],
            betting_completeness_by_event={"event-1": betting(status="degraded")},
        )

        self.assertEqual(report.candidates[0].readiness, "betting_degraded")
        self.assertIn("betting:bookmaker_diversity", report.candidates[0].degrading_reasons)

    def test_service_uses_prediction_store(self):
        prediction_store = SimpleNamespace(list_predictions=lambda: [prediction(markets=["Over 1.5"])])
        report = build_ligue1_ticket_family_report(prediction_store=prediction_store)

        self.assertEqual(report.source, "ligue1-ticket-families")
        self.assertEqual(report.n_candidates, 1)

    def test_router_exposes_ligue1_ticket_families_endpoint(self):
        self.assertTrue(any(route.path.endswith("/ticket-families/ligue1") for route in router.routes))

    def test_ligue1_ticket_families_route_returns_candidates(self):
        candidate = SimpleNamespace(
            family="buts",
            event_id="event-1",
            kickoff="2026-08-14",
            home="Paris SG",
            away="Marseille",
            markets=("Over 1.5",),
            rationale="test",
            risk_level="medium",
            readiness="sporting_ready",
            sporting_completeness_score=95,
            betting_completeness_score=None,
            blocking_reasons=(),
            degrading_reasons=(),
        )
        result = SimpleNamespace(
            source="test",
            n_predictions=1,
            n_candidates=1,
            min_sporting_completeness=70,
            warnings=("warning",),
            candidates=(candidate,),
        )
        with patch("app.routes_value.service.build_ligue1_ticket_family_report", return_value=result) as mocked:
            response = ligue1_ticket_families(
                min_sporting_completeness=70,
                require_betting_ready=False,
                decision_at=None,
                user={"id": 1},
            )

        mocked.assert_called_once_with(
            min_sporting_completeness=70,
            require_betting_ready=False,
            decision_at=None,
        )
        self.assertEqual(response["n_candidates"], 1)
        self.assertEqual(response["candidates"][0]["family"], "buts")


if __name__ == "__main__":
    unittest.main()