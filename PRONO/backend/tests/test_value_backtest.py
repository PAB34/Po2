import unittest

import pandas as pd

from app.value.backtest import (
    DEFAULT_WARNING_NO_SNAPSHOT,
    TemporalLeakageError,
    run_market_1x2_backtest,
    validate_no_future_data,
)
from app.value.metrics import brier_score_multiclass, calibration_bins, log_loss_multiclass


ODDS_COLUMNS = {"H": "PSH", "D": "PSD", "A": "PSA"}


def sample_matches():
    return pd.DataFrame([
        {
            "Kickoff": "2026-01-01 20:00",
            "HomeTeam": "A",
            "AwayTeam": "B",
            "FTR": "H",
            "PSH": 1.80,
            "PSD": 3.60,
            "PSA": 4.80,
            "captured_at": "2026-01-01 10:00",
            "decision_at": "2026-01-01 12:00",
        },
        {
            "Kickoff": "2026-01-02 20:00",
            "HomeTeam": "C",
            "AwayTeam": "D",
            "FTR": "A",
            "PSH": 2.80,
            "PSD": 3.20,
            "PSA": 2.50,
            "captured_at": "2026-01-02 10:00",
            "decision_at": "2026-01-02 12:00",
        },
        {
            "Kickoff": "2026-01-03 20:00",
            "HomeTeam": "E",
            "AwayTeam": "F",
            "FTR": "D",
            "PSH": 2.10,
            "PSD": 3.00,
            "PSA": 3.90,
            "captured_at": "2026-01-03 10:00",
            "decision_at": "2026-01-03 12:00",
        },
    ])


class BacktestMetricsTests(unittest.TestCase):
    def test_log_loss_multiclass(self):
        loss = log_loss_multiclass([(0.7, 0.2, 0.1), (0.2, 0.3, 0.5)], [0, 2])
        self.assertAlmostEqual(loss, 0.5249110622, places=6)

    def test_brier_score_multiclass(self):
        score = brier_score_multiclass([(0.7, 0.2, 0.1), (0.2, 0.3, 0.5)], [0, 2])
        self.assertAlmostEqual(score, 0.26, places=6)

    def test_calibration_bins(self):
        bins = calibration_bins([0.52, 0.57, 0.82], [True, False, True], bins=[(0.5, 0.6), (0.8, 0.85)])
        self.assertEqual(bins[0].count, 2)
        self.assertAlmostEqual(bins[0].predicted_mean, 0.545, places=6)
        self.assertAlmostEqual(bins[0].actual_rate, 0.5, places=6)
        self.assertEqual(bins[1].count, 1)


class MarketBacktestTests(unittest.TestCase):
    def test_backtest_runs_in_closing_proxy_mode_without_timestamps(self):
        result = run_market_1x2_backtest(sample_matches(), ODDS_COLUMNS, source="Pinnacle")
        self.assertEqual(result.n_matches, 3)
        self.assertEqual(result.source, "Pinnacle")
        self.assertIn(DEFAULT_WARNING_NO_SNAPSHOT, result.warnings)
        self.assertGreater(result.log_loss, 0.0)
        self.assertGreater(result.brier_score, 0.0)
        self.assertEqual(len(result.predictions), 3)

    def test_backtest_with_valid_temporal_columns_has_no_warning(self):
        result = run_market_1x2_backtest(
            sample_matches(),
            ODDS_COLUMNS,
            source="Pinnacle",
            captured_at_column="captured_at",
            decision_at_column="decision_at",
        )
        self.assertEqual(result.n_matches, 3)
        self.assertEqual(result.warnings, ())

    def test_temporal_guard_rejects_future_data(self):
        frame = sample_matches()
        frame.loc[1, "captured_at"] = "2026-01-02 13:00"
        with self.assertRaisesRegex(TemporalLeakageError, "Future data"):
            validate_no_future_data(frame, "captured_at", "decision_at")

    def test_invalid_rows_are_skipped(self):
        frame = sample_matches()
        frame.loc[0, "FTR"] = ""
        frame.loc[1, "PSH"] = None
        result = run_market_1x2_backtest(frame, ODDS_COLUMNS, source="Pinnacle")
        self.assertEqual(result.n_matches, 1)
        self.assertEqual(result.predictions[0].home, "E")


if __name__ == "__main__":
    unittest.main()

