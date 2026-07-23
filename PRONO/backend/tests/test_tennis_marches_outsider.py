"""Les trois marches que le backtest place devant : calcul, orientation, cote juste.

Ces marches remplacent les totaux de jeux en tete d'affichage parce que
backtest_marches_outsider.py les mesure a +8.0/+10.5 pt d'ecart de frequence contre
+2.5/+3.3 pt pour les totaux. Les tests ci-dessous verrouillent ce qui se casserait
sans bruit : l'orientation cote outsider, et le fait qu'aucun over ne vienne se
greffer sur "prend un set" (la mesure dit que ca fait tomber le signal a +6.9 pt).
"""
import unittest

from app import tennis
from app.tennis_calibration import _score_outcomes


class ScoreOutcomesTests(unittest.TestCase):
    def test_favorite_wins_set_1_reads_the_opening_set(self):
        # Le score est ecrit du point de vue du vainqueur : ici il gagne 6-4 le set 1.
        outcomes = _score_outcomes("6-4 6-3", favorite_won=True)
        self.assertEqual(1.0, outcomes["favorite_wins_set_1"])

    def test_favorite_losing_the_opening_set_but_winning_the_match(self):
        outcomes = _score_outcomes("4-6 6-3 6-2", favorite_won=True)
        self.assertEqual(0.0, outcomes["favorite_wins_set_1"])

    def test_set_1_is_flipped_when_the_favorite_lost_the_match(self):
        # Vainqueur = outsider et il remporte la manche d'ouverture : du point de vue du
        # favori, le set 1 est perdu. C'est l'inversion la plus facile a rater.
        outcomes = _score_outcomes("6-4 6-3", favorite_won=False)
        self.assertEqual(0.0, outcomes["favorite_wins_set_1"])

    def test_outsider_wins_match_after_losing_set_1(self):
        outcomes = _score_outcomes("4-6 6-3 6-2", favorite_won=False)
        self.assertEqual(1.0, outcomes["favorite_wins_set_1"])

    def test_cover_3_5_is_stricter_than_cover_2_5(self):
        # Marge favori = 3 jeux : couvre 2.5 mais pas 3.5.
        outcomes = _score_outcomes("6-4 6-5", favorite_won=True)
        self.assertEqual(1.0, outcomes["favorite_cover_2_5"])
        self.assertEqual(0.0, outcomes["favorite_cover_3_5"])

    def test_cover_3_5_on_a_wide_margin(self):
        outcomes = _score_outcomes("6-1 6-2", favorite_won=True)
        self.assertEqual(1.0, outcomes["favorite_cover_3_5"])


def _calibration(**rates):
    base = {
        "favorite_2_1_share": 0.38,
        "favorite_cover_3_5": 0.5,
        "favorite_wins_set_1": 0.7,
    }
    base.update(rates)
    return {"rates": base, "sample": 1200, "confidence": "elevee", "training": "2021-2024"}


class OutsiderMarketsTests(unittest.TestCase):
    def test_takes_a_set_is_the_complement_of_the_market_anchored_2_0(self):
        # favori a 70%, part des 2-1 a 38% => P(2-0) = 0.70 * 0.62 = 43.4% => 57% pour le set.
        markets = tennis._outsider_markets("Dupont", 0.70, _calibration())
        takes = next(m for m in markets if m["key"] == "outsider_takes_a_set")
        self.assertEqual(57, takes["prob"])
        self.assertEqual("ancrage marche", takes["source"])

    def test_a_stronger_favorite_lowers_the_chance_of_conceding_a_set(self):
        weak = tennis._outsider_markets("Dupont", 0.60, _calibration())
        strong = tennis._outsider_markets("Dupont", 0.90, _calibration())
        weak_prob = next(m for m in weak if m["key"] == "outsider_takes_a_set")["prob"]
        strong_prob = next(m for m in strong if m["key"] == "outsider_takes_a_set")["prob"]
        self.assertGreater(weak_prob, strong_prob)

    def test_markets_are_oriented_towards_the_outsider(self):
        markets = tennis._outsider_markets("Dupont", 0.70, _calibration())
        for market in markets:
            self.assertIn("Dupont", market["pick"])

    def test_fair_odds_is_the_inverse_of_the_probability(self):
        markets = tennis._outsider_markets("Dupont", 0.70, _calibration(favorite_wins_set_1=0.75))
        set_1 = next(m for m in markets if m["key"] == "outsider_set_1")
        self.assertEqual(25, set_1["prob"])
        self.assertEqual(4.0, set_1["fair_odds"])  # 1 / 0.25

    def test_games_handicap_uses_the_3_5_line(self):
        markets = tennis._outsider_markets("Dupont", 0.70, _calibration(favorite_cover_3_5=0.4))
        handicap = next(m for m in markets if m["key"] == "outsider_games_3_5")
        self.assertEqual(60, handicap["prob"])
        self.assertIn("+3.5", handicap["label"])

    def test_no_over_is_bundled_into_the_takes_a_set_market(self):
        # Garde-fou volontaire : combiner un over a "prend un set" fait tomber le signal
        # mesure de +9.5 a +6.9 pt. Si un jour quelqu'un l'ajoute, ce test doit sauter.
        markets = tennis._outsider_markets("Dupont", 0.70, _calibration())
        takes = next(m for m in markets if m["key"] == "outsider_takes_a_set")
        self.assertNotIn("over", (takes["label"] + takes["pick"]).lower())

    def test_fallback_label_when_the_outsider_name_is_missing(self):
        markets = tennis._outsider_markets(None, 0.70, _calibration())
        self.assertTrue(all("Outsider" in m["pick"] for m in markets))

    def test_each_signal_market_carries_its_measured_edge(self):
        markets = tennis._outsider_markets("Dupont", 0.70, _calibration())
        self.assertTrue(all(m["signal"] for m in markets))


if __name__ == "__main__":
    unittest.main()
