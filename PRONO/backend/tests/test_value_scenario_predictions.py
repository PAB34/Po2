import copy
import gc
import os
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from app.routes_value import persist_ligue1_journee_scenario_predictions, router
from app.value.scenario_predictions import (
    ScenarioPredictionStore,
    predictions_from_ligue1_journee,
)
from app.value.service import persist_ligue1_journee_scenario_predictions as persist_predictions_service


def sample_match():
    return {
        "kickoff": "2026-08-14 20:45:00",
        "home": "Paris SG",
        "away": "Marseille",
        "p_home": 61.2,
        "p_draw": 22.0,
        "p_away": 16.8,
        "pick": "Paris SG",
        "pick_proba": 61.2,
        "bookmaker": "ignored",
        "derby": "Classique",
        "home_block": {
            "team": "Paris SG",
            "ppg_recent": 2.2,
            "gf_recent": 2.1,
            "ga_recent": 1.1,
            "injuries_count": 1,
            "stakes": {"level": "Moyen", "enjeu_label": "Europe"},
        },
        "away_block": {
            "team": "Marseille",
            "ppg_recent": 1.4,
            "gf_recent": 1.6,
            "ga_recent": 1.3,
            "injuries_count": 2,
            "stakes": {"level": "Moyen", "enjeu_label": "Europe"},
        },
    }


def sample_journee():
    return {
        "source": "test",
        "updated": "06/07/2026 10:00",
        "odds_source": ["Pinnacle"],
        "break": {"detected": False},
        "matches": [sample_match()],
    }


class ScenarioPredictionTests(unittest.TestCase):
    def test_predictions_from_ligue1_journee_hashes_sporting_input_only(self):
        clean = sample_journee()
        contaminated = copy.deepcopy(clean)
        contaminated["odds_source"] = ["Other"]
        contaminated["matches"][0].update({
            "p_home": 1.0,
            "p_draw": 98.0,
            "p_away": 1.0,
            "pick_proba": 98.0,
            "bookmaker": "Other bookmaker",
            "odds": {"home": 9.99},
            "ev": 0.42,
        })

        first = predictions_from_ligue1_journee(clean, predicted_at="2026-07-06T10:00:00Z")
        second = predictions_from_ligue1_journee(contaminated, predicted_at="2026-07-06T10:00:00Z")

        self.assertEqual(first[0].input_hash, second[0].input_hash)
        self.assertEqual(first[0].sporting_input_json, second[0].sporting_input_json)
        self.assertEqual(first[0].scenario_json, second[0].scenario_json)

    def test_store_inserts_and_deduplicates_predictions(self):
        db_path = os.path.abspath(f"scenario_predictions_test_{uuid.uuid4().hex}.db")
        try:
            store = ScenarioPredictionStore(db_path)
            predictions = predictions_from_ligue1_journee(sample_journee(), predicted_at="2026-07-06T10:00:00Z")

            self.assertEqual(store.insert_many(predictions), 1)
            self.assertEqual(store.insert_many(predictions), 0)
            self.assertEqual(store.count(), 1)
            stored = store.list_predictions()
            self.assertEqual(stored[0].home, "Paris SG")
            self.assertIn("Over 1.5", stored[0].to_dict()["scenario"]["coherent_markets"])
        finally:
            store = None
            gc.collect()
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except PermissionError:
                    pass

    def test_service_persists_ligue1_journee_predictions(self):
        db_path = os.path.abspath(f"scenario_predictions_service_test_{uuid.uuid4().hex}.db")
        try:
            store = ScenarioPredictionStore(db_path)
            first = persist_predictions_service(
                sample_journee(),
                predicted_at="2026-07-06T10:00:00Z",
                store=store,
            )
            second = persist_predictions_service(
                sample_journee(),
                predicted_at="2026-07-06T10:00:00Z",
                store=store,
            )

            self.assertEqual(first.generated_count, 1)
            self.assertEqual(first.inserted_count, 1)
            self.assertEqual(second.inserted_count, 0)
            self.assertEqual(first.db_path, db_path)
        finally:
            store = None
            gc.collect()
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except PermissionError:
                    pass

    def test_router_exposes_ligue1_prediction_persistence_endpoint(self):
        self.assertTrue(any(route.path.endswith("/scenarios/ligue1/journee/predictions") for route in router.routes))

    def test_prediction_route_uses_ligue1_payload_and_persistence_service(self):
        result = SimpleNamespace(
            source="ligue1-journee",
            predicted_at="2026-07-06T10:00:00Z",
            generated_count=1,
            inserted_count=1,
            db_path="test.db",
            predictions=(),
        )
        with patch("app.routes_value.ligue1_service.build_journee", return_value=sample_journee()) as build_mock:
            with patch("app.routes_value.service.persist_ligue1_journee_scenario_predictions", return_value=result) as persist_mock:
                response = persist_ligue1_journee_scenario_predictions(refresh=1, user={"id": 1})

        build_mock.assert_called_once_with(force=True)
        persist_mock.assert_called_once()
        self.assertEqual(response["inserted_count"], 1)


if __name__ == "__main__":
    unittest.main()