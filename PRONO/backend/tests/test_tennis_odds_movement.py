"""Trajectoire de cote et closing line lues sur les snapshots existants.

Points sensibles : la closing line doit etre le dernier snapshot AVANT le kickoff (pas un
recalcul post-match), et le sens du mouvement doit etre correct (cote qui BAISSE = marche
qui va vers l'outsider = "raccourcit").
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from app import tennis_odds_movement as movement


SCHEMA = """
CREATE TABLE tennis_decisions (
    id INTEGER PRIMARY KEY,
    calculated_at TEXT NOT NULL,
    kickoff TEXT,
    tour TEXT,
    tournament TEXT,
    pair_key TEXT,
    player1 TEXT,
    player2 TEXT,
    favorite TEXT,
    favorite_odds REAL,
    outsider_odds REAL,
    result_winner TEXT,
    match_id TEXT
);
"""


class OddsMovementTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        with sqlite3.connect(self.path) as db:
            db.executescript(SCHEMA)

    def tearDown(self):
        try:
            os.unlink(self.path)
        except (FileNotFoundError, PermissionError):
            pass

    def _snap(self, calculated_at, outsider_odds, kickoff="2026-07-25T14:00",
              match_id="ATP|test|a|b", result_winner=None):
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT INTO tennis_decisions (calculated_at, kickoff, tour, tournament,
                   pair_key, player1, player2, favorite, favorite_odds, outsider_odds,
                   result_winner, match_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (calculated_at, kickoff, "ATP", "Test", "a|b", "Favori", "Outsider",
                 "Favori", 1.5, outsider_odds, result_winner, match_id),
            )

    def test_shortening_is_detected_when_the_price_drops(self):
        self._snap("2026-07-24T10:00", 3.20)
        self._snap("2026-07-25T09:00", 3.00)
        self._snap("2026-07-25T13:30", 2.70)
        move = movement.match_movement("ATP|test|a|b", path=self.path)
        self.assertEqual(3.20, move["opening_outsider_odds"])
        self.assertEqual(2.70, move["closing_outsider_odds"])
        self.assertEqual("raccourcit", move["direction"])
        self.assertLess(move["delta_odds"], 0)
        self.assertGreater(move["implied_move_points"], 0)  # proba implicite qui monte

    def test_drifting_is_detected_when_the_price_rises(self):
        self._snap("2026-07-24T10:00", 2.50)
        self._snap("2026-07-25T13:30", 3.10)
        move = movement.match_movement("ATP|test|a|b", path=self.path)
        self.assertEqual("derive", move["direction"])
        self.assertGreater(move["delta_odds"], 0)

    def test_closing_line_ignores_post_kickoff_recalculation(self):
        self._snap("2026-07-24T10:00", 3.00)
        self._snap("2026-07-25T13:30", 2.60)          # dernier PREMATCH = closing
        self._snap("2026-07-25T18:00", 5.00)          # recalcul APRES le kickoff 14:00
        move = movement.match_movement("ATP|test|a|b", path=self.path)
        self.assertEqual(2.60, move["closing_outsider_odds"],
                         "la closing line doit ignorer le snapshot post-kickoff")

    def test_all_post_kickoff_falls_back_to_last_available(self):
        self._snap("2026-07-25T20:00", 3.00, kickoff="2026-07-25T14:00")
        self._snap("2026-07-25T21:00", 2.80, kickoff="2026-07-25T14:00")
        move = movement.match_movement("ATP|test|a|b", path=self.path)
        self.assertEqual(2.80, move["closing_outsider_odds"])

    def test_aggregate_counts_directions(self):
        # un match qui raccourcit, un qui derive
        self._snap("2026-07-25T09:00", 3.00, match_id="m1")
        self._snap("2026-07-25T13:00", 2.50, match_id="m1")
        self._snap("2026-07-25T09:00", 2.50, match_id="m2")
        self._snap("2026-07-25T13:00", 3.20, match_id="m2")
        summary = movement.recent_movements(days=120, path=self.path)
        self.assertEqual(2, summary["tracked_matches"])
        self.assertEqual(1, summary["shortened_count"])
        self.assertEqual(1, summary["drifted_count"])
        self.assertEqual(50.0, summary["shortened_rate"])

    def test_single_snapshot_match_is_not_tracked(self):
        self._snap("2026-07-25T09:00", 3.00)
        self.assertEqual(0, movement.recent_movements(days=120, path=self.path)["tracked_matches"])

    def test_no_data_dir_returns_empty_without_guessing(self):
        previous = os.environ.pop("PRONO_DATA_DIR", None)
        try:
            self.assertEqual({}, movement._snapshots())
            self.assertEqual(0, movement.recent_movements()["tracked_matches"])
        finally:
            if previous is not None:
                os.environ["PRONO_DATA_DIR"] = previous


if __name__ == "__main__":
    unittest.main()
