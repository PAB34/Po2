import unittest

import pandas as pd

from app.value.boost import BoostSchedule
from app.value.ticket_backtest import build_market_favorite_selections, run_boosted_ticket_backtest


ODDS_COLUMNS = {"H": "PSH", "D": "PSD", "A": "PSA"}


def sample_matches():
    return pd.DataFrame([
        {"Kickoff": "2026-01-01", "HomeTeam": "A", "AwayTeam": "B", "FTR": "H", "PSH": 1.50, "PSD": 4.00, "PSA": 7.00},
        {"Kickoff": "2026-01-02", "HomeTeam": "C", "AwayTeam": "D", "FTR": "A", "PSH": 3.10, "PSD": 3.30, "PSA": 2.20},
        {"Kickoff": "2026-01-03", "HomeTeam": "E", "AwayTeam": "F", "FTR": "H", "PSH": 1.60, "PSD": 3.90, "PSA": 6.00},
        {"Kickoff": "2026-01-04", "HomeTeam": "G", "AwayTeam": "H", "FTR": "D", "PSH": 1.80, "PSD": 3.50, "PSA": 4.80},
    ])


class TicketBacktestTests(unittest.TestCase):
    def test_build_market_favorite_selections(self):
        selections = build_market_favorite_selections(sample_matches(), ODDS_COLUMNS, source="Pinnacle")
        self.assertEqual(len(selections), 4)
        self.assertEqual(selections[0].selection, "A")
        self.assertEqual(selections[1].selection, "D")
        self.assertTrue(selections[0].result)
        self.assertTrue(selections[1].result)
        self.assertLess(selections[0].ev, 0.0)

    def test_build_market_favorite_filters_odds(self):
        selections = build_market_favorite_selections(
            sample_matches(),
            ODDS_COLUMNS,
            source="Pinnacle",
            min_odd=1.55,
            max_odd=1.90,
        )
        self.assertEqual([selection.selection for selection in selections], ["E", "G"])

    def test_boosted_ticket_backtest_profit_and_drawdown(self):
        selections = build_market_favorite_selections(sample_matches(), ODDS_COLUMNS, source="Pinnacle")
        schedule = BoostSchedule(name="test", rates_by_selection_count={2: 0.10}, max_selection_count=10)
        result = run_boosted_ticket_backtest(selections, selections_per_ticket=2, stake=50.0, boost_schedule=schedule)
        self.assertEqual(result.n_tickets, 2)
        self.assertEqual(result.total_staked, 100.0)
        self.assertTrue(result.tickets[0].won)
        self.assertFalse(result.tickets[1].won)
        expected_first_profit = 50.0 * ((1.50 * 2.20 * 1.10) - 1.0)
        self.assertAlmostEqual(result.tickets[0].profit, expected_first_profit, places=6)
        self.assertAlmostEqual(result.total_profit, expected_first_profit - 50.0, places=6)
        self.assertAlmostEqual(result.roi, result.total_profit / 100.0, places=6)
        self.assertEqual(result.max_drawdown, 50.0)

    def test_backtest_respects_max_tickets(self):
        selections = build_market_favorite_selections(sample_matches(), ODDS_COLUMNS, source="Pinnacle")
        result = run_boosted_ticket_backtest(selections, selections_per_ticket=1, max_tickets=2)
        self.assertEqual(result.n_tickets, 2)
        self.assertEqual(result.n_selections, 4)


if __name__ == "__main__":
    unittest.main()
