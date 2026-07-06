import gc
import os
import unittest
import uuid

from app.value.clv_report import build_snapshot_clv_report
from app.value.service import snapshot_clv_report
from app.value.snapshots import OddsSnapshot, OddsSnapshotStore


def snapshot(captured_at, odd, selection="Player A", event_id="event-1"):
    return OddsSnapshot(
        sport="tennis",
        competition="atp",
        event_id=event_id,
        participant_1="Player A",
        participant_2="Player B",
        market="h2h",
        selection=selection,
        bookmaker="pinnacle",
        odd=odd,
        captured_at=captured_at,
        commence_time="2026-07-03T12:00:00Z",
        source="test",
    )


class SnapshotClvReportTests(unittest.TestCase):
    def test_report_compares_decision_to_latest_before_kickoff(self):
        report = build_snapshot_clv_report([
            snapshot("2026-07-02T08:00:00Z", 1.90),
            snapshot("2026-07-02T10:00:00Z", 2.00),
            snapshot("2026-07-03T11:30:00Z", 1.80),
        ], decision_at="2026-07-02T09:00:00Z")
        self.assertEqual(len(report.rows), 1)
        row = report.rows[0]
        self.assertEqual(row.decision_odd, 1.90)
        self.assertEqual(row.closing_odd, 1.80)
        self.assertAlmostEqual(row.clv, 1.90 / 1.80 - 1.0, places=6)

    def test_report_uses_latest_snapshot_at_or_before_decision(self):
        report = build_snapshot_clv_report([
            snapshot("2026-07-02T08:00:00Z", 1.90),
            snapshot("2026-07-02T10:00:00Z", 2.00),
            snapshot("2026-07-03T11:30:00Z", 1.80),
        ], decision_at="2026-07-02T10:30:00Z")
        self.assertEqual(report.rows[0].decision_odd, 2.00)
        self.assertEqual(report.rows[0].decision_captured_at, "2026-07-02T10:00:00Z")

    def test_report_skips_without_decision_snapshot(self):
        report = build_snapshot_clv_report([
            snapshot("2026-07-03T11:30:00Z", 1.80),
        ], decision_at="2026-07-02T10:30:00Z")
        self.assertEqual(len(report.rows), 0)
        self.assertEqual(report.skipped_groups, 1)

    def test_service_report_filters_event_and_market(self):
        db_path = os.path.abspath(f"value_clv_test_{uuid.uuid4().hex}.db")
        try:
            store = OddsSnapshotStore(db_path)
            store.insert_many([
                snapshot("2026-07-02T08:00:00Z", 1.90),
                snapshot("2026-07-03T11:30:00Z", 1.80),
                snapshot("2026-07-02T08:00:00Z", 2.10, event_id="event-2"),
                snapshot("2026-07-03T11:30:00Z", 2.00, event_id="event-2"),
            ])
            report = snapshot_clv_report(
                decision_at="2026-07-02T09:00:00Z",
                event_id="event-1",
                market="h2h",
                store=store,
            )
            self.assertEqual(len(report.rows), 1)
            self.assertEqual(report.rows[0].event_id, "event-1")
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
