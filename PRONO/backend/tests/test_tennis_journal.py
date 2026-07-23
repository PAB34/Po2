"""Journal des decisions tennis.

Enjeu couvert : le moteur de calibration savait deja lire une table
`tennis_decisions`, mais rien ne l'ecrivait. Ces tests verrouillent le contrat
entre l'ecriture (tennis_journal) et la lecture (tennis_decision_calibration) --
si le schema derive d'un cote, la calibration redeviendrait muette sans bruit.

Pour executer :
    cd PRONO/backend && pytest tests/test_tennis_journal.py -v
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import tennis_journal
from app.tennis_decision_calibration import records_from_sqlite


def _entry(match_id: str, **over):
    base = dict(
        match_id=match_id,
        favorite="Alice",
        opponent="Bob",
        market_probability=0.62,
        elo_probability=0.44,
        elo_gap=-38.0,
        decision="suivre l'outsider",
        concordance="divergence Elo/marche",
        tour="ATP",
        surface="Hard",
        favorite_odds=1.55,
        outsider_odds=2.45,
    )
    base.update(over)
    return base


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "journal.db"

    def tearDown(self):
        self.dir.cleanup()

    def test_records_then_settles(self):
        tennis_journal.record_decision(path=self.path, **_entry("m1"))
        self.assertEqual(len(tennis_journal.pending(self.path)), 1)

        self.assertTrue(tennis_journal.settle("m1", winner="Bob", score="4-6 6-3 6-4", path=self.path))
        self.assertEqual(tennis_journal.pending(self.path), [])

    def test_settling_an_unknown_match_is_reported(self):
        self.assertFalse(tennis_journal.settle("inconnu", winner="Bob", path=self.path))

    def test_calibration_engine_reads_what_the_journal_writes(self):
        """Le contrat entre les deux modules : c'est lui qui manquait."""
        for i in range(3):
            tennis_journal.record_decision(path=self.path, **_entry(f"m{i}"))
            tennis_journal.settle(f"m{i}", winner="Alice" if i else "Bob", path=self.path)

        records = records_from_sqlite(self.path)
        self.assertEqual(len(records), 3)
        record = records[0]
        self.assertEqual(record.favorite, "Alice")
        # le journal stocke une fraction, la calibration expose des pourcentages
        self.assertAlmostEqual(record.market_probability, 62.0)
        self.assertEqual(record.circuit, "ATP")
        # l'issue du match doit etre correctement rapportee au favori
        self.assertEqual([r.favorite_won for r in records], [False, True, True])

    def test_unsettled_rows_are_ignored_by_the_calibration(self):
        tennis_journal.record_decision(path=self.path, **_entry("m1"))
        self.assertEqual(records_from_sqlite(self.path), [])

    def test_roi_is_computed_per_market(self):
        """Le tableau que les backtests ne peuvent pas produire : les marches
        secondaires n'ont aucune cote archivee."""
        played = [
            ("m1", "prend un set", 1.61, True),
            ("m2", "prend un set", 1.75, False),
            ("m3", "handicap +3.5", 1.68, True),
        ]
        for match_id, market, odds, won in played:
            tennis_journal.record_decision(
                path=self.path,
                **_entry(match_id, market=market, selection="Bob", taken_odds=odds, stake=1.0),
            )
            tennis_journal.settle(match_id, winner="Bob", bet_won=won, path=self.path)

        rows = {r["market"]: r for r in tennis_journal.roi_by_market(self.path)}
        self.assertEqual(rows["prend un set"]["n"], 2)
        self.assertEqual(rows["prend un set"]["wins"], 1)
        # mise 2, retour 1.61 -> perte de 0.39
        self.assertAlmostEqual(rows["prend un set"]["profit"], -0.39, places=2)
        self.assertAlmostEqual(rows["handicap +3.5"]["roi"], 0.68, places=2)

    def test_a_no_bet_is_journalled_too(self):
        """Ne garder que les paris pris empecherait de savoir si le filtre ecarte
        les bons ou les mauvais matchs."""
        tennis_journal.record_decision(path=self.path, **_entry("m1"))  # sans marche
        tennis_journal.settle("m1", winner="Alice", path=self.path)
        self.assertEqual(tennis_journal.roi_by_market(self.path), [])
        self.assertEqual(len(records_from_sqlite(self.path)), 1)
