import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from src.event_study import (
    event_study_from_csv,
    load_shared_price_series,
    market_model_event_study,
)


def synthetic_series(count=35, event_index=25):
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(count)]
    market = [100.0]
    stock = [80.0]
    market_returns = [0.0]
    for i in range(1, count):
        market_return = ((i % 7) - 3) * 0.3
        market_returns.append(market_return)
        market.append(market[-1] * (1 + market_return / 100))
        stock_return = 0.4 + 1.2 * market_return
        if i == event_index:
            stock_return += 2.0
        stock.append(stock[-1] * (1 + stock_return / 100))
    return dates, stock, market


class EventStudyTests(unittest.TestCase):
    def test_market_model_detects_injected_abnormal_return(self):
        dates, stock, market = synthetic_series()
        result = market_model_event_study(
            dates, stock, market, dates[25],
            estimation_window=20, event_window_start=0, event_window_end=1,
            symbol="abuk",
        )
        self.assertEqual(result["symbol"], "ABUK")
        self.assertEqual(result["estimation_observations"], 20)
        self.assertAlmostEqual(result["market_model_beta"], 1.2, places=6)
        self.assertAlmostEqual(
            result["abnormal_returns"][0]["abnormal_return_pct_points"], 2.0, places=5
        )
        self.assertAlmostEqual(
            result["cumulative_abnormal_return_pct_points"],
            sum(x["abnormal_return_pct_points"] for x in result["abnormal_returns"]),
            places=6,
        )

    def test_rejects_insufficient_estimation_window(self):
        dates, stock, market = synthetic_series()
        with self.assertRaisesRegex(ValueError, "insufficient_pre_event"):
            market_model_event_study(
                dates, stock, market, dates[10], estimation_window=20
            )

    def test_rejects_misaligned_or_unsorted_data(self):
        dates, stock, market = synthetic_series()
        with self.assertRaisesRegex(ValueError, "equal_lengths"):
            market_model_event_study(dates, stock[:-1], market, dates[25])
        bad_dates = dates[:]
        bad_dates[2], bad_dates[3] = bad_dates[3], bad_dates[2]
        with self.assertRaisesRegex(ValueError, "unique_and_ascending"):
            market_model_event_study(bad_dates, stock, market, dates[25])

    def test_rejects_zero_variance_benchmark_returns(self):
        dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(8)]
        market = [100.0] * 8
        stock = [100.0 + i for i in range(8)]
        with self.assertRaisesRegex(ValueError, "zero_variance"):
            market_model_event_study(
                dates, stock, market, dates[5], estimation_window=3,
                event_window_start=0, event_window_end=0,
            )

    def test_csv_loader_requires_source_metadata_and_shared_dates(self):
        rows = [
            ["symbol", "date", "close", "source", "source_url", "data_status", "as_of"],
            ["ABUK", "2026-01-01", "100", "Issuer", "https://issuer.example/data", "official", "2026-01-01"],
            ["EGX30", "2026-01-01", "200", "EGX", "https://egx.example/data", "official", "2026-01-01"],
            ["ABUK", "2026-01-02", "101", "Issuer", "https://issuer.example/data", "official", "2026-01-02"],
            ["EGX30", "2026-01-02", "201", "EGX", "https://egx.example/data", "official", "2026-01-02"],
            ["ABUK", "2026-01-03", "102", "Issuer", "https://issuer.example/data", "official", "2026-01-03"],
            ["EGX30", "2026-01-03", "202", "EGX", "https://egx.example/data", "official", "2026-01-03"],
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prices.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(rows)
            loaded = load_shared_price_series(str(path), "ABUK")
        self.assertEqual(loaded["dates"], ["2026-01-01", "2026-01-02", "2026-01-03"])
        self.assertTrue(
            loaded["provenance"]["ABUK"]["2026-01-01"]
            ["status_is_source_assertion_not_independent_verification"]
        )

    def test_csv_wrapper_runs_complete_analysis(self):
        dates, stock, market = synthetic_series(count=35, event_index=25)
        rows = [["symbol", "date", "close", "source", "source_url", "data_status", "as_of"]]
        for day, s, m in zip(dates, stock, market):
            rows.append(["ABUK", day, s, "Issuer", "https://issuer.example/data", "official", day])
            rows.append(["EGX30", day, m, "EGX", "https://egx.example/data", "official", day])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prices.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(rows)
            result = event_study_from_csv(
                str(path), "ABUK", dates[25], estimation_window=20,
                event_window_start=0, event_window_end=1,
            )
        self.assertEqual(result["event_date"], dates[25])
        self.assertEqual(result["price_data_provenance"]["ABUK"]["shared_observations"], 35)


if __name__ == "__main__":
    unittest.main()
