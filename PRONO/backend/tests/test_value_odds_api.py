import gc
import os
import unittest
import uuid

from app.value.odds_api import OddsApiNotConfigured, OddsApiRequest, build_odds_url
from app.value.service import collect_the_odds_api_snapshots, snapshot_store_stats
from app.value.snapshots import OddsSnapshotStore


class OddsApiClientTests(unittest.TestCase):
    def test_build_odds_url_contains_core_parameters(self):
        url = build_odds_url(
            OddsApiRequest(sport_key="tennis_atp_french_open", regions="eu", markets="h2h", bookmakers="pinnacle"),
            api_key="secret",
        )
        self.assertIn("/sports/tennis_atp_french_open/odds/", url)
        self.assertIn("apiKey=secret", url)
        self.assertIn("regions=eu", url)
        self.assertIn("markets=h2h", url)
        self.assertIn("bookmakers=pinnacle", url)

    def test_build_odds_url_requires_api_key(self):
        with self.assertRaises(OddsApiNotConfigured):
            build_odds_url(OddsApiRequest(sport_key="soccer_france_ligue_one"), api_key="")


class OddsApiCollectionServiceTests(unittest.TestCase):
    def test_collect_the_odds_api_snapshots_from_injected_payload(self):
        db_path = os.path.abspath(f"value_odds_api_test_{uuid.uuid4().hex}.db")
        try:
            store = OddsSnapshotStore(db_path)
            payload = [{
                "id": "match-1",
                "home_team": "Player A",
                "away_team": "Player B",
                "commence_time": "2026-07-03T12:00:00Z",
                "bookmakers": [{
                    "key": "pinnacle",
                    "last_update": "2026-07-02T10:01:00Z",
                    "markets": [{
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Player A", "price": 1.62},
                            {"name": "Player B", "price": 2.35},
                        ],
                    }],
                }],
            }]
            result = collect_the_odds_api_snapshots(
                sport_key="tennis_atp_french_open",
                sport="tennis",
                competition="atp_french_open",
                captured_at="2026-07-02T10:02:00Z",
                store=store,
                events=payload,
            )
            stats = snapshot_store_stats(store)
            self.assertEqual(result.generated_count, 2)
            self.assertEqual(result.inserted_count, 2)
            self.assertEqual(stats.by_source, {"the-odds-api": 2})
        finally:
            store = None
            gc.collect()
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except PermissionError:
                    pass


if __name__ == "__main__":
    unittest.main()
