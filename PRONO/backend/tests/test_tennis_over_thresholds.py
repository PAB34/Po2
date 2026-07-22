"""Seuils de total jeux 18.5 / 19.5 et probabilite conjointe avec "prend un set".

Contexte : les tickets joues combinent "le joueur prend au moins un set" et un over
sur le total de jeux, mais seul l'over 22.5 etait mesure. Le ticket etait donc evalue
sur un seuil que le modele ne calculait pas, en supposant implicitement l'independance
des deux evenements -- alors qu'ils sont fortement correles.

Pour executer :
    cd PRONO/backend && pytest tests/test_tennis_over_thresholds.py -v
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.tennis_calibration import OUTCOMES, _score_outcomes
from app.tennis_coherence import MARKETS

MATRIX = Path(__file__).resolve().parents[1] / "app" / "tennis_data" / "coherence_matrix.json"


class ScoreOutcomeTests(unittest.TestCase):
    def test_thresholds_follow_the_actual_game_count(self):
        # 6-2 6-2 = 16 jeux : sous les trois seuils.
        out = _score_outcomes("6-2 6-2", favorite_won=True)
        self.assertEqual(out["over_18_5"], 0.0)
        self.assertEqual(out["over_19_5"], 0.0)
        self.assertEqual(out["over_22_5"], 0.0)

        # 6-4 6-4 = 20 jeux : au-dessus de 18.5 et 19.5, sous 22.5.
        out = _score_outcomes("6-4 6-4", favorite_won=True)
        self.assertEqual(out["over_18_5"], 1.0)
        self.assertEqual(out["over_19_5"], 1.0)
        self.assertEqual(out["over_22_5"], 0.0)

        # 7-6 6-7 7-6 = 39 jeux : au-dessus des trois.
        out = _score_outcomes("7-6 6-7 7-6", favorite_won=True)
        self.assertEqual(out["over_18_5"], 1.0)
        self.assertEqual(out["over_19_5"], 1.0)
        self.assertEqual(out["over_22_5"], 1.0)

    def test_thresholds_are_nested(self):
        """Un seuil plus bas ne peut jamais etre plus difficile a franchir."""
        for score in ("6-2 6-2", "6-4 6-4", "6-3 4-6 7-5", "7-6 6-7 7-6"):
            out = _score_outcomes(score, favorite_won=True)
            self.assertGreaterEqual(out["over_18_5"], out["over_19_5"], score)
            self.assertGreaterEqual(out["over_19_5"], out["over_22_5"], score)

    def test_new_markets_are_declared_everywhere(self):
        for market in ("over_18_5", "over_19_5"):
            self.assertIn(market, OUTCOMES)
            self.assertIn(market, MARKETS)


class MatrixTests(unittest.TestCase):
    """Verifications sur la matrice versionnee, calculee sur l'historique reel."""

    @classmethod
    def setUpClass(cls):
        cls.scope = json.loads(MATRIX.read_text(encoding="utf-8"))["scopes"]["ALL"]["all"]

    def _pair(self, a, b):
        return self.scope["pairs"]["|".join(sorted((a, b)))]["p_ab"]

    def test_matrix_carries_the_new_thresholds(self):
        for market in ("over_18_5", "over_19_5"):
            self.assertIn(market, self.scope["marginals"])

    def test_marginals_are_ordered_by_threshold(self):
        m = self.scope["marginals"]
        self.assertGreater(m["over_18_5"], m["over_19_5"])
        self.assertGreater(m["over_19_5"], m["over_22_5"])

    def test_joint_probability_beats_the_naive_product(self):
        """Le coeur du sujet : "prend un set" et "over" ne sont pas independants.

        Les multiplier sous-estime lourdement le ticket combine.
        """
        m = self.scope["marginals"]
        p_set = 1 - m["favorite_2_0"]  # l'outsider prend au moins un set
        for threshold in ("over_18_5", "over_19_5", "over_22_5"):
            joint = m[threshold] - self._pair("favorite_2_0", threshold)
            naive = p_set * m[threshold]
            self.assertGreater(joint, naive, threshold)
            # conditionnellement, l'over est bien plus probable qu'en absolu
            self.assertGreater(joint / p_set, m[threshold], threshold)

    def test_every_three_set_match_clears_18_5_games(self):
        """Controle croise : un match en 3 sets fait au moins 19 jeux en pratique.

        Si cette egalite se rompt, c'est que les seuils ou le comptage ont derive.
        """
        m = self.scope["marginals"]
        self.assertAlmostEqual(self._pair("over_18_5", "three_sets"), m["three_sets"], places=3)
