import math
import unittest

from src.performance_review import percentage_return, review_event_window


class PerformanceReviewTests(unittest.TestCase):
    def test_percentage_return(self):
        self.assertAlmostEqual(percentage_return(100, 110), 10.0)

    def test_rejects_non_positive_and_non_finite_prices(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                percentage_return(value, 110)

    def test_relative_return_uses_same_window_benchmark(self):
        result = review_event_window(
            "abuk", "2026-01-01", "2026-01-10",
            100, 108, 200, 204,
        )
        self.assertEqual(result["symbol"], "ABUK")
        self.assertEqual(result["benchmark_symbol"], "EGX30")
        self.assertEqual(result["stock_return_pct"], 8.0)
        self.assertEqual(result["benchmark_return_pct"], 2.0)
        self.assertEqual(result["relative_return_pct_points"], 6.0)
        self.assertEqual(result["window_calendar_days"], 9)
        self.assertTrue(result["source_prices_required"])
        self.assertIn("لا يثبت", result["interpretation"])

    def test_requires_symbol_and_valid_dates(self):
        with self.assertRaises(ValueError):
            review_event_window("", "2026-01-01", "2026-01-10", 10, 11, 20, 21)
        with self.assertRaises(ValueError):
            review_event_window("ABUK", "01-01-2026", "2026-01-10", 10, 11, 20, 21)

    def test_end_date_must_follow_event_date(self):
        with self.assertRaises(ValueError):
            review_event_window("ABUK", "2026-01-10", "2026-01-10", 10, 11, 20, 21)


if __name__ == "__main__":
    unittest.main()
