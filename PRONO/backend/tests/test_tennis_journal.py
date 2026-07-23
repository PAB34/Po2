"""Registre des marches secondaires : alimente et regle sans intervention.

Le point sensible n'est pas le stockage, c'est l'ORIENTATION. Les scores ESPN sont ecrits
du point de vue du vainqueur du match ; les marches suivis, eux, portent tous sur
l'outsider. Une inversion ne leverait aucune erreur et fausserait toute la calibration en
silence -- d'ou la densite de tests sur ce seul point.

Pour executer :
    cd PRONO/backend && pytest tests/test_tennis_journal.py -v
"""
from __future__ import annotations

import os
import tempfile
import unittest

from app import tennis_journal


def _pair_key(a, b):
    return "|".join(sorted([str(a).casefold(), str(b).casefold()]))


def _row(**over):
    row = {
        "joueur1": "Favori", "joueur2": "Outsider", "favori": "Favori", "outsider": "Outsider",
        "tour": "ATP", "tournoi": "Gstaad", "surface": "Terre", "kickoff": "2026-07-24T12:00",
        "decision_level": "watch", "concordance": "divergence",
        "markets": [
            {"key": "outsider_takes_a_set", "pick": "Outsider >= 1 set", "prob": 57, "fair_odds": 1.76},
            {"key": "outsider_games_3_5", "pick": "Outsider +3.5", "prob": 54, "fair_odds": 1.86},
            {"key": "outsider_set_1", "pick": "Outsider set 1", "prob": 39, "fair_odds": 2.56},
            {"key": "total_games", "pick": "Over 22.5 jeux", "prob": 51, "fair_odds": 1.96},
            {"key": "aces", "pick": "profil", "prob": None, "fair_odds": None},
        ],
    }
    row.update(over)
    return row


def _result(winner="Favori", loser="Outsider", sets=((6, 4), (6, 3))):
    pairs = [list(s) for s in sets]
    return {
        "winner": winner, "loser": loser, "sets": pairs,
        "sets_w": sum(a > b for a, b in pairs), "sets_l": sum(b > a for a, b in pairs),
        "games_w": sum(a for a, _ in pairs), "games_l": sum(b for _, b in pairs),
    }


class MarketOutcomesTests(unittest.TestCase):
    def test_outsider_swept_loses_everything(self):
        # Favori 6-4 6-3 : aucun set pris, defaite de 5 jeux.
        out = tennis_journal.market_outcomes(_result(), "Outsider")
        self.assertFalse(out["outsider_takes_a_set"])
        self.assertFalse(out["outsider_set_1"])
        self.assertFalse(out["outsider_games_3_5"])

    def test_outsider_takes_a_set_when_the_match_goes_three(self):
        out = tennis_journal.market_outcomes(_result(sets=((4, 6), (6, 3), (6, 4))), "Outsider")
        self.assertTrue(out["outsider_takes_a_set"])
        self.assertTrue(out["outsider_set_1"])   # l'outsider remporte 6-4 la manche 1

    def test_outsider_winning_the_match_reverses_the_reading(self):
        # L'outsider EST le vainqueur : les scores sont deja ecrits de son cote.
        out = tennis_journal.market_outcomes(
            _result(winner="Outsider", loser="Favori", sets=((6, 4), (6, 3))), "Outsider")
        self.assertTrue(out["outsider_takes_a_set"])
        self.assertTrue(out["outsider_set_1"])
        self.assertTrue(out["outsider_games_3_5"])

    def test_close_defeat_still_covers_the_handicap(self):
        # 7-5 6-7 7-5 : le favori l'emporte de 2 jeux, l'outsider couvre +3.5.
        out = tennis_journal.market_outcomes(_result(sets=((7, 5), (6, 7), (7, 5))), "Outsider")
        self.assertTrue(out["outsider_games_3_5"])
        self.assertTrue(out["outsider_takes_a_set"])

    def test_handicap_boundary_at_exactly_four_games(self):
        # 6-4 6-4 : marge de 4 jeux, l'outsider ne couvre pas +3.5.
        out = tennis_journal.market_outcomes(_result(sets=((6, 4), (6, 4))), "Outsider")
        self.assertFalse(out["outsider_games_3_5"])

    def test_missing_set_detail_does_not_invent_a_set_1(self):
        result = _result()
        result["sets"] = []
        self.assertNotIn("outsider_set_1", tennis_journal.market_outcomes(result, "Outsider"))


class RegistryTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        os.unlink(self.path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(self.path + suffix):
                os.unlink(self.path + suffix)

    def _record(self, rows=None, stamp="2026-07-24T09:00"):
        return tennis_journal.record_market_picks(rows or [_row()], stamp, _pair_key, path=self.path)

    def test_only_tracked_markets_are_registered(self):
        self.assertEqual(3, self._record())   # ni total_games ni aces

    def test_recording_twice_the_same_snapshot_is_idempotent(self):
        self._record()
        self.assertEqual(0, self._record())

    def test_a_later_snapshot_of_the_same_match_is_a_new_reading(self):
        self._record(stamp="2026-07-24T09:00")
        self.assertEqual(3, self._record(stamp="2026-07-24T15:00"))

    def test_markets_stay_pending_until_the_match_is_played(self):
        self._record()
        self.assertEqual(3, len(tennis_journal.pending(path=self.path)))

    def test_settlement_is_automatic_and_orientation_aware(self):
        self._record()
        settled = tennis_journal.settle_from_results(
            [_result(sets=((4, 6), (6, 3), (6, 4)))], _pair_key, "2026-07-24T18:00", path=self.path)
        self.assertEqual(3, settled)
        self.assertEqual([], tennis_journal.pending(path=self.path))
        by_market = {m["market"]: m for m in
                     tennis_journal.calibration_by_market(path=self.path, min_sample=1)}
        self.assertEqual(1, by_market["outsider_takes_a_set"]["wins"])
        self.assertEqual(1, by_market["outsider_set_1"]["wins"])

    def test_settling_twice_does_not_double_count(self):
        self._record()
        tennis_journal.settle_from_results([_result()], _pair_key, "t1", path=self.path)
        self.assertEqual(0, tennis_journal.settle_from_results(
            [_result()], _pair_key, "t2", path=self.path))

    def test_an_unknown_match_settles_nothing(self):
        self._record()
        other = _result(winner="Inconnu A", loser="Inconnu B")
        self.assertEqual(0, tennis_journal.settle_from_results(
            [other], _pair_key, "t", path=self.path))

    def test_calibration_compares_realised_against_announced(self):
        for index, stamp in enumerate(("t1", "t2")):
            row = _row(joueur2=f"Outsider{index}", outsider=f"Outsider{index}")
            self._record([row], stamp=stamp)
            tennis_journal.settle_from_results(
                [_result(loser=f"Outsider{index}", sets=((4, 6), (6, 3), (6, 4)))],
                _pair_key, stamp, path=self.path)
        takes = next(m for m in tennis_journal.calibration_by_market(path=self.path, min_sample=1)
                     if m["market"] == "outsider_takes_a_set")
        self.assertEqual(2, takes["n"])
        self.assertEqual(100.0, takes["realised"])
        self.assertEqual(57.0, takes["expected"])
        self.assertEqual(43.0, takes["delta_points"])

    def test_a_thin_sample_never_concludes(self):
        self._record()
        tennis_journal.settle_from_results([_result()], _pair_key, "t", path=self.path)
        for market in tennis_journal.calibration_by_market(path=self.path, min_sample=20):
            self.assertEqual("echantillon insuffisant", market["verdict"])

    def test_unsettled_rows_are_excluded_from_the_calibration(self):
        self._record()
        self.assertEqual([], tennis_journal.calibration_by_market(path=self.path, min_sample=1))


class SingleSourceTests(unittest.TestCase):
    """Une seule base fait foi : celle que l'enregistrement automatique alimente."""

    def test_the_registry_lives_in_the_decision_history_database(self):
        previous = os.environ.get("PRONO_DATA_DIR")
        os.environ["PRONO_DATA_DIR"] = tempfile.gettempdir()
        try:
            path = tennis_journal.journal_path()
            self.assertEqual("decision_history.sqlite3", path.name)
            self.assertEqual("tennis", path.parent.name)
        finally:
            if previous is None:
                os.environ.pop("PRONO_DATA_DIR", None)
            else:
                os.environ["PRONO_DATA_DIR"] = previous

    def test_without_a_data_dir_nothing_is_guessed(self):
        previous = os.environ.pop("PRONO_DATA_DIR", None)
        try:
            self.assertIsNone(tennis_journal.journal_path())
            self.assertEqual([], tennis_journal.pending())
            self.assertEqual([], tennis_journal.calibration_by_market())
        finally:
            if previous is not None:
                os.environ["PRONO_DATA_DIR"] = previous


if __name__ == "__main__":
    unittest.main()
