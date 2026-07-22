import unittest

from app import tennis_coherence as tc


def _synthetic_matrix() -> dict:
    return {
        "min_sample": 200,
        "markets": list(tc.MARKETS),
        "scopes": {
            "ALL": {
                "all": {
                    "n": 1000,
                    "marginals": {"over_22_5": 0.5, "three_sets": 0.4, "tiebreak": 0.5, "favorite_2_0": 0.5, "favorite_2_1": 0.3, "favorite_cover_2_5": 0.5},
                    "pairs": {
                        "over_22_5|three_sets": {"n": 1000, "p_ab": 0.371, "phi": 0.70},   # correlation forte +
                        "three_sets|tiebreak": {"n": 1000, "p_ab": 0.205, "phi": 0.05},     # quasi independant
                        "favorite_2_0|favorite_cover_2_5": {"n": 150, "p_ab": 0.40, "phi": 0.60},  # n < min -> non evaluee
                    },
                }
            }
        },
    }


class CoherenceMatrixTests(unittest.TestCase):
    def test_build_matrix_recovers_perfect_correlations(self):
        base = {
            "tour": "ATP", "bin": 0,
            "favorite_2_0": 0, "favorite_2_1": 0, "favorite_cover_2_5": 0,
            "over_18_5": 0, "over_19_5": 0,
        }
        records = [
            {**base, "over_22_5": 1, "three_sets": 1, "tiebreak": 0},
            {**base, "over_22_5": 0, "three_sets": 0, "tiebreak": 1},
            {**base, "over_22_5": 1, "three_sets": 1, "tiebreak": 0},
            {**base, "over_22_5": 0, "three_sets": 0, "tiebreak": 1},
        ]
        matrix = tc.build_matrix_from_records(records, min_sample=2)
        pairs = matrix["scopes"]["ALL"]["all"]["pairs"]
        self.assertEqual(pairs["over_22_5|three_sets"]["phi"], 1.0)      # parfaitement correles
        self.assertEqual(pairs["over_22_5|tiebreak"]["phi"], -1.0)       # parfaitement anticorreles
        self.assertEqual(matrix["scopes"]["ALL"]["all"]["n"], 4)

    def test_relation_tension_redundancy_independence_and_side_flip(self):
        matrix = _synthetic_matrix()
        # meme cote -> correlation positive = redondance
        redundant = tc.relation(matrix, "ALL", "over_22_5", "yes", "three_sets", "yes")
        self.assertEqual(redundant["relation"], "redondance")
        self.assertEqual(redundant["strength"], "fort")
        # cote inverse (Under) -> signe inverse = tension
        tension = tc.relation(matrix, "ALL", "over_22_5", "no", "three_sets", "yes")
        self.assertEqual(tension["relation"], "tension")
        self.assertAlmostEqual(tension["phi"], -0.70, places=2)
        self.assertIn("sens oppose", tension["message"])
        # faible correlation -> quasi independant
        indep = tc.relation(matrix, "ALL", "three_sets", "yes", "tiebreak", "yes")
        self.assertEqual(indep["relation"], "quasi_independant")

    def test_relation_below_min_sample_is_not_evaluated(self):
        matrix = _synthetic_matrix()
        rel = tc.relation(matrix, "ALL", "favorite_2_0", "yes", "favorite_cover_2_5", "yes")
        self.assertEqual(rel["relation"], "non_evaluee")
        self.assertIsNone(rel["phi"])
        self.assertIn("insuffisant", rel["message"])

    def test_coherence_flags_only_surfaces_notable_pairs_sorted(self):
        matrix = _synthetic_matrix()
        flags = tc.coherence_flags([("over_22_5", 0), ("three_sets", 1), ("tiebreak", 1)], circuit="ALL", matrix=matrix)
        # over/three -> tension notable ; three/tiebreak -> quasi independant (ignore) ; over/tiebreak absent (ignore)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["relation"], "tension")

    def test_check_ticket_intra_tension_joint_and_inter_match_independence(self):
        matrix = _synthetic_matrix()
        selections = [
            {"match_id": "M1", "circuit": "ALL", "market": "over_22_5", "side": "no"},
            {"match_id": "M1", "circuit": "ALL", "market": "three_sets", "side": "yes"},
            {"match_id": "M1", "circuit": "ALL", "market": "aces", "side": "yes"},   # hors matrice v1
            {"match_id": "M2", "circuit": "ALL", "market": "over_22_5", "side": "yes"},
        ]
        result = tc.check_ticket(selections, matrix=matrix)
        self.assertEqual(result["tension_count"], 1)
        entry = result["intra_match"][0]
        self.assertEqual(entry["relation"], "tension")
        # proba jointe corrigee < produit des probas (les deux se contredisent)
        self.assertLess(entry["joint"]["joint_corrected"], entry["joint"]["joint_independent"])
        # picks hors matrice signales explicitement, pas de flag silencieux
        self.assertTrue(any(u.get("reason") == "hors matrice v1" for u in result["unevaluated"]))
        # paires inter-matchs (M1 x M2 = 3 x 1) traitees comme independantes
        self.assertEqual(result["inter_match_pairs"], 3)


if __name__ == "__main__":
    unittest.main()
