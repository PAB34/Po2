import gc
import os
import unittest
import uuid

import pandas as pd

from app.value.collectors import snapshots_from_football_data_rows, snapshots_from_the_odds_api_events
from app.value.snapshots import OddsSnapshot, OddsSnapshotStore, payload_hash


class SnapshotStorageTests(unittest.TestCase):
    def test_payload_hash_is_stable(self):
        self.assertEqual(payload_hash({"b": 2, "a": 1}), payload_hash({"a": 1, "b": 2}))

    def test_store_inserts_and_deduplicates_snapshots(self):
        db_path = os.path.abspath(f"value_snapshots_test_{uuid.uuid4().hex}.db")
        try:
            store = OddsSnapshotStore(db_path)
            snapshot = OddsSnapshot(
                sport="tennis",
                competition="atp",
                event_id="event-1",
                participant_1="Player A",
                participant_2="Player B",
                market="h2h",
                selection="Player A",
                bookmaker="book",
                odd=1.75,
                captured_at="2026-07-02T10:00:00Z",
                commence_time="2026-07-03T12:00:00Z",
                source="test",
            )
            self.assertEqual(store.insert_many([snapshot, snapshot]), 1)
            rows = store.list_event_snapshots("event-1", market="h2h")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].selection, "Player A")
        finally:
            store = None
            gc.collect()
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except PermissionError:
                    pass


class SnapshotCollectorTests(unittest.TestCase):
    def test_football_data_rows_create_1x2_snapshots(self):
        rows = pd.DataFrame([{
            "Kickoff": "2026-08-15 20:00",
            "HomeTeam": "Paris SG",
            "AwayTeam": "Marseille",
            "PSH": 1.70,
            "PSD": 4.10,
            "PSA": 5.20,
        }])
        snapshots = snapshots_from_football_data_rows(rows, captured_at="2026-08-14T10:00:00Z")
        self.assertEqual(len(snapshots), 3)
        self.assertEqual({s.market for s in snapshots}, {"1x2"})
        self.assertEqual({s.selection for s in snapshots}, {"Paris SG", "Draw", "Marseille"})
        self.assertTrue(all(s.bookmaker == "Pinnacle" for s in snapshots))

    def test_the_odds_api_events_create_tennis_h2h_snapshots(self):
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
        snapshots = snapshots_from_the_odds_api_events(
            payload,
            captured_at="2026-07-02T10:02:00Z",
            sport="tennis",
            competition="atp",
        )
        self.assertEqual(len(snapshots), 2)
        self.assertEqual({s.market for s in snapshots}, {"h2h"})
        self.assertEqual({s.bookmaker for s in snapshots}, {"pinnacle"})
        self.assertTrue(all(s.last_update == "2026-07-02T10:01:00Z" for s in snapshots))

    def test_the_odds_api_h2h_maps_to_1x2_for_football(self):
        payload = [{
            "id": "match-1",
            "home_team": "Lens",
            "away_team": "Lille",
            "commence_time": "2026-08-10T18:00:00Z",
            "bookmakers": [{
                "key": "book",
                "markets": [{
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Lens", "price": 2.20},
                        {"name": "Draw", "price": 3.30},
                        {"name": "Lille", "price": 3.40},
                    ],
                }],
            }],
        }]
        snapshots = snapshots_from_the_odds_api_events(
            payload,
            captured_at="2026-08-09T10:00:00Z",
            sport="football",
            competition="ligue1",
        )
        self.assertEqual(len(snapshots), 3)
        self.assertEqual({s.market for s in snapshots}, {"1x2"})


if __name__ == "__main__":
    unittest.main()





