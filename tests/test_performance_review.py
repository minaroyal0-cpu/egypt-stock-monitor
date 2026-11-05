import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.performance_review import (
    percentage_return,
    review_event_window,
    review_event_window_from_csv,
)


class PerformanceReviewTests(unittest.TestCase):
    def _write_csv(self, folder, rows):
        path = Path(folder) / "prices.csv"
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return str(path)

    def test_percentage_return(self):
        self.assertAlmostEqual(percentage_return(100, 110), 10.0)

    def test_rejects_non_positive_non_finite_and_non_numeric_prices(self):
        for value in (0, -1, float("nan"), float("inf"), "bad", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                percentage_return(value, 110)

    def test_relative_return_uses_same_window_benchmark(self):
        result = review_event_window(
            "abuk", "2026-01-01", "2026-01-10", 100, 108, 200, 204
        )
        self.assertEqual(result["symbol"], "ABUK")
        self.assertEqual(result["benchmark_symbol"], "EGX30")
        self.assertEqual(result["stock_return_pct"], 8.0)
        self.assertEqual(result["benchmark_return_pct"], 2.0)
        self.assertEqual(result["relative_return_pct_points"], 6.0)
        self.assertEqual(result["window_calendar_days"], 9)
        self.assertTrue(result["source_prices_required"])
        self.assertIn("لا يثبت", result["interpretation"])

    def test_rejects_missing_symbol_and_invalid_dates(self):
        with self.assertRaises(ValueError):
            review_event_window("", "2026-01-01", "2026-01-10", 10, 11, 20, 21)
        with self.assertRaises(ValueError):
            review_event_window("ABUK", "01-01-2026", "2026-01-10", 10, 11, 20, 21)

    def test_end_date_must_follow_event_date(self):
        with self.assertRaises(ValueError):
            review_event_window("ABUK", "2026-01-10", "2026-01-10", 10, 11, 20, 21)

    def test_csv_review_uses_shared_dates_and_retains_sources(self):
        rows = [
            "symbol,date,close,source,source_url,data_status,as_of",
            "ABUK,2026-01-02,100,Issuer,https://issuer.example/prices,official,2026-01-02",
            "EGX30,2026-01-02,200,EGX,https://egx.example/prices,official,2026-01-02",
            "ABUK,2026-01-05,110,Issuer,https://issuer.example/prices,official,2026-01-05",
            "EGX30,2026-01-05,220,EGX,https://egx.example/prices,official,2026-01-05",
        ]
        with TemporaryDirectory() as folder:
            result = review_event_window_from_csv(
                self._write_csv(folder, rows), "ABUK", "2026-01-01", "2026-01-10"
            )
        self.assertEqual(result["actual_start_date"], "2026-01-02")
        self.assertEqual(result["actual_end_date"], "2026-01-05")
        self.assertEqual(result["stock_return_pct"], 10.0)
        self.assertEqual(result["benchmark_return_pct"], 10.0)
        self.assertTrue(result["stock_price_provenance_start"]["status_is_source_assertion_not_independent_verification"])

    def test_csv_review_rejects_missing_provenance(self):
        rows = [
            "symbol,date,close,source,source_url,data_status,as_of",
            "ABUK,2026-01-02,100,,https://issuer.example,official,2026-01-02",
            "EGX30,2026-01-02,200,EGX,https://egx.example,official,2026-01-02",
            "ABUK,2026-01-05,110,Issuer,https://issuer.example,official,2026-01-05",
            "EGX30,2026-01-05,220,EGX,https://egx.example,official,2026-01-05",
        ]
        with TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                review_event_window_from_csv(
                    self._write_csv(folder, rows), "ABUK", "2026-01-01", "2026-01-10"
                )

    def test_csv_review_rejects_duplicate_instrument_date(self):
        rows = [
            "symbol,date,close,source,source_url,data_status,as_of",
            "ABUK,2026-01-02,100,Issuer,https://issuer.example,official,2026-01-02",
            "ABUK,2026-01-02,101,Issuer,https://issuer.example,official,2026-01-02",
        ]
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "duplicate_price"):
                review_event_window_from_csv(
                    self._write_csv(folder, rows), "ABUK", "2026-01-01", "2026-01-10"
                )

    def test_csv_rejects_non_https_and_malformed_source_urls(self):
        for url in ("http://issuer.example/prices", "https://"):
            rows = [
                "symbol,date,close,source,source_url,data_status,as_of",
                f"ABUK,2026-01-02,100,Issuer,{url},official,2026-01-02",
            ]
            with TemporaryDirectory() as folder:
                with self.subTest(url=url), self.assertRaisesRegex(ValueError, "invalid_source_url"):
                    review_event_window_from_csv(
                        self._write_csv(folder, rows), "ABUK", "2026-01-01", "2026-01-10"
                    )


if __name__ == "__main__":
    unittest.main()
