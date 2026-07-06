import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app
from app.routes_value import router, value_diagnostics
from app.value.diagnostics import build_value_diagnostics


class ValueDiagnosticsTests(unittest.TestCase):
    def test_router_exposes_diagnostics_endpoint(self):
        self.assertTrue(any(route.path.endswith("/diagnostics") for route in router.routes))

    def test_value_diagnostics_route_delegates_to_builder(self):
        expected = {"ok": True, "status": "ok", "checks": []}
        with patch("app.routes_value.build_value_diagnostics", return_value=expected) as mocked:
            response = value_diagnostics(refresh=1, user={"id": 1})

        mocked.assert_called_once_with(refresh=True)
        self.assertEqual(response, expected)


    def test_diagnostics_endpoint_smoke_with_test_client(self):
        expected = {"ok": True, "status": "ok", "checks": [], "summary": {}}
        app.dependency_overrides[get_current_user] = lambda: {"id": 1, "email": "test@example.com", "is_active": True}
        try:
            with patch("app.routes_value.build_value_diagnostics", return_value=expected) as mocked:
                client = TestClient(app)
                response = client.get("/api/value/diagnostics?refresh=1")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        mocked.assert_called_once_with(refresh=True)
    def test_build_value_diagnostics_reports_degraded_odds_without_blocking_scenarios(self):
        history = pd.DataFrame([
            {
                "Season": "2526",
                "Kickoff": pd.Timestamp("2026-05-16 21:00"),
                "HomeTeam": "Paris SG",
                "AwayTeam": "Marseille",
            }
        ])
        empty_upcoming = pd.DataFrame(columns=["Kickoff", "HomeTeam", "AwayTeam"])
        journee = {"source": "Demo intersaison", "matches": [{"home": "Paris SG", "away": "Marseille"}]}
        stats = SimpleNamespace(db_path="odds.db", total_count=0, by_source={})

        with patch("app.value.diagnostics.ligue1_data.load_history", return_value=history), \
             patch("app.value.diagnostics.ligue1_data.load_upcoming", return_value=empty_upcoming), \
             patch("app.value.diagnostics.ligue1_service.build_journee", return_value=journee), \
             patch("app.value.diagnostics.value_service.snapshot_store_stats", return_value=stats):
            report = build_value_diagnostics(refresh=True)

        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "degraded")
        self.assertTrue(report["summary"]["can_build_scenarios"])
        self.assertFalse(report["summary"]["has_upcoming_fixtures"])
        self.assertTrue(report["summary"]["needs_user_odds_action"])


if __name__ == "__main__":
    unittest.main()

