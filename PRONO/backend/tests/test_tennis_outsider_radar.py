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
        # Best-effort : sous Windows le fichier temporaire peut rester verrouille un
        # instant apres la fermeture des connexions, sans incidence sur le test.
        try:
            os.unlink(self.path)
        except (FileNotFoundError, PermissionError):
            pass

    def _insert(self, calculated_at: str, elo_probability: float, winner: str = "Outsider",
                kickoff: str | None = None, tournament: str = "Test",
                players: tuple[str, str] = ("Favori", "Outsider"), pair_key: str = "favori|outsider"):
        if kickoff is None:
            kickoff = (date.today() + timedelta(days=1)).isoformat() + "T12:00"
        p1, p2 = players
        payload = {"joueur1": p1, "joueur2": p2, "outsider": p2}
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT INTO tennis_decisions (
                    calculated_at, kickoff, tour, tournament, surface, pair_key, favorite,
                    favorite_odds, outsider_odds, market_probability, elo_probability,
                    elo_gap, decision, decision_level, concordance, context_label, quality,
                    cycle_favorite, fatigue_favorite, cycle_opponent, fatigue_opponent,
                    payload_json, result_winner
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (calculated_at, kickoff, "ATP", tournament, "Dur", pair_key, p1,
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

    def test_kickoff_drift_collapses_to_one_match(self):
        # Le bug historique : un meme match, capture plusieurs jours de suite, voyait son
        # horaire estime bouger et etait recompte a chaque derive. Trois snapshots, trois
        # kickoffs differents, mais un seul et meme match (meme paire, meme tournoi).
        self._insert("2026-07-26T22:06", 58.0, kickoff="2026-07-26T23:30")
        self._insert("2026-07-27T00:28", 56.0, kickoff="2026-07-27T06:00")
        self._insert("2026-07-28T13:26", 54.0, kickoff="2026-07-29T01:30")
        rows = radar._canonical_history(self.path)
        self.assertEqual(1, len(rows), "les 3 snapshots doivent se reduire a un seul match")
        self.assertEqual("2026-07-28T13:26", rows[0]["calculated_at"], "on garde le dernier snapshot")

    def test_distinct_matches_are_not_merged(self):
        # Deux vrais matchs differents (paires differentes) ne doivent jamais fusionner,
        # meme dans le meme tournoi.
        self._insert("2026-07-20T09:00", 55.0, players=("Favori", "Outsider"), pair_key="favori|outsider")
        self._insert("2026-07-20T09:00", 55.0, players=("Nadal", "Alcaraz"), pair_key="alcaraz|nadal")
        rows = radar._canonical_history(self.path)
        self.assertEqual(2, len(rows))

    def test_same_pair_in_two_tournaments_stays_separate(self):
        self._insert("2026-07-20T09:00", 55.0, tournament="Bastad")
        self._insert("2026-07-25T09:00", 55.0, tournament="Gstaad",
                     kickoff=(date.today() + timedelta(days=2)).isoformat() + "T12:00")
        rows = radar._canonical_history(self.path)
        self.assertEqual(2, len(rows))

    def test_recent_summary_counts_unique_matches(self):
        # Cinq snapshots du meme match (le cas Kaji-Preston observe en prod) doivent
        # compter pour UN, pas cinq.
        for day, hour in enumerate(("22:06", "00:28", "13:26", "09:00", "15:00")):
            self._insert(f"2026-07-2{6+day//2}T{hour}", 54.0,
                         kickoff=f"2026-07-2{6+day}T{hour}")
        result = radar.recent_outsiders(days=90, path=self.path)
        self.assertEqual(1, result["canonical_match_count"])
        self.assertEqual(1, result["upset_count"])
        self.assertEqual(100.0, result["upset_rate"])


class MatchIdentityTests(unittest.TestCase):
    def test_identity_ignores_kickoff_and_is_stable(self):
        from app import tennis
        a = tennis._match_identity("ATP", "Odlum Brown VanOpen", "kaji|preston")
        b = tennis._match_identity("atp", "  Odlum Brown VanOpen  ", "kaji|preston")
        self.assertEqual(a, b)  # casse et espaces normalises, aucune trace d'horaire
        self.assertEqual("ATP|odlum brown vanopen|kaji|preston", a)
        # avec ou sans horaire different, l'identite ne bouge pas (il n'y en a pas dedans)
        self.assertEqual(a, tennis._match_identity("ATP", "Odlum Brown VanOpen", "kaji|preston"))

    def test_different_pairs_get_different_identities(self):
        from app import tennis
        self.assertNotEqual(
            tennis._match_identity("ATP", "Gstaad", "a|b"),
            tennis._match_identity("ATP", "Gstaad", "c|d"),
        )


class MatchIdColumnTests(unittest.TestCase):
    """Quand la colonne match_id existe, elle prime, meme si le tournoi differe d'un
    snapshot a l'autre (orthographe qui bouge)."""

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        with sqlite3.connect(self.path) as db:
            db.executescript(SCHEMA.replace("payload_json TEXT,", "payload_json TEXT, match_id TEXT,"))

    def tearDown(self):
        # Best-effort : sous Windows le fichier temporaire peut rester verrouille un
        # instant apres la fermeture des connexions, sans incidence sur le test.
        try:
            os.unlink(self.path)
        except (FileNotFoundError, PermissionError):
            pass

    def test_shared_match_id_collapses_despite_diverging_fields(self):
        payload = json.dumps({"joueur1": "Favori", "joueur2": "Outsider", "outsider": "Outsider"})
        with sqlite3.connect(self.path) as db:
            for stamp, tournament in (("2026-07-26T22:00", "VanOpen"), ("2026-07-27T22:00", "Van Open")):
                db.execute(
                    """INSERT INTO tennis_decisions (calculated_at, kickoff, tour, tournament,
                       surface, pair_key, favorite, market_probability, elo_probability, elo_gap,
                       payload_json, result_winner, match_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (stamp, "2026-07-28T01:30", "ATP", tournament, "Dur", "favori|outsider",
                     "Favori", 66.7, 54.0, -8.0, payload, "Outsider", "ATP|vanopen-stable|favori|outsider"),
                )
        rows = radar._canonical_history(self.path)
        self.assertEqual(1, len(rows))


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
