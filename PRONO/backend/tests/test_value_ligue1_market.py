import unittest

import pandas as pd

from app.value.backtest import DEFAULT_WARNING_NO_SNAPSHOT
from app.value.ligue1_market import run_ligue1_market_backtests, source_coverage


class Ligue1MarketBridgeTests(unittest.TestCase):
    def test_source_coverage_counts_valid_rows(self):
        history = pd.DataFrame([
            {"FTR": "H", "PSH": 1.8, "PSD": 3.5, "PSA": 4.8, "B365H": 1.7, "B365D": 3.4, "B365A": 5.0},
            {"FTR": "A", "PSH": None, "PSD": 3.2, "PSA": 2.4, "B365H": 2.8, "B365D": 3.1, "B365A": 2.5},
            {"FTR": "", "PSH": 2.0, "PSD": 3.1, "PSA": 3.8, "B365H": 2.0, "B365D": 3.1, "B365A": 3.8},
        ])
        coverage = source_coverage(history, sources=(
            ("Pinnacle", {"H": "PSH", "D": "PSD", "A": "PSA"}),
            ("Bet365", {"H": "B365H", "D": "B365D", "A": "B365A"}),
        ))
        self.assertEqual(coverage[0].valid_rows, 1)
        self.assertEqual(coverage[1].valid_rows, 2)

    def test_run_ligue1_market_backtests_uses_available_sources(self):
        history = pd.DataFrame([
            {"Kickoff": "2026-01-01", "HomeTeam": "A", "AwayTeam": "B", "FTR": "H", "PSH": 1.8, "PSD": 3.5, "PSA": 4.8},
            {"Kickoff": "2026-01-02", "HomeTeam": "C", "AwayTeam": "D", "FTR": "A", "PSH": 2.8, "PSD": 3.2, "PSA": 2.4},
        ])
        results = run_ligue1_market_backtests(history)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "Pinnacle")
        self.assertEqual(results[0].n_matches, 2)
        self.assertIn(DEFAULT_WARNING_NO_SNAPSHOT, results[0].warnings)


if __name__ == "__main__":
    unittest.main()
