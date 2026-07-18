import unittest
from datetime import datetime
from unittest.mock import patch

from app import tennis


class TennisServiceTests(unittest.TestCase):
    def test_build_tennis_filters_and_scores_matches(self):
        feed = {
            "last_updated": "2026-07-17T12:00:00Z",
            "matches": [
                {
                    "tour": "ATP",
                    "tournament": "ATP Hamburg",
                    "player1": "Market Player A (1)",
                    "player2": "Market Player B (2)",
                    "odds1": "1.50",
                    "odds2": "2.70",
                },
                {
                    "tour": "ATP",
                    "tournament": "Challenger Turin",
                    "player1": "Player A",
                    "player2": "Player B",
                    "odds1": "1.80",
                    "odds2": "2.00",
                },
                {
                    "tour": "WTA",
                    "tournament": "Wimbledon",
                    "player1": "Grass Player A",
                    "player2": "Grass Player B",
                    "odds1": "2.40",
                    "odds2": "1.62",
                },
            ],
        }

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        self.assertEqual(payload["feed_updated"], "2026-07-17T12:00:00Z")
        self.assertEqual(len(payload["atp"]), 1)
        self.assertEqual(payload["atp"][0]["surface"], "Terre")
        self.assertEqual(payload["atp"][0]["favori"], "Market Player A")
        self.assertEqual(payload["atp"][0]["match"], "Market Player A vs Market Player B")
        self.assertIn("proba_brute", payload["atp"][0])
        self.assertIn("preuves", payload["atp"][0])
        self.assertEqual(len(payload["wta"]), 1)
        self.assertEqual(payload["wta"][0]["surface"], "Gazon")
        self.assertEqual(payload["wta"][0]["favori"], "Grass Player B")

    def test_build_tennis_hides_past_timed_matches(self):
        feed = {
            "last_updated": "2026-07-18T09:00:00",
            "matches": [
                {
                    "tour": "ATP",
                    "tournament": "Gstaad",
                    "player1": "Past Player A",
                    "player2": "Past Player B",
                    "time": "08:00",
                    "odds1": 1.7,
                    "odds2": 2.2,
                },
                {
                    "tour": "ATP",
                    "tournament": "Gstaad",
                    "player1": "Future Player A",
                    "player2": "Future Player B",
                    "time": "11:00",
                    "odds1": 1.8,
                    "odds2": 2.0,
                },
            ],
        }

        now = datetime(2026, 7, 18, 10, 0, tzinfo=tennis.PARIS_TZ)
        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "_now_paris", return_value=now), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        self.assertEqual(payload["filtered_past"], 1)
        self.assertEqual(len(payload["atp"]), 1)
        self.assertEqual(payload["atp"][0]["match"], "Future Player A vs Future Player B")
        self.assertEqual(payload["atp"][0]["heure"], "Aujourd'hui 11:00")
        self.assertIsNotNone(payload["atp"][0]["kickoff"])

    def test_build_tennis_marks_stale_local_data_confirmed_by_secondary_source(self):
        feed = {
            "last_updated": "2026-07-17T12:00:00Z",
            "matches": [
                {
                    "tour": "ATP",
                    "tournament": "Gstaad",
                    "player1": "Cerundolo J. (6)",
                    "player2": "Ruud C. (2)",
                    "odds1": 3.43,
                    "odds2": 1.31,
                }
            ],
        }
        secondary = {"status": "confirmed_recent", "days": 1, "source": "SportScore"}

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value=secondary):
            payload = tennis.build_tennis()

        row = payload["atp"][0]
        self.assertIn("SportScore", payload["external_sources"])
        self.assertIn("match recent retrouve SportScore", row["preuves"])

    def test_build_tennis_penalizes_ruud_with_coach_and_h2h(self):
        feed = {
            "last_updated": "2026-07-17T12:00:00Z",
            "matches": [
                {
                    "tour": "ATP",
                    "tournament": "Gstaad",
                    "player1": "Cerundolo J. (6)",
                    "player2": "Ruud C. (2)",
                    "odds1": 3.43,
                    "odds2": 1.31,
                }
            ],
        }

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        row = payload["atp"][0]
        self.assertEqual(row["favori"], "Ruud C.")
        self.assertEqual(row["h2h"], "1-0")
        self.assertIn("Gstaad 2025", row["alerte"])
        self.assertLess(row["proba"], row["proba_brute"])
        self.assertLess(row["proba"], row["proba_marche"])
        self.assertEqual(row["cycle2"], "sous-rythme")

    def test_scoreboard_matchups_override_stale_market_pairs(self):
        feed = {
            "last_updated": "2026-07-18T09:00:00Z",
            "matches": [
                {
                    "tour": "ATP",
                    "tournament": "Bastad",
                    "player1": "Darderi L. (2)",
                    "player2": "Borges N. (5)",
                    "time": "13:00",
                    "odds1": 1.66,
                    "odds2": 2.19,
                }
            ],
        }
        scoreboard = [
            {
                "tour": "ATP",
                "tournament": "Nordea Open",
                "player1": "Luciano Darderi",
                "player2": "Adolfo Daniel Vallejo",
                "kickoff": "2026-07-18T13:00:00+02:00",
                "source": "ESPN",
            }
        ]
        now = datetime(2026, 7, 18, 10, 0, tzinfo=tennis.PARIS_TZ)

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_scoreboard_matches", return_value=scoreboard), patch.object(tennis, "_now_paris", return_value=now), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        self.assertEqual(payload["scoreboard_source"], "ESPN")
        self.assertEqual(payload["scoreboard_count"], 1)
        self.assertEqual(len(payload["atp"]), 1)
        row = payload["atp"][0]
        self.assertEqual(row["match"], "Luciano Darderi vs Adolfo Daniel Vallejo")
        self.assertEqual(row["match_source"], "ESPN")
        self.assertEqual(row["odds_status"], "indisponibles")
        self.assertIsNone(row["cote"])
    def test_scoreboard_tournament_names_keep_clay_surface(self):
        self.assertEqual(tennis._surface("Nordea Open"), "Terre")
        self.assertEqual(tennis._surface("EFG Swiss Open Gstaad"), "Terre")
        self.assertEqual(tennis._surface("Plava Laguna Croatia Open Umag"), "Terre")
        self.assertEqual(tennis._surface("Generali Open"), "Terre")
    def test_scoreboard_matchups_attach_abbreviated_market_odds(self):
        feed = {
            "last_updated": "2026-07-18T09:00:00Z",
            "matches": [
                {
                    "tour": "ATP",
                    "tournament": "Bastad",
                    "player1": "Rublev A. (1)",
                    "player2": "Tabilo A. (3)",
                    "time": "14:30",
                    "odds1": 1.42,
                    "odds2": 2.82,
                }
            ],
        }
        scoreboard = [
            {
                "tour": "ATP",
                "tournament": "Nordea Open",
                "player1": "Alejandro Tabilo",
                "player2": "Andrey Rublev",
                "kickoff": "2026-07-18T14:30:00+02:00",
                "source": "ESPN",
            }
        ]
        now = datetime(2026, 7, 18, 10, 0, tzinfo=tennis.PARIS_TZ)

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_scoreboard_matches", return_value=scoreboard), patch.object(tennis, "_now_paris", return_value=now), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        row = payload["atp"][0]
        self.assertEqual(row["odds_status"], "ok")
        self.assertEqual(row["odds_source"], "market-feed")
        self.assertEqual(row["cote"], 2.82 if row["favori"] == "Alejandro Tabilo" else 1.42)
        self.assertNotEqual(row["proba_marche"], 50.0)

if __name__ == "__main__":
    unittest.main()
