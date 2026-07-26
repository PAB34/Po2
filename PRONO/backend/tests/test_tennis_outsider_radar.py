from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta

from app import tennis_outsider_radar as radar


SCHEMA = """
CREATE TABLE tennis_decisions (
    id INTEGER PRIMARY KEY,
    calculated_at TEXT NOT NULL,
    kickoff TEXT,
    tour TEXT,
    tournament TEXT,
    surface TEXT,
    pair_key TEXT,
    favorite TEXT,
    favorite_odds REAL,
    outsider_odds REAL,
    market_probability REAL,
    elo_probability REAL,
    elo_gap REAL,
    decision TEXT,
    decision_level TEXT,
    concordance TEXT,
    context_label TEXT,
    quality TEXT,
    cycle_favorite TEXT,
    fatigue_favorite TEXT,
    cycle_opponent TEXT,
    fatigue_opponent TEXT,
    payload_json TEXT,
    result_winner TEXT
);
"""


class OutsiderHistoryTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        with sqlite3.connect(self.path) as db:
            db.executescript(SCHEMA)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def _insert(self, calculated_at: str, elo_probability: float, winner: str = "Outsider"):
        kickoff = (date.today() + timedelta(days=1)).isoformat() + "T12:00"
        payload = {"joueur1": "Favori", "joueur2": "Outsider", "outsider": "Outsider"}
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT INTO tennis_decisions (
                    calculated_at, kickoff, tour, tournament, surface, pair_key, favorite,
                    favorite_odds, outsider_odds, market_probability, elo_probability,
                    elo_gap, decision, decision_level, concordance, context_label, quality,
                    cycle_favorite, fatigue_favorite, cycle_opponent, fatigue_opponent,
                    payload_json, result_winner
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (calculated_at, kickoff, "ATP", "Test", "Dur", "favori|outsider", "Favori",
                 1.50, 2.80, 66.7, elo_probability, -8.0, "prudence", "watch",
                 "Divergence Elo", "Desavantage relatif", "elevee", "stable", "fraicheur",
                 "montee", "fraicheur", json.dumps(payload), winner),
            )

    def test_later_snapshot_is_the_only_evaluated_match(self):
        self._insert("2026-07-20T09:00", 58.0)
        self._insert("2026-07-20T11:00", 54.0)
        rows = radar._canonical_history(self.path)
        self.assertEqual(1, len(rows))
        self.assertEqual("2026-07-20T11:00", rows[0]["calculated_at"])
        self.assertEqual(54.0, rows[0]["elo_probability"])

    def test_recent_summary_counts_unique_matches(self):
        self._insert("2026-07-20T09:00", 58.0)
        self._insert("2026-07-20T11:00", 54.0)
        result = radar.recent_outsiders(days=90, path=self.path)
        self.assertEqual(1, result["canonical_match_count"])
        self.assertEqual(1, result["upset_count"])
        self.assertEqual(100.0, result["upset_rate"])


class RadarScoreTests(unittest.TestCase):
    def test_strong_divergence_and_recent_upset_rank_high(self):
        payload = {
            "updated": "2026-07-26T10:00",
            "atp": [{
                "tour": "ATP", "tournoi": "Test", "surface": "Dur", "heure": "12:00",
                "favori": "Favori", "outsider": "Outsider", "cote": 1.45,
                "cote_outsider": 3.10, "proba_marche": 68.0, "proba_elo": 51.0,
                "concordance": "Conflit fort", "impact_contexte": "Desavantage relatif",
                "cycle_adversaire": "Pic probable", "fatigue_favori": "Charge lourde",
                "fatigue_adversaire": "Fraicheur", "qualite": "elevee", "markets": [],
            }],
            "wta": [],
        }
        original = radar.recent_outsiders
        radar.recent_outsiders = lambda **_: {
            "days": 7, "source": "test", "canonical_match_count": 1, "upset_count": 1,
            "upset_rate": 100.0, "average_winning_outsider_odds": 3.2,
            "winners": [{"outsider": "Outsider", "outsider_odds": 3.2}], "losses": [],
        }
        try:
            result = radar.build_radar(payload)
        finally:
            radar.recent_outsiders = original
        candidate = result["candidates"][0]
        self.assertGreaterEqual(candidate["score"], 65)
        self.assertEqual("prioritaire", candidate["label"])
        self.assertEqual(1, candidate["recent_upsets"])


if __name__ == "__main__":
    unittest.main()
