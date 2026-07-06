import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.routes_value import betting_completeness, router
from app.value.betting_completeness import assess_betting_completeness
from app.value.service import betting_completeness_report
from app.value.snapshots import OddsSnapshot


def snapshot(
    selection="Paris SG",
    bookmaker="book-a",
    captured_at="2026-08-14T10:00:00Z",
    commence_time="2026-08-15T20:00:00Z",
    market="1x2",
):
    return OddsSnapshot(
        sport="football",
        competition="ligue1",
        event_id="event-1",
        participant_1="Paris SG",
        participant_2="Marseille",
        market=market,
        selection=selection,
        bookmaker=bookmaker,
        odd=1.80,
        captured_at=captured_at,
        commence_time=commence_time,
        source="test",
        raw_payload_hash="hash",
    )


def complete_snapshots():
    return [
        snapshot(selection="Paris SG", bookmaker="book-a"),
        snapshot(selection="Draw", bookmaker="book-a"),
        snapshot(selection="Marseille", bookmaker="book-a"),
        snapshot(selection="Paris SG", bookmaker="book-b"),
        snapshot(selection="Draw", bookmaker="book-b"),
        snapshot(selection="Marseille", bookmaker="book-b"),
    ]


class BettingCompletenessTests(unittest.TestCase):
    def test_complete_betting_data_scores_high(self):
        report = assess_betting_completeness(
            complete_snapshots(),
            required_markets=("1x2",),
            decision_at="2026-08-14T12:00:00Z",
        )

        self.assertEqual(report.score, 100)
        self.assertEqual(report.status, "complete")
        self.assertEqual(report.bookmaker_count, 2)
        self.assertEqual(report.blocking_missing_data, ())

    def test_no_snapshots_is_blocking(self):
        report = assess_betting_completeness([], decision_at="2026-08-14T12:00:00Z")

        self.assertEqual(report.score, 0)
        self.assertEqual(report.status, "blocked")
        self.assertIn("snapshots", report.blocking_missing_data)

    def test_missing_required_market_is_blocking(self):
        report = assess_betting_completeness(
            complete_snapshots(),
            required_markets=("1x2", "btts"),
            decision_at="2026-08-14T12:00:00Z",
        )

        self.assertEqual(report.status, "blocked")
        self.assertIn("market:btts", report.blocking_missing_data)
        self.assertLess(report.score, 100)

    def test_single_bookmaker_is_degrading_not_blocking(self):
        report = assess_betting_completeness(
            [snapshot("Paris SG"), snapshot("Draw"), snapshot("Marseille")],
            required_markets=("1x2",),
            decision_at="2026-08-14T12:00:00Z",
        )

        self.assertEqual(report.status, "degraded")
        self.assertIn("bookmaker_diversity", report.degrading_missing_data)
        self.assertNotIn("bookmaker_diversity", report.blocking_missing_data)

    def test_service_filters_store_snapshots_by_required_market(self):
        store = SimpleNamespace(list_snapshots=lambda event_id=None: complete_snapshots() + [snapshot(market="btts", selection="Yes")])
        report = betting_completeness_report(
            event_id="event-1",
            decision_at="2026-08-14T12:00:00Z",
            required_markets=("btts",),
            store=store,
        )

        self.assertEqual(report.available_markets, ("btts",))
        self.assertIn("selection_depth:btts", report.degrading_missing_data)

    def test_router_exposes_betting_completeness_endpoint(self):
        self.assertTrue(any(route.path.endswith("/completeness/betting") for route in router.routes))

    def test_betting_completeness_route_returns_warning(self):
        result = SimpleNamespace(
            score=95,
            status="complete",
            snapshot_count=6,
            decision_snapshot_count=6,
            closing_snapshot_count=6,
            bookmaker_count=2,
            available_markets=("1x2",),
            required_markets=("1x2",),
            missing_data=(),
            blocking_missing_data=(),
            degrading_missing_data=(),
        )
        with patch("app.routes_value.service.betting_completeness_report", return_value=result) as mocked:
            response = betting_completeness(
                event_id="event-1",
                decision_at="2026-08-14T12:00:00Z",
                required_markets="1x2,btts",
                user={"id": 1},
            )

        mocked.assert_called_once_with(
            event_id="event-1",
            decision_at="2026-08-14T12:00:00Z",
            required_markets=("1x2", "btts"),
        )
        self.assertEqual(response["score"], 95)
        self.assertIn("must not be used", response["warning"])


if __name__ == "__main__":
    unittest.main()