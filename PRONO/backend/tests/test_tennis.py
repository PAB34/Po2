import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from app.tennis_coach import DATASET_DIR
from app.tennis_props import TennisPropsEngine
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

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_tennisexplorer_odds", return_value=[]), patch.object(tennis, "fetch_scoreboard_snapshot", return_value=([], [])), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        self.assertEqual(payload["feed_updated"], "2026-07-17T12:00:00Z")
        self.assertEqual(len(payload["atp"]), 1)
        self.assertEqual(payload["atp"][0]["surface"], "Terre")
        self.assertEqual(payload["atp"][0]["favori"], "Market Player A")
        self.assertEqual(payload["atp"][0]["match"], "Market Player A vs Market Player B")
        self.assertIn("proba_brute", payload["atp"][0])
        self.assertIn("preuves", payload["atp"][0])
        self.assertIn("markets", payload["atp"][0])
        self.assertIn("qualite", payload["atp"][0])
        self.assertIn("elo_detail", payload["atp"][0])
        self.assertIn("proba_elo_surface", payload["atp"][0])
        self.assertIn("proba_elo_global", payload["atp"][0])
        self.assertEqual("historique calibre", payload["atp"][0]["markets"][0]["source"])
        self.assertEqual(
            {"total_games", "handicap_games", "aces", "double_faults", "hold", "breaks", "tiebreak"},
            {m["key"] for m in payload["atp"][0]["markets"]},
        )
        self.assertIn("props", payload["atp"][0])
        self.assertIn("concordance", payload["atp"][0])
        self.assertEqual(len(payload["atp"][0]["levels"]), 2)
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
        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_tennisexplorer_odds", return_value=[]), patch.object(tennis, "fetch_scoreboard_snapshot", return_value=([], [])), patch.object(tennis, "_now_paris", return_value=now), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
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

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_tennisexplorer_odds", return_value=[]), patch.object(tennis, "fetch_scoreboard_snapshot", return_value=([], [])), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value=secondary):
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

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_tennisexplorer_odds", return_value=[]), patch.object(tennis, "fetch_scoreboard_snapshot", return_value=([], [])), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        row = payload["atp"][0]
        self.assertEqual(row["favori"], "Ruud C.")
        self.assertEqual(row["h2h"], "1-0")
        self.assertIn("Gstaad 2025", row["alerte"])
        self.assertEqual(row["proba"], row["proba_marche"])
        self.assertIsNone(row["ajustement"])
        self.assertIn(row["decision"], {"Vigilance", "Vigilance forte"})
        self.assertLess(row["proba_elo"], row["proba_marche"])
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

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_tennisexplorer_odds", return_value=[]), patch.object(tennis, "fetch_scoreboard_snapshot", return_value=(scoreboard, [])), patch.object(tennis, "_now_paris", return_value=now), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        self.assertEqual(payload["scoreboard_source"], "ESPN")
        self.assertEqual(payload["scoreboard_count"], 1)
        self.assertEqual(payload["filtered_unpriced"], 1)
        self.assertEqual(len(payload["atp"]), 0)
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

        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_tennisexplorer_odds", return_value=[]), patch.object(tennis, "fetch_scoreboard_snapshot", return_value=(scoreboard, [])), patch.object(tennis, "_now_paris", return_value=now), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        row = payload["atp"][0]
        self.assertEqual(row["odds_status"], "ok")
        self.assertEqual(row["odds_source"], "market-feed")
        self.assertEqual(row["cote"], 2.82 if row["favori"] == "Alejandro Tabilo" else 1.42)
        self.assertNotEqual(row["proba_marche"], 50.0)

    def test_parse_tennisexplorer_day_extracts_singles_with_odds(self):
        html = """
        <table class="result">
        <tr class="head flags"><td class="t-name" colspan="2"><a href="/estoril/2026/atp-men/">Estoril</a></td></tr>
        <tr class="bott one"><td class="t-name"><a href="/player/torres-1/">Torres T.</a></td><td class="h2h">1</td><td class="course" rowspan="2">3.45</td><td class="course" rowspan="2">1.30</td></tr>
        <tr class="one"><td class="t-name"><a href="/player/basila-2/">Basilashvili N.</a></td><td class="h2h">1</td></tr>
        <tr class="head flags"><td class="t-name" colspan="2"><a href="/iasi-wta/2026/wta-women/">Iasi</a></td></tr>
        <tr class="bott one"><td class="t-name"><a href="/player/sherif-3/">Sherif M.</a></td><td class="course" rowspan="2">2.53</td><td class="course" rowspan="2">1.51</td></tr>
        <tr class="one"><td class="t-name"><a href="/player/badosa-4/">Badosa P.</a></td></tr>
        <tr class="head flags"><td class="t-name" colspan="2"><a href="/prague/2026/wta-women/?type=double">Doubles</a></td></tr>
        <tr class="bott one"><td class="t-name"><a href="/doubles-team/team-9/">Team A/B</a></td><td class="course" rowspan="2">1.90</td><td class="course" rowspan="2">1.90</td></tr>
        <tr class="one"><td class="t-name"><a href="/doubles-team/team-10/">Team C/D</a></td></tr>
        <tr class="head flags"><td class="t-name" colspan="2"><a href="/palermo/2026/wta-women/">Palermo</a></td></tr>
        <tr class="bott one"><td class="t-name"><a href="/player/noodds-5/">NoOdds A.</a></td><td class="score">&nbsp;</td></tr>
        <tr class="one"><td class="t-name"><a href="/player/noodds-6/">NoOdds B.</a></td></tr>
        </table>
        """
        parsed = tennis._parse_te_day(html)
        self.assertEqual(len(parsed), 2)  # doubles et match sans cote ignores
        self.assertEqual(parsed[0], {"tour": "ATP", "player1": "Torres T.", "player2": "Basilashvili N.", "odds1": 3.45, "odds2": 1.30, "source": "tennisexplorer"})
        self.assertEqual(parsed[1], {"tour": "WTA", "player1": "Sherif M.", "player2": "Badosa P.", "odds1": 2.53, "odds2": 1.51, "source": "tennisexplorer"})

    def test_tennisexplorer_odds_price_upcoming_scoreboard_match(self):
        feed = {"last_updated": "2026-07-19T19:00:00Z", "matches": []}
        scoreboard = [{
            "tour": "ATP", "tournament": "Generali Open",
            "player1": "Mariano Navone", "player2": "Alexandre Muller",
            "kickoff": "2026-07-20T11:00:00+02:00", "source": "ESPN",
        }]
        te_odds = [{"tour": "ATP", "player1": "Muller A.", "player2": "Navone M.", "odds1": 4.58, "odds2": 1.19, "source": "tennisexplorer"}]
        now = datetime(2026, 7, 19, 22, 0, tzinfo=tennis.PARIS_TZ)
        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_tennisexplorer_odds", return_value=te_odds), patch.object(tennis, "fetch_scoreboard_snapshot", return_value=(scoreboard, [])), patch.object(tennis, "_now_paris", return_value=now), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()

        self.assertEqual(payload["te_odds_count"], 1)
        self.assertEqual(payload["filtered_unpriced"], 0)
        self.assertEqual(len(payload["atp"]), 1)
        row = payload["atp"][0]
        self.assertEqual(row["odds_status"], "ok")
        self.assertEqual(row["match"], "Mariano Navone vs Alexandre Muller")
        self.assertEqual(row["favori"], "Mariano Navone")
        self.assertEqual(row["cote"], 1.19)

    def test_dual_anchor_range_spread_and_single(self):
        # Elo indisponible -> ancre marche seule, pas de fausse fourchette
        no_elo = tennis._dual_anchor(40, None)
        self.assertEqual(no_elo, {"value_market": 40, "value_elo": None, "value_ref": 40, "range_min": 40, "range_max": 40, "spread": None, "single": True})
        # ecart < 3 pts -> valeur unique (single True) mais les deux valeurs restent tracees
        tight = tennis._dual_anchor(40, 41)
        self.assertEqual(tight["spread"], 1)
        self.assertTrue(tight["single"])
        # conflit fort -> fourchette complete, bornes triees min/max
        wide = tennis._dual_anchor(36, 45)
        self.assertEqual((wide["range_min"], wide["range_max"], wide["spread"], wide["single"]), (36, 45, 9, False))
        self.assertEqual((wide["value_market"], wide["value_elo"], wide["value_ref"]), (36, 45, 36))
        flipped = tennis._dual_anchor(45, 36)
        self.assertEqual((flipped["range_min"], flipped["range_max"]), (36, 45))

    def test_anchor_values_support_favorite_below_50_and_backcompat(self):
        calib = {"rates": {"favorite_2_1_share": 0.38, "three_sets": 0.34, "over_22_5": 0.5, "favorite_cover_2_5": 0.4}}
        # cas conflit d'identite du favori: proba < 0.5 supportee, p20+p21 = proba favori
        low = tennis._anchor_values(0.45, calib)
        self.assertEqual(low["p20"] + low["p21"], 45)
        self.assertEqual(low["p3"], 34)
        # non-regression: memes formules qu'avant pour une ancre standard
        std = tennis._anchor_values(0.60, calib)
        self.assertEqual((std["p20"], std["p21"], std["p3"], std["total_games"], std["handicap"]), (37, 23, 34, 50, 40))

    def _dual_row(self):
        pairs = {"p20": (38, 30), "p21": (23, 18), "p3": (36, 45), "total_games": (50, 52), "handicap": (40, 38)}
        derived = {key: tennis._dual_anchor(market, elo) for key, (market, elo) in pairs.items()}
        derived.update(anchor_recommended="market", calibration_flag="en attente", elo_available=True, favorite_conflict=False)
        return {"decision": "Vigilance forte", "concordance": "conflict", "p20": 38, "p21": 23, "p3": 36, "derived_anchors": derived}

    def test_apply_anchor_recommendation_picks_elo_when_better_calibrated(self):
        row = self._dual_row()
        report = {"min_sample": 50, "primary": [{"bucket": "Vigilance forte x conflict", "n": 120, "conclusion": "favori_surcote_historique", "favorite_win_rate": 55.0, "market_probability": 61.8, "delta_points": -6.8, "brier_market": 0.24, "brier_elo": 0.21}]}
        tennis._apply_anchor_recommendations([row], report, min_sample=50)
        self.assertEqual(row["derived_anchors"]["anchor_recommended"], "elo")
        self.assertEqual(row["derived_anchors"]["p3"]["value_ref"], 45)
        self.assertEqual(row["p3"], 45)  # scalaire retro-compat bascule aussi
        self.assertEqual(row["p20"], 30)

    def test_apply_anchor_recommendation_defaults_and_flags(self):
        # bucket a echantillon trop faible -> marche par defaut + flag
        weak = self._dual_row()
        weak_report = {"min_sample": 50, "primary": [{"bucket": "Vigilance forte x conflict", "n": 10, "conclusion": "favori_surcote_historique", "brier_market": 0.24, "brier_elo": 0.21}]}
        tennis._apply_anchor_recommendations([weak], weak_report, min_sample=50)
        self.assertEqual(weak["derived_anchors"]["anchor_recommended"], "market")
        self.assertEqual(weak["derived_anchors"]["calibration_flag"], "calibration insuffisante")
        self.assertEqual(weak["p3"], 36)  # inchange
        # delta non significatif -> indetermine
        noisy = self._dual_row()
        noisy_report = {"min_sample": 50, "primary": [{"bucket": "Vigilance forte x conflict", "n": 120, "conclusion": "bruit_probable", "favorite_win_rate": 60.0, "market_probability": 61.8, "delta_points": -1.8, "brier_market": 0.24, "brier_elo": 0.21}]}
        tennis._apply_anchor_recommendations([noisy], noisy_report, min_sample=50)
        self.assertEqual(noisy["derived_anchors"]["anchor_recommended"], "indetermine")
        # Elo indisponible -> ancre marche, aucune bascule
        blind = self._dual_row()
        blind["derived_anchors"]["elo_available"] = False
        tennis._apply_anchor_recommendations([blind], {"min_sample": 50, "primary": []}, min_sample=50)
        self.assertEqual(blind["derived_anchors"]["anchor_recommended"], "market")
        self.assertEqual(blind["derived_anchors"]["calibration_flag"], "elo indisponible")

    def test_build_tennis_exposes_derived_anchors_without_history(self):
        feed = {"last_updated": "2026-07-17T12:00:00Z", "matches": [{"tour": "ATP", "tournament": "Gstaad", "player1": "Cerundolo J. (6)", "player2": "Ruud C. (2)", "odds1": 3.43, "odds2": 1.31}]}
        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_tennisexplorer_odds", return_value=[]), patch.object(tennis, "fetch_scoreboard_snapshot", return_value=([], [])), patch.object(tennis.TennisCoach, "_sportscore_freshness", return_value={"status": "unavailable"}):
            payload = tennis.build_tennis()
        row = payload["atp"][0]
        da = row["derived_anchors"]
        for key in tennis.DERIVED_ANCHOR_KEYS:
            self.assertIn("value_market", da[key])
            self.assertIn("range_min", da[key])
        self.assertTrue(da["elo_available"])
        self.assertIsNotNone(da["p3"]["value_elo"])
        # sans historique en test -> ancre marche, scalaires retro-compat = value_market (non-regression)
        self.assertEqual(da["anchor_recommended"], "market")
        self.assertEqual(row["p3"], da["p3"]["value_market"])
        self.assertEqual(row["p20"], da["p20"]["value_market"])
        self.assertEqual(row["p21"], da["p21"]["value_market"])

    def test_sampling_uncertainty_widens_sparse_extreme_bins(self):
        coach = tennis._coach()
        # Favori moyen (bin1, gros echantillon) -> fourchette serree, confiance haute, pas de note
        mid = tennis._build_derived_anchors("ATP", "Dur", 0.65, coach.market_priors("ATP", "Dur", 0.65), 0.63)
        # Gros favori (bin3) -> incertitude plus large, confiance bridee, note directionnelle
        strong = tennis._build_derived_anchors("WTA", "Dur", 0.85, coach.market_priors("WTA", "Dur", 0.85), 0.82)
        # Favori extreme (bin4, echantillon faible) -> plus large encore, confiance faible
        extreme = tennis._build_derived_anchors("WTA", "Dur", 0.95, coach.market_priors("WTA", "Dur", 0.95), 0.9)

        self.assertLessEqual(mid["p20"]["uncertainty_pts"], strong["p20"]["uncertainty_pts"])
        self.assertLess(strong["p20"]["uncertainty_pts"], extreme["p20"]["uncertainty_pts"])
        self.assertEqual(mid["strength_bin"], 1)
        self.assertIsNone(mid.get("reliability_note"))
        self.assertEqual(mid["split_confidence"], "elevee")
        self.assertGreaterEqual(strong["strength_bin"], 3)
        self.assertNotEqual(strong["split_confidence"], "elevee")  # bridee malgre un n correct
        self.assertIn("WTA", strong["reliability_note"])
        self.assertEqual(extreme["split_confidence"], "faible")
        # la fourchette elargie contient bien la valeur marche
        self.assertLessEqual(extreme["p20"]["range_min"], extreme["p20"]["value_market"])
        self.assertGreaterEqual(extreme["p20"]["range_max"], extreme["p20"]["value_market"])

    def test_form_signals_do_not_shift_market_probability(self):
        coach = tennis._coach()
        stats_hot = {
            "matchs_90j": 12,
            "serie": 8,
            "momentum_90j": 35,
            "winrate_90j": 0.9,
            "derniere_date": "2026-07-17",
        }
        stats_cold = dict(stats_hot, serie=-5, momentum_90j=-30, winrate_90j=0.2)
        self.assertEqual(coach.context_assessment(stats_hot, None)["score"], coach.context_assessment(stats_cold, None)["score"])

    def test_form_label_is_independent_from_tournament_load(self):
        coach = tennis._coach()
        stats = {
            "matchs_90j": 8, "serie": 3, "momentum_90j": 10,
            "winrate_90j": 0.75, "derniere_date": "2026-07-18",
        }
        heavy_load = {
            "tours_gagnes": 3, "sets_laches": 2, "jeux_joues": 80,
            "dernier_jeux": 32, "decisifs": 2, "tiebreaks": 2,
            "matchs_14j": 6, "charge_minutes_est": 220, "repos_jours": 0,
        }
        fresh = coach.cycle("Player A", stats, None)
        tired = coach.cycle("Player A", stats, heavy_load)
        self.assertEqual(fresh["label"], tired["label"])
        self.assertEqual(tired["fatigue"], "charge lourde")
        self.assertLess(tired["combined_score"], tired["score"])

    def test_elo_divergence_creates_vigilance_and_range_without_shifting_market(self):
        neutral = {"score": 0.0, "label": "neutre", "positives": [], "risks": []}
        decision = tennis._coach()._decision(0.60, 0.45, neutral, neutral, 0.90)
        aligned = tennis._coach()._decision(0.60, 0.59, neutral, neutral, 0.90)
        self.assertEqual(decision["label"], "Vigilance forte")
        self.assertAlmostEqual(sum(decision["range_p1"]) / 2, 0.60)
        self.assertGreater(decision["range_p1"][1] - decision["range_p1"][0], aligned["range_p1"][1] - aligned["range_p1"][0])

    def test_context_label_is_explicitly_relative(self):
        favorite = {"score": -0.06, "label": "defavorable", "positives": [], "risks": ["charge lourde"]}
        opponent = {"score": -0.14, "label": "defavorable", "positives": ["trois tours franchis"], "risks": ["charge tres lourde"]}
        decision = tennis._coach()._decision(0.67, 0.55, favorite, opponent, 0.90)
        self.assertEqual(decision["label"], "Vigilance forte")
        self.assertEqual(decision["context_label"], "avantage relatif")

    def test_surface_elo_does_not_silently_fallback_to_global(self):
        coach = tennis._coach()
        stats = {"elo_global": 1700, "elo_clay": None}
        self.assertIsNone(coach._surface_elo(stats, "clay"))
        self.assertEqual(coach._global_elo(stats), 1700.0)

    def test_decision_history_is_persisted_and_reconciled(self):
        row = {
            "tour": "ATP", "kickoff": "2026-07-18T14:00:00+02:00", "tournoi": "Test Open",
            "joueur1": "Player A", "joueur2": "Player B", "favori": "Player A",
            "cote": 1.8, "proba_marche": 55.0, "proba_elo": 53.0, "ecart_elo": -2.0,
            "decision": "Neutre", "decision_level": "neutral", "impact_contexte": "neutre",
            "qualite": "moyenne", "fourchette_min": 50.0, "fourchette_max": 60.0,
        }
        completed = [{"winner": "Player A", "loser": "Player B"}]
        calculated_at = datetime(2026, 7, 18, 12, 0, tzinfo=tennis.PARIS_TZ)
        with tempfile.TemporaryDirectory(dir=r"C:\tmp") as directory, patch.dict(os.environ, {"PRONO_DATA_DIR": directory}):
            self.assertTrue(tennis._record_decision_history([row], completed, calculated_at))
            path = os.path.join(directory, "tennis", "decision_history.sqlite3")
            with sqlite3.connect(path) as db:
                cursor = db.execute("SELECT market_probability, decision, result_winner FROM tennis_decisions")
                stored = cursor.fetchone()
                cursor.close()
            db.close()
        self.assertEqual(stored, (55.0, "Neutre", "Player A"))

    def test_calibration_improves_2025_holdout(self):
        report = tennis._coach().calibration_report(2025)
        self.assertGreater(report["count"], 4000)
        for scores in report["markets"].values():
            self.assertLess(scores["brier"], scores["baseline_brier"])

    def test_player_props_are_surface_specific_and_validated_out_of_sample(self):
        props = tennis._coach().props.predict("ATP", "clay", "Alejandro Tabilo", "Andrey Rublev")
        self.assertEqual(props["surface"], "clay")
        self.assertEqual(len(props["players"]), 2)
        self.assertGreater(props["players"][0]["sample_surface"], 20)
        self.assertGreater(props["players"][0]["aces_expected"], 0)
        self.assertGreater(props["players"][0]["hold_probability"], 50)
        self.assertGreater(props["players"][0]["break_probability"], 0)
        for scores in props["validation"].values():
            self.assertTrue(scores["validated"])
            self.assertGreater(scores["sample"], 4000)
            self.assertLess(scores["brier"], scores["baseline_brier"])

    def test_concordance_flags_market_elo_conflict(self):
        coach = tennis._coach()
        conflict = coach._concordance(
            0.68, {"elo_gap_favorite": -0.2}, {"score": -0.1}, {"score": 0.1}, 0.9,
        )
        aligned = coach._concordance(
            0.62, {"elo_gap_favorite": 0.02}, {"score": 0.1}, {"score": -0.1}, 0.9,
        )
        self.assertEqual(conflict["level"], "conflict")
        self.assertEqual(aligned["level"], "aligned")

    def test_multi_surname_alias_restores_merida_elo_without_faking_service_stats(self):
        coach = tennis._coach()
        stats = coach.player_stats("Daniel Merida", "ATP")
        level = coach.level_profile("Daniel Merida", "ATP", "Terre")
        with patch.dict(os.environ, {"PRONO_TENNIS_LIVE_STATS": "0"}):
            props = coach.props.predict("ATP", "clay", "Damir Dzumhur", "Daniel Merida")

        self.assertEqual(stats["player"], "Merida Aguilar D.")
        self.assertEqual(level["elo_global"], 1568.0)
        self.assertEqual(level["elo_surface"], 1562.0)
        self.assertEqual(level["sample"], 10)
        self.assertIsNotNone(props["players"][0])
        self.assertIsNone(props["players"][1])

    def test_live_atp_feed_fills_missing_merida_service_profile(self):
        engine = TennisPropsEngine(DATASET_DIR)
        live_rows = [{
            "tourney_date": "2026-07-17T00:00:00.000Z",
            "surface": "Clay",
            "winner_name": "Daniel Merida",
            "loser_name": "Roman Andres Burruchaga",
            "score": "6-4 6-2",
            "w_ace": 4,
            "w_df": 1,
            "w_SvGms": 9,
            "w_bpSaved": 3,
            "w_bpFaced": 4,
            "l_ace": 1,
            "l_df": 1,
            "l_SvGms": 9,
            "l_bpSaved": 5,
            "l_bpFaced": 9,
        }]

        invalid = {**live_rows[0], "w_bpSaved": 5}
        self.assertIsNone(engine._parse_match("ATP", invalid))


        with patch.dict(os.environ, {"PRONO_TENNIS_LIVE_STATS": "1"}), patch.object(
            engine.live_source, "player_matches", return_value=live_rows,
        ) as fetch:
            props = engine.predict("ATP", "clay", "Damir Dzumhur", "Daniel Merida")

        fetch.assert_called_once_with("Daniel Merida")
        merida = props["players"][1]
        self.assertIsNotNone(merida)
        self.assertEqual(merida["sample_surface"], 1)
        self.assertEqual(merida["source"], "TennisMyLife live + archives")
        self.assertGreater(merida["aces_expected"], 0)
        self.assertGreater(merida["break_probability"], 0)

    def test_full_wta_name_keeps_elo_when_advanced_stats_use_another_spelling(self):
        coach = tennis.TennisCoach()

        krejcikova = coach.player_stats("Barbora Krejcikova", "WTA")
        tauson = coach.player_stats("Clara Tauson", "WTA")

        self.assertEqual(krejcikova["elo_global"], 1554)
        self.assertEqual(krejcikova["matchs_chartes"], 28)
        self.assertEqual(tauson["elo_global"], 1477)
        self.assertEqual(tauson["matchs_chartes"], 41)

    def test_live_match_is_kept_after_kickoff_grace(self):
        now = datetime(2026, 7, 18, 18, 0, tzinfo=tennis.PARIS_TZ)
        timing = tennis._match_timing(
            {"kickoff": "2026-07-18T15:00:00+02:00", "live": True}, now, now,
        )
        self.assertFalse(timing["past"])
        self.assertEqual(timing["display"], "En cours - 15:00")

    def test_unpriced_final_is_exposed_without_fake_market_probability(self):
        feed = {"last_updated": "2026-07-18T20:00:00+02:00", "matches": []}
        scoreboard = [{
            "tour": "ATP", "tournament": "EFG Swiss Open Gstaad",
            "player1": "Raphael Collignon", "player2": "Stefanos Tsitsipas",
            "kickoff": "2026-07-19T11:30:00+02:00", "source": "ESPN", "round": "Final",
        }]
        now = datetime(2026, 7, 18, 20, 30, tzinfo=tennis.PARIS_TZ)
        with patch.object(tennis, "fetch_feed", return_value=feed), patch.object(tennis, "fetch_tennisexplorer_odds", return_value=[]), patch.object(tennis, "fetch_scoreboard_snapshot", return_value=(scoreboard, [])), patch.object(tennis, "_now_paris", return_value=now):
            payload = tennis.build_tennis()

        self.assertEqual(payload["atp"], [])
        self.assertEqual(len(payload["pending_odds"]), 1)
        final = payload["pending_odds"][0]
        self.assertEqual(final["match"], "Raphael Collignon vs Stefanos Tsitsipas")
        self.assertEqual(final["odds_status"], "en_attente")
        self.assertNotIn("proba_marche", final)
        self.assertIn("props", final)

    def test_completed_scoreboard_match_feeds_fatigue_context(self):
        competition = {
            "competitors": [
                {"winner": True, "athlete": {"displayName": "Winner A"}, "linescores": [{"value": 6}, {"value": 7}]},
                {"winner": False, "athlete": {"displayName": "Loser B"}, "linescores": [{"value": 4}, {"value": 6}]},
            ]
        }
        kickoff = datetime(2026, 7, 18, 10, 0, tzinfo=tennis.PARIS_TZ)
        row = tennis._completed_scoreboard_row(competition, "ATP", "Nordea Open", kickoff)
        self.assertEqual(row["winner"], "Winner A")
        self.assertEqual(row["games_w"], 13)
        self.assertEqual(row["sets_w"], 2)
        self.assertEqual(row["tiebreaks"], 1)
if __name__ == "__main__":
    unittest.main()
