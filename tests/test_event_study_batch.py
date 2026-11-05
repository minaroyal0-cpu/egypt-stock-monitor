import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from src.event_study_batch import run_batch


class EventStudyBatchTests(unittest.TestCase):
    def _write_inputs(self, folder: str):
        dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(36)]
        market = [100.0]
        stock = [80.0]
        for i in range(1, len(dates)):
            market_return = ((i % 7) - 3) * 0.3
            market.append(market[-1] * (1 + market_return / 100))
            stock_return = 0.4 + 1.2 * market_return
            if i == 25:
                stock_return += 2
            stock.append(stock[-1] * (1 + stock_return / 100))

        prices_path = Path(folder) / "prices.csv"
        with prices_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["symbol", "date", "close", "source", "source_url", "data_status", "as_of"])
            for day, stock_close, market_close in zip(dates, stock, market):
                writer.writerow(["ABUK", day, stock_close, "Issuer", "https://issuer.example/prices", "official", day])
                writer.writerow(["EGX30", day, market_close, "EGX", "https://egx.example/prices", "official", day])

        events_path = Path(folder) / "events.csv"
        with events_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["event_id", "symbol", "event_date", "estimation_window", "event_window_start", "event_window_end"])
            writer.writerow(["news-001", "ABUK", dates[25], "20", "0", "1"])
            writer.writerow(["news-002", "ABUK", dates[10], "20", "0", "0"])
            writer.writerow(["news-001", "ABUK", dates[25], "20", "0", "0"])
        return str(events_path), str(prices_path), dates

    def test_batch_returns_results_and_isolates_bad_event_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            events, prices, dates = self._write_inputs(folder)
            results = run_batch(events, prices)
        self.assertEqual([item["status"] for item in results], ["ok", "error", "error"])
        self.assertEqual(results[0]["event_id"], "news-001")
        self.assertEqual(results[0]["event_date"], dates[25])
        self.assertEqual(results[1]["error"], "insufficient_pre_event_estimation_observations")
        self.assertEqual(results[2]["error"], "duplicate_event_id")

    def test_requires_event_register_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            events = Path(folder) / "events.csv"
            prices = Path(folder) / "prices.csv"
            events.write_text("symbol,event_date\nABUK,2026-01-01\n", encoding="utf-8")
            prices.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing_required_event_columns"):
                run_batch(str(events), str(prices))


if __name__ == "__main__":
    unittest.main()
