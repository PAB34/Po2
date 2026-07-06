import gc
import os
import unittest
import uuid

import pandas as pd

from app.value.service import collect_football_data_snapshots, snapshot_store_stats
from app.value.snapshots import OddsSnapshotStore


class ValueServiceTests(unittest.TestCase):
    def test_collect_football_data_snapshots_inserts_and_deduplicates(self):
        db_path = os.path.abspath(f"value_service_test_{uuid.uuid4().hex}.db")
        try:
            store = OddsSnapshotStore(db_path)
            rows = pd.DataFrame([{
                "Kickoff": "2026-08-15 20:00",
                "HomeTeam": "Paris SG",
                "AwayTeam": "Marseille",
                "PSH": 1.70,
                "PSD": 4.10,
                "PSA": 5.20,
            }])
            first = collect_football_data_snapshots(rows=rows, captured_at="2026-08-14T10:00:00Z", store=store)
            second = collect_football_data_snapshots(rows=rows, captured_at="2026-08-14T10:00:00Z", store=store)
            stats = snapshot_store_stats(store)

            self.assertEqual(first.generated_count, 3)
            self.assertEqual(first.inserted_count, 3)
            self.assertEqual(second.generated_count, 3)
            self.assertEqual(second.inserted_count, 0)
            self.assertEqual(stats.total_count, 3)
            self.assertEqual(stats.by_source, {"football-data-fixtures": 3})
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
