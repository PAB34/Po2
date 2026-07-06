import os
import tempfile
import time
import unittest
from unittest.mock import patch

import pandas as pd

from app.ligue1 import data as ligue1_data


TMP_ROOT = os.environ.get("PRONO_TEST_TMP", r"C:\tmp")
os.makedirs(TMP_ROOT, exist_ok=True)


class Ligue1DataCacheFallbackTests(unittest.TestCase):
    def _cached_history(self):
        return pd.DataFrame([
            {
                "Season": "2526",
                "Kickoff": pd.Timestamp("2026-05-16 21:00"),
                "HomeTeam": "Paris SG",
                "AwayTeam": "Marseille",
                "FTR": "H",
                "FTHG": 2,
                "FTAG": 1,
                "PSH": 1.8,
                "PSD": 3.7,
                "PSA": 4.2,
            }
        ])

    def test_load_history_uses_stale_cache_when_remote_download_fails(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as tmp:
            cache_path = os.path.join(tmp, "raw.pkl")
            self._cached_history().to_pickle(cache_path)
            old = time.time() - 72 * 3600
            os.utime(cache_path, (old, old))

            with patch.object(ligue1_data, "RAW_CACHE", cache_path), \
                 patch.object(ligue1_data, "SEASON_START_YEARS", [2025]), \
                 patch.object(ligue1_data, "_read", return_value=None):
                history = ligue1_data.load_history()

        self.assertEqual(len(history), 1)
        self.assertEqual(history.iloc[0]["HomeTeam"], "Paris SG")
        self.assertIn("PSH", history.columns)

    def test_load_history_returns_empty_frame_without_cache_or_remote_data(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as tmp:
            cache_path = os.path.join(tmp, "missing.pkl")
            with patch.object(ligue1_data, "RAW_CACHE", cache_path), \
                 patch.object(ligue1_data, "SEASON_START_YEARS", [2025]), \
                 patch.object(ligue1_data, "_read", return_value=None):
                history = ligue1_data.load_history()

        self.assertEqual(len(history), 0)
        self.assertTrue({"Season", "Kickoff", "HomeTeam", "AwayTeam"}.issubset(history.columns))

    def test_load_history_ignores_invalid_cache_without_crashing(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as tmp:
            cache_path = os.path.join(tmp, "raw.pkl")
            pd.DataFrame([{"bad": "cache"}]).to_pickle(cache_path)

            with patch.object(ligue1_data, "RAW_CACHE", cache_path), \
                 patch.object(ligue1_data, "_cache_fresh", return_value=True):
                history = ligue1_data.load_history()

        self.assertEqual(len(history), 0)
        self.assertTrue({"Season", "Kickoff", "HomeTeam", "AwayTeam"}.issubset(history.columns))


if __name__ == "__main__":
    unittest.main()

