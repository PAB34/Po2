import unittest
from unittest.mock import patch

import pandas as pd

from app.value.service import run_ligue1_boosted_ticket_backtest


class ValueBacktestServiceTests(unittest.TestCase):
    def test_run_ligue1_boosted_ticket_backtest_uses_history(self):
        history = pd.DataFrame([
            {"Kickoff": "2026-01-01", "HomeTeam": "A", "AwayTeam": "B", "FTR": "H", "PSH": 1.50, "PSD": 4.00, "PSA": 7.00},
            {"Kickoff": "2026-01-02", "HomeTeam": "C", "AwayTeam": "D", "FTR": "A", "PSH": 3.10, "PSD": 3.30, "PSA": 2.20},
            {"Kickoff": "2026-01-03", "HomeTeam": "E", "AwayTeam": "F", "FTR": "H", "PSH": 1.60, "PSD": 3.90, "PSA": 6.00},
            {"Kickoff": "2026-01-04", "HomeTeam": "G", "AwayTeam": "H", "FTR": "D", "PSH": 1.80, "PSD": 3.50, "PSA": 4.80},
        ])
        with patch("app.value.service.load_history", return_value=history):
            result = run_ligue1_boosted_ticket_backtest(selections_per_ticket=2, stake=50.0, max_tickets=1)
        self.assertEqual(result.n_selections, 4)
        self.assertEqual(result.n_tickets, 1)
        self.assertEqual(result.selections_per_ticket, 2)


if __name__ == "__main__":
    unittest.main()
