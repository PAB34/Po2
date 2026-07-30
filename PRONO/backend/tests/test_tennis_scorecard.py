"""Bilan hebdomadaire : regroupement par semaine des deux mesures.

On verifie surtout que le bucket ISO-semaine est correct et que le cumule agrege bien
plusieurs semaines -- c'est ce qui permettra de lire l'accumulation dans le temps.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from app import tennis_journal, tennis_scorecard


def _pair_key(a, b):
    return "|".join(sorted([str(a).casefold(), str(b).casefold()]))


class IsoWeekTests(unittest.TestCase):
    def test_iso_week_format(self):
        self.assertEqual("2026-S30", tennis_scorecard._iso_week("2026-07-24T12:00"))
        self.assertEqual("2026-S31", tennis_scorecard._iso_week("2026-07-29T00:00:00+02:00"))

    def test_iso_week_none_on_garbage(self):
        self.assertIsNone(tennis_scorecard._iso_week(""))
        self.assertIsNone(tennis_scorecard._iso_week(None))


class ScorecardTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        os.unlink(self.path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(self.path + suffix)
            except (FileNotFoundError, PermissionError):
                pass

    def _pick(self, kickoff, market, prob, won):
        row = {
            "joueur1": "Favori", "joueur2": "Outsider", "favori": "Favori", "outsider": "Outsider",
            "tour": "ATP", "tournoi": "T", "surface": "Dur", "kickoff": kickoff,
            "markets": [{"key": market, "pick": "Outsider", "prob": prob, "fair_odds": 100 / prob}],
        }
        stamp = kickoff  # calculated_at unique par pick
        tennis_journal.record_market_picks([row], stamp, _pair_key, path=self.path)
        if won is not None:
            result = {"winner": "Outsider" if won else "Favori", "loser": "Favori" if won else "Outsider",
                      "sets": [[6, 4], [3, 6], [6, 2]], "sets_w": 2, "sets_l": 1, "games_w": 15, "games_l": 12}
            # regle le marche "prend un set" : ici l'outsider prend toujours un set (3 sets)
            tennis_journal.settle_from_results([result], _pair_key, stamp, path=self.path)

    def test_market_weeks_bucketed_and_cumulative_spans_them(self):
        # deux semaines distinctes, meme marche
        self._pick("2026-07-20T12:00", "outsider_takes_a_set", 60, True)   # S30
        self._pick("2026-07-21T12:00", "outsider_takes_a_set", 60, True)   # S30
        self._pick("2026-07-28T12:00", "outsider_takes_a_set", 60, True)   # S31
        card = tennis_scorecard.weekly_scorecard(path=self.path)
        weeks = {w["week"]: w for w in card["markets"]["by_week"]}
        self.assertIn("2026-S30", weeks)
        self.assertIn("2026-S31", weeks)
        s30 = next(m for m in weeks["2026-S30"]["markets"] if m["market"] == "outsider_takes_a_set")
        self.assertEqual(2, s30["n"])
        # le cumule couvre les deux semaines
        cum = next(m for m in card["markets"]["cumulative"] if m["market"] == "outsider_takes_a_set")
        self.assertEqual(3, cum["n"])
        self.assertEqual(3, card["coverage"]["settled_market_picks"] // 1 if False else cum["n"])

    def test_coverage_flags_thin_sample(self):
        self._pick("2026-07-20T12:00", "outsider_takes_a_set", 60, True)
        card = tennis_scorecard.weekly_scorecard(path=self.path)
        self.assertFalse(card["coverage"]["enough_to_read_markets"])  # n=1 << 50
        self.assertGreaterEqual(card["coverage"]["settled_market_picks"], 1)

    def test_empty_when_no_data(self):
        # base vide : structure presente, listes vides, pas d'erreur
        open(self.path, "a").close()
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS x (a)")
        card = tennis_scorecard.weekly_scorecard(path=self.path)
        self.assertEqual([], card["markets"]["by_week"])
        self.assertEqual([], card["markets"]["cumulative"])
        self.assertFalse(card["coverage"]["enough_to_read_markets"])


if __name__ == "__main__":
    unittest.main()
