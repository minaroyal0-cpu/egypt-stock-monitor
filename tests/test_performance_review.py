import math
import unittest

from pathlib import Path\nfrom tempfile import TemporaryDirectory\n\nfrom src.performance_review import (\n    percentage_return, review_event_window, review_event_window_from_csv,\n)


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

    def test_csv_review_uses_shared_dates_and_retains_sources(self):
        rows = [
            "symbol,date,close,source,source_url,data_status,as_of",
            "ABUK,2026-01-02,100,Issuer,https://issuer.example/prices,official,2026-01-02",
            "EGX30,2026-01-02,200,EGX,https://egx.example/prices,official,2026-01-02",
            "ABUK,2026-01-05,110,Issuer,https://issuer.example/prices,official,2026-01-05",
            "EGX30,2026-01-05,220,EGX,https://egx.example/prices,official,2026-01-05",
        ]
        with TemporaryDirectory() as folder:
            path = Path(folder) / "prices.csv"
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            result = review_event_window_from_csv(
                str(path), "ABUK", "2026-01-01", "2026-01-10"
            )
        self.assertEqual(result["actual_start_date"], "2026-01-02")
        self.assertEqual(result["actual_end_date"], "2026-01-05")
        self.assertEqual(result["stock_return_pct"], 10.0)
        self.assertEqual(result["benchmark_return_pct"], 10.0)
        self.assertEqual(result["stock_price_provenance_start"]["data_status"], "official")

    def test_csv_review_rejects_missing_provenance(self):
        rows = [
            "symbol,date,close,source,source_url,data_status,as_of",
            "ABUK,2026-01-02,100,,https://issuer.example,official,2026-01-02",
            "EGX30,2026-01-02,200,EGX,https://egx.example,official,2026-01-02",
            "ABUK,2026-01-05,110,Issuer,https://issuer.example,official,2026-01-05",
            "EGX30,2026-01-05,220,EGX,https://egx.example,official,2026-01-05",
        ]
        with TemporaryDirectory() as folder:
            path = Path(folder) / "prices.csv"
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                review_event_window_from_csv(str(path), "ABUK", "2026-01-01", "2026-01-10")

    def test_end_date_must_follow_event_date(self):
        with self.assertRaises(ValueError):
            review_event_window("ABUK", "2026-01-10", "2026-01-10", 10, 11, 20, 21)


if __name__ == "__main__":
    unittest.main()
