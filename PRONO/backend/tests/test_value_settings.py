import unittest

from app.value.settings import DEFAULT_SIMULATION


class ValueSettingsTests(unittest.TestCase):
    def test_user_confirmed_defaults(self):
        self.assertEqual(DEFAULT_SIMULATION.sports, ("football_ligue1", "tennis"))
        self.assertEqual(DEFAULT_SIMULATION.markets, ("1x2", "h2h"))
        self.assertEqual(DEFAULT_SIMULATION.session_ticket_count, 10)
        self.assertEqual(DEFAULT_SIMULATION.stake_eur, 50.0)
        self.assertEqual(DEFAULT_SIMULATION.boost_model, "winamax_like_configurable")


if __name__ == "__main__":
    unittest.main()
