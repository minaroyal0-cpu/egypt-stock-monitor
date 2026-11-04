import csv
import tempfile
import unittest
from pathlib import Path
from src.ingestion import normalize_financial_row, normalize_price_row, ingest_csv

FIN = {"symbol":"ABUK","company":"Abu Qir","period":"2025-Q4","currency":"EGP","basis":"consolidated",
       "source":"issuer report","source_url":"https://example.org/report.pdf","data_status":"official",
       "as_of":"2026-03-01","revenue":"1000","net_income":"100"}
PRICE = {"symbol":"ABUK","date":"2026-11-03","currency":"EGP","source":"EGX bulletin",
         "source_url":"https://example.org/market.pdf","data_status":"official","as_of":"2026-11-03",
         "open":"10","high":"12","low":"9","close":"11","volume":"1000","turnover_egp":"11000"}

class IngestionTests(unittest.TestCase):
    def test_financial_normalization_preserves_provenance(self):
        row = normalize_financial_row(FIN)
        self.assertEqual(row["revenue"], 1000)
        self.assertEqual(row["data_status"], "official")
        self.assertEqual(row["period"], "2025-Q4")

    def test_rejects_missing_source_url(self):
        row = dict(FIN, source_url="")
        with self.assertRaises(ValueError):
            normalize_financial_row(row)

    def test_price_ohlc_validation(self):
        row = normalize_price_row(PRICE)
        self.assertEqual(row["close"], 11)
        with self.assertRaises(ValueError):
            normalize_price_row(dict(PRICE, high="10"))

    def test_same_symbol_date_in_different_currencies_is_not_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "prices.csv"
            output = Path(folder) / "prices.jsonl"
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(PRICE))
                writer.writeheader()
                writer.writerow(PRICE)
                writer.writerow(dict(PRICE, currency="USD"))
            result = ingest_csv(source, output, "prices")
            self.assertEqual(result["accepted"], 2)
            self.assertEqual(result["rejected"], [])

    def test_same_financial_period_in_different_currencies_is_not_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "financials.csv"
            output = Path(folder) / "financials.jsonl"
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(FIN))
                writer.writeheader()
                writer.writerow(FIN)
                writer.writerow(dict(FIN, currency="USD"))
            result = ingest_csv(source, output, "financial")
            self.assertEqual(result["accepted"], 2)
            self.assertEqual(result["rejected"], [])

    def test_csv_ingestion_reports_rejected_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.csv"
            output = Path(folder) / "out.jsonl"
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(FIN))
                writer.writeheader()
                writer.writerow(FIN)
                writer.writerow(dict(FIN, source_url=""))
            result = ingest_csv(source, output, "financial")
            self.assertEqual(result["accepted"], 1)
            self.assertEqual(len(result["rejected"]), 1)
            self.assertTrue(output.exists())

if __name__ == "__main__":
    unittest.main()
