import unittest

from app.value.boost import BoostSchedule, WINAMAX_LIKE_SCHEDULE


class BoostScheduleTests(unittest.TestCase):
    def test_winamax_like_schedule_depends_on_selection_count(self):
        self.assertAlmostEqual(WINAMAX_LIKE_SCHEDULE.rate_for(2), 0.02, places=6)
        self.assertAlmostEqual(WINAMAX_LIKE_SCHEDULE.rate_for(5), 0.15, places=6)
        self.assertAlmostEqual(WINAMAX_LIKE_SCHEDULE.rate_for(10), 0.40, places=6)

    def test_schedule_uses_lower_eligible_count_when_gap_exists(self):
        schedule = BoostSchedule(name="custom", rates_by_selection_count={3: 0.05, 5: 0.12}, max_selection_count=6)
        self.assertAlmostEqual(schedule.rate_for(4), 0.05, places=6)
        self.assertAlmostEqual(schedule.rate_for(6), 0.12, places=6)

    def test_schedule_rejects_above_limit(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            WINAMAX_LIKE_SCHEDULE.rate_for(11)

    def test_schedule_returns_zero_when_not_eligible_yet(self):
        schedule = BoostSchedule(name="custom", rates_by_selection_count={3: 0.05}, max_selection_count=10)
        self.assertEqual(schedule.rate_for(2), 0.0)


if __name__ == "__main__":
    unittest.main()
