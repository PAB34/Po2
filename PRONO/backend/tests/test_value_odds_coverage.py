import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.routes_value import odds_coverage, router
from app.value.odds_coverage import build_odds_coverage_report
from app.value.service import odds_coverage_report
from app.value.snapshots import OddsSnapshot


def snapshot(event_id="event-1", market="1x2", selection="Paris SG", bookmaker="book-a", sport="football", competition="ligue1"):
    return OddsSnapshot(
        sport=sport,
        competition=competition,
        event_id=event_id,
        participant_1="Paris SG",
        participant_2="Marseille",
        market=market,
        selection=selection,
        bookmaker=bookmaker,
        odd=1.80,
        captured_at="2026-08-14T10:00:00Z",
        commence_time="2026-08-15T20:00:00Z",
        source="test",
        raw_payload_hash="hash",
    )


def snapshots():
    return [
        snapshot(selection="Paris SG", bookmaker="book-a"),
        snapshot(selection="Draw", bookmaker="book-a"),
        snapshot(selection="Marseille", bookmaker="book-a"),
        snapshot(selection="Paris SG", bookmaker="book-b"),
        snapshot(selection="Draw", bookmaker="book-b"),
        snapshot(selection="Marseille", bookmaker="book-b"),
        snapshot(event_id="event-2", selection="Paris SG", bookmaker="book-a"),
    ]


class OddsCoverageTests(unittest.TestCase):
    def test_coverage_groups_snapshots_by_event(self):
        report = build_odds_coverage_report(
            snapshots(),
            required_markets=("1x2",),
            decision_at="2026-08-14T12:00:00Z",
        )

        self.assertEqual(report.event_count, 2)
        self.assertEqual(report.snapshot_count, 7)
        first = report.events[0]
        self.assertEqual(first.bookmaker_count, 2)
        self.assertEqual(first.selections_by_market["1x2"], ("Draw", "Marseille", "Paris SG"))
        self.assertEqual(first.completeness.status, "complete")

    def test_missing_required_market_is_visible_per_event(self):
        report = build_odds_coverage_report(
            snapshots(),
            required_markets=("1x2", "btts"),
            decision_at="2026-08-14T12:00:00Z",
        )

        self.assertEqual(report.events[0].completeness.status, "blocked")
        self.assertIn("market:btts", report.events[0].completeness.blocking_missing_data)

    def test_service_filters_by_sport_and_competition(self):
        store = SimpleNamespace(list_snapshots=lambda event_id=None: snapshots() + [
            snapshot(event_id="tennis-1", sport="tennis", competition="atp", selection="Player A")
        ])

        report = odds_coverage_report(sport="tennis", competition="atp", store=store)

        self.assertEqual(report.event_count, 1)
        self.assertEqual(report.events[0].sport, "tennis")

    def test_router_exposes_odds_coverage_endpoint(self):
        self.assertTrue(any(route.path.endswith("/coverage/odds") for route in router.routes))

    def test_odds_coverage_route_serializes_events(self):
        completeness = SimpleNamespace(
            score=100,
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
        event = SimpleNamespace(
            event_id="event-1",
            sport="football",
            competition="ligue1",
            participant_1="Paris SG",
            participant_2="Marseille",
            commence_time="2026-08-15T20:00:00Z",
            snapshot_count=6,
            bookmaker_count=2,
            markets=("1x2",),
            selections_by_market={"1x2": ("Paris SG", "Draw", "Marseille")},
            bookmakers_by_market={"1x2": ("book-a", "book-b")},
            first_captured_at="2026-08-14T10:00:00Z",
            last_captured_at="2026-08-14T10:00:00Z",
            completeness=completeness,
        )
        result = SimpleNamespace(
            source="test",
            event_count=1,
            snapshot_count=6,
            required_markets=("1x2",),
            events=(event,),
        )
        with patch("app.routes_value.service.odds_coverage_report", return_value=result) as mocked:
            response = odds_coverage(
                event_id="event-1",
                sport="football",
                competition="ligue1",
                required_markets="1x2,btts",
                decision_at="2026-08-14T12:00:00Z",
                user={"id": 1},
            )

        mocked.assert_called_once_with(
            event_id="event-1",
            sport="football",
            competition="ligue1",
            required_markets=("1x2", "btts"),
            decision_at="2026-08-14T12:00:00Z",
        )
        self.assertEqual(response["event_count"], 1)
        self.assertEqual(response["events"][0]["bookmakers_by_market"]["1x2"], ["book-a", "book-b"])


if __name__ == "__main__":
    unittest.main()