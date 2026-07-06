import gc
import os
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from app.routes_value import collect_manual_csv, router
from app.value.manual_odds_csv import snapshots_from_manual_csv
from app.value.service import collect_manual_csv_snapshots, snapshot_store_stats
from app.value.snapshots import OddsSnapshotStore


CSV_TEXT = """kickoff,home,away,market,selection,odd,bookmaker
2026-08-14T20:45:00Z,Paris SG,Marseille,1x2,home,1.80,book-a
2026-08-14T20:45:00Z,Paris SG,Marseille,1x2,nul,3.60,book-a
2026-08-14T20:45:00Z,Paris SG,Marseille,1x2,away,4.80,book-a
"""


class ManualOddsCsvTests(unittest.TestCase):
    def test_manual_csv_normalizes_1x2_rows(self):
        snapshots = snapshots_from_manual_csv(CSV_TEXT, captured_at="2026-08-14T10:00:00Z")

        self.assertEqual(len(snapshots), 3)
        self.assertEqual({snapshot.selection for snapshot in snapshots}, {"Paris SG", "Draw", "Marseille"})
        self.assertEqual({snapshot.market for snapshot in snapshots}, {"1x2"})
        self.assertEqual({snapshot.bookmaker for snapshot in snapshots}, {"book-a"})
        self.assertTrue(all(snapshot.raw_payload_hash for snapshot in snapshots))

    def test_manual_csv_uses_default_bookmaker_when_missing(self):
        csv_text = """kickoff,home,away,selection,odd
2026-08-14T20:45:00Z,Paris SG,Marseille,Paris SG,1.80
"""
        snapshots = snapshots_from_manual_csv(
            csv_text,
            captured_at="2026-08-14T10:00:00Z",
            default_bookmaker="winamax-manual",
        )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].bookmaker, "winamax-manual")
        self.assertEqual(snapshots[0].source, "manual-csv")

    def test_manual_csv_skips_incomplete_or_invalid_rows(self):
        csv_text = """kickoff,home,away,selection,odd
2026-08-14T20:45:00Z,Paris SG,Marseille,Paris SG,1.00
2026-08-14T20:45:00Z,Paris SG,,Paris SG,1.80
2026-08-14T20:45:00Z,Paris SG,Marseille,Paris SG,1.80
"""
        snapshots = snapshots_from_manual_csv(csv_text, captured_at="2026-08-14T10:00:00Z")

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].odd, 1.80)

    def test_service_inserts_and_deduplicates_manual_csv(self):
        db_path = os.path.abspath(f"manual_csv_test_{uuid.uuid4().hex}.db")
        try:
            store = OddsSnapshotStore(db_path)
            first = collect_manual_csv_snapshots(
                CSV_TEXT,
                captured_at="2026-08-14T10:00:00Z",
                store=store,
            )
            second = collect_manual_csv_snapshots(
                CSV_TEXT,
                captured_at="2026-08-14T10:00:00Z",
                store=store,
            )
            stats = snapshot_store_stats(store)

            self.assertEqual(first.generated_count, 3)
            self.assertEqual(first.inserted_count, 3)
            self.assertEqual(second.inserted_count, 0)
            self.assertEqual(stats.by_source, {"manual-csv": 3})
        finally:
            store = None
            gc.collect()
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except PermissionError:
                    pass

    def test_router_exposes_manual_csv_collection_endpoint(self):
        self.assertTrue(any(route.path.endswith("/collect/manual-csv") for route in router.routes))

    def test_manual_csv_route_returns_collection_result(self):
        result = SimpleNamespace(
            source="manual-csv",
            captured_at="2026-08-14T10:00:00Z",
            generated_count=3,
            inserted_count=3,
            db_path="test.db",
        )
        with patch("app.routes_value.service.collect_manual_csv_snapshots", return_value=result) as mocked:
            response = collect_manual_csv(
                CSV_TEXT,
                default_bookmaker="manual-book",
                default_sport="football",
                default_competition="ligue1",
                captured_at="2026-08-14T10:00:00Z",
                user={"id": 1},
            )

        mocked.assert_called_once_with(
            CSV_TEXT,
            captured_at="2026-08-14T10:00:00Z",
            default_bookmaker="manual-book",
            default_sport="football",
            default_competition="ligue1",
        )
        self.assertEqual(response["source"], "manual-csv")
        self.assertEqual(response["generated_count"], 3)


if __name__ == "__main__":
    unittest.main()
