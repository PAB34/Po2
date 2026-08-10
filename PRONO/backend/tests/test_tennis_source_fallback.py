"""Repli de source quand ESPN bloque l'IP du VPS (403).

Sans ESPN, l'outil affichait un tour en retard parce qu'il retombait sur le flux GitHub.
Ces tests verrouillent le correctif : tennisexplorer devient la source de repli (a jour,
joignable depuis le VPS) et son parseur capte desormais le nom du tournoi -- sans quoi le
filtre LOW_LEVEL ne s'appliquerait plus et l'UI se noierait sous les UTR/ITF.
"""
import unittest
from datetime import date

from app import tennis


# La 1re ligne du match porte l'heure (`td.first.time`) + les cotes (rowspan=2).
TE_FIXTURE_TIME = """
<table>
<tr class="head flags"><td class="t-name" colspan="2"><a href="/montreal/2026/atp-men/"><span class="fl fl-ca">&nbsp;</span><span class="type-men2">&nbsp;</span>Montreal</a></td></tr>
<tr id="r1" class="one fRow bott"><td class="first time" rowspan="2">22:10<br /><img src="/res/img/icon-tv.gif"/></td><td class="t-name"><a href="/player/jodar/">Jodar R.</a></td><td class="course">1.77</td><td class="course">2.04</td></tr>
<tr id="r2" class="two bott"><td class="t-name"><a href="/player/fils/">Fils A.</a></td></tr>
</table>
"""


TE_FIXTURE = """
<table>
<tr class="head flags"><td class="t-name" colspan="2"><a href="/montreal/2026/atp-men/"><span class="fl fl-ca">&nbsp;</span><span class="type-men2">&nbsp;</span>Montreal</a></td><td class="score">S</td></tr>
<tr class="bott"><td class="t-name"><a href="/player/jodar-rafael/">Jodar R.</a></td><td class="course">1.77</td><td class="course">2.04</td></tr>
<tr class="bott"><td class="t-name"><a href="/player/fils-arthur/">Fils A.</a></td><td class="result">2</td></tr>
<tr class="head flags"><td class="t-name" colspan="2"><a href="/utr-pro-tennis-series-3/2026/atp-men/"><span class="fl fl-us">&nbsp;</span><span class="type-men2">&nbsp;</span>UTR Pro Tennis Series 3</a></td></tr>
<tr class="bott"><td class="t-name"><a href="/player/x/">Player X.</a></td><td class="course">1.50</td><td class="course">2.50</td></tr>
<tr class="bott"><td class="t-name"><a href="/player/y/">Player Y.</a></td><td class="result">1</td></tr>
</table>
"""


class ParseTennisExplorerTests(unittest.TestCase):
    def test_captures_tournament_name_and_odds(self):
        matches = tennis._parse_te_day(TE_FIXTURE)
        self.assertEqual(2, len(matches))
        first = matches[0]
        self.assertEqual("ATP", first["tour"])
        self.assertEqual("Montreal", first["tournament"])
        self.assertEqual("Jodar R.", first["player1"])
        self.assertEqual("Fils A.", first["player2"])
        self.assertEqual(1.77, first["odds1"])
        self.assertEqual(2.04, first["odds2"])

    def test_captures_match_time_and_dates_kickoff_on_the_page_day(self):
        matches = tennis._parse_te_day(TE_FIXTURE_TIME, date(2026, 8, 11))
        self.assertEqual(1, len(matches))
        self.assertEqual("22:10", matches[0]["time"])
        self.assertTrue(matches[0]["kickoff"].startswith("2026-08-11T22:10"))

    def test_time_without_page_day_yields_no_kickoff(self):
        # Sans jour (usage direct/tests), on garde l'heure affichee mais pas de kickoff date.
        matches = tennis._parse_te_day(TE_FIXTURE_TIME)
        self.assertEqual("22:10", matches[0]["time"])
        self.assertIsNone(matches[0]["kickoff"])

    def test_low_level_tournament_name_is_captured_so_it_can_be_filtered(self):
        # Le parseur ne filtre pas, mais il doit livrer le nom pour que LOW_LEVEL agisse.
        matches = tennis._parse_te_day(TE_FIXTURE)
        utr = matches[1]
        self.assertEqual("UTR Pro Tennis Series 3", utr["tournament"])
        self.assertTrue(tennis.LOW_LEVEL.search(utr["tournament"]))
        self.assertFalse(tennis.LOW_LEVEL.search(matches[0]["tournament"]))


class SelectMatchSourceTests(unittest.TestCase):
    def test_espn_scoreboard_wins_when_present(self):
        sb = [{"tour": "ATP", "player1": "A", "player2": "B"}]
        _, source = tennis._select_match_source(sb, [], [{"x": 1}], [{"y": 2}])
        self.assertEqual("ESPN", source)

    def test_tennisexplorer_is_preferred_over_stale_github_feed(self):
        te = [{"tour": "ATP", "tournament": "Montreal", "player1": "Jodar R.", "player2": "Fils A."}]
        github = [{"tour": "ATP", "tournament": "Montreal", "player1": "Shelton B.", "player2": "Fonseca J."}]
        matches, source = tennis._select_match_source([], [], te, github)
        self.assertEqual("tennisexplorer-fallback", source)
        self.assertEqual(te, matches)

    def test_github_feed_is_the_last_resort(self):
        github = [{"tour": "ATP", "player1": "A", "player2": "B"}]
        matches, source = tennis._select_match_source([], [], [], github)
        self.assertEqual("market-feed-fallback", source)
        self.assertEqual(github, matches)


if __name__ == "__main__":
    unittest.main()
