import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import tennis_atp_elo
from app.tennis_coach import norm


class FakeCoach:
    def __init__(self, dataset_dir: Path):
        self.dataset_dir = dataset_dir
        self.stats = {"ATP": {}, "WTA": {}}
        self._stats_exact = {"ATP": {}, "WTA": {}}
        self._ambiguous_stats_keys = {"ATP": set(), "WTA": set()}


class TennisAtpEloTests(unittest.TestCase):
    def _csv(self, path: Path, rows: list[str]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "tourney_date,match_num,winner_name,loser_name,surface\n" + "\n".join(rows) + "\n",
            encoding="utf-8",
        )
        return path

    def test_rebuild_injects_global_and_surface_elo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = self._csv(
                root / "tml" / "2026.csv",
                [
                    "20260101,1,Alice Alpha,Bob Beta,Hard",
                    "20260102,2,Alice Alpha,Carla Gamma,Clay",
                    "20260103,3,Bob Beta,Carla Gamma,Hard",
                ],
            )
            coach = FakeCoach(root)

            summary = tennis_atp_elo.rebuild_atp_elo(coach, [history], source="test")

            alice = coach._stats_exact["ATP"][norm("Alice Alpha")]
            bob = coach._stats_exact["ATP"][norm("Bob Beta")]
            carla = coach._stats_exact["ATP"][norm("Carla Gamma")]
            self.assertEqual(summary["status"], "ok")
            self.assertEqual(summary["matches"], 3)
            self.assertEqual(summary["latest_date"], "2026-01-03")
            self.assertGreater(alice["elo_global"], 1500)
            self.assertGreater(alice["elo_hard"], bob["elo_hard"])
            self.assertGreater(alice["elo_clay"], carla["elo_clay"])
            self.assertEqual(alice["elo_source"], "test")
            self.assertIs(coach.stats["ATP"][norm("Alice Alpha")], alice)

    def test_history_paths_replaces_packaged_current_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = self._csv(root / "tml" / "2025.csv", ["20250101,1,A,B,Hard"])
            packaged = self._csv(root / "tml" / "2026.csv", ["20260101,1,A,B,Hard"])
            live = self._csv(root / "runtime" / "2026.csv", ["20260730,1,C,D,Hard"])

            paths = tennis_atp_elo.history_paths(root, live, year=2026)

            self.assertIn(old, paths)
            self.assertIn(live, paths)
            self.assertNotIn(packaged, paths)

    def test_current_year_file_stays_offline_without_runtime_data_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packaged = self._csv(root / "tml" / "2026.csv", ["20260101,1,A,B,Hard"])
            with patch.dict(os.environ, {"PRONO_DATA_DIR": ""}, clear=False), patch.object(
                tennis_atp_elo, "_download_live_year", side_effect=AssertionError("network should not be used")
            ):
                selected, source = tennis_atp_elo.current_year_file(root, year=2026, now=1_800_000_000)

            self.assertEqual(selected, packaged)
            self.assertEqual(source, "TennisMyLife embarque")

    def test_refresh_is_cached_for_24_hours(self):
        with tempfile.TemporaryDirectory() as tmp:
            coach = FakeCoach(Path(tmp))
            coach._atp_elo_refreshed_at = 1000.0
            coach._atp_elo_refresh_summary = {"status": "ok", "source": "cached"}
            with patch.object(tennis_atp_elo, "current_year_file", side_effect=AssertionError("must not refresh")):
                summary = tennis_atp_elo.refresh_coach_if_needed(coach, now=1000.0 + 3600)
            self.assertEqual(summary["source"], "cached")


if __name__ == "__main__":
    unittest.main()
