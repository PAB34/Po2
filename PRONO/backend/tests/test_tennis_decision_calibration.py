import unittest

from app.tennis_decision_calibration import (
    DecisionRecord,
    records_from_export_payload,
    run_decision_calibration,
    status_summary_for_row,
)


def record(i, won, decision="Vigilance forte", concordance="Conflit fort", market=65.0):
    return DecisionRecord(
        match_id=f"m-{i}", date="2026-01-01", circuit="ATP", surface="clay",
        favorite="Favorite", market_probability=market, elo_probability=55.0,
        elo_gap=-10.0, decision=decision, concordance=concordance,
        cycle_favorite="alerte forme", fatigue_favorite="charge lourde",
        cycle_opponent="montee", fatigue_opponent="controlee",
        favorite_odds=1.54, outsider_odds=2.60,
        winner="Favorite" if won else "Opponent", favorite_won=won,
    )


class TennisDecisionCalibrationTests(unittest.TestCase):
    def test_significant_bucket_compares_realized_rate_to_market(self):
        records = [record(i, i < 30) for i in range(60)]
        report = run_decision_calibration(records, min_sample=50)
        bucket = next(item for item in report["primary"] if item["bucket"] == "Vigilance forte x Conflit fort")
        self.assertEqual(bucket["n"], 60)
        self.assertEqual(bucket["conclusion"], "favori_surcote_historique")
        self.assertLess(bucket["delta_points"], 0)
        self.assertLess(bucket["delta_ci95"][1], 0)
        self.assertIsNotNone(bucket["roi_fade"])

    def test_small_bucket_is_non_conclusive(self):
        records = [record(i, i < 12, decision="Favorable", concordance="Concordance forte") for i in range(20)]
        report = run_decision_calibration(records, min_sample=50)
        bucket = next(item for item in report["primary"] if item["bucket"] == "Favorable x Concordance forte")
        self.assertEqual(bucket["conclusion"], "non_concluant")

    def test_json_export_payload_is_supported(self):
        payload = {"matches": [{
            "identity": {"circuit": "ATP", "surface": "Terre", "kickoff": "2026-01-01"},
            "lecture": {"favorite": "Player A", "decision": "Neutre", "concordance": "Marche seul"},
            "probabilities": {"market": 58, "elo_surface": 54, "odds": 1.72},
            "raw": {"winner": "Player A", "cote_outsider": 2.20},
        }]}
        records = records_from_export_payload(payload)
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].favorite_won)
        self.assertEqual(records[0].market_probability, 58.0)

    def test_status_summary_uses_decision_concordance_bucket(self):
        records = [record(i, i < 30) for i in range(60)]
        report = run_decision_calibration(records, min_sample=50)
        summary = status_summary_for_row({"decision": "Vigilance forte", "concordance": "Conflit fort"}, report)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["conclusion"], "favori_surcote_historique")
        self.assertIn("favori realise", summary["detail"])


if __name__ == "__main__":
    unittest.main()
