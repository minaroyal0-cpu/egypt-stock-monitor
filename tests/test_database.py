import csv
import tempfile
import unittest
from pathlib import Path
from src.database import store_records, get_best_financial, get_price_history, database_summary
from src.db_cli import import_csv

FIN_BASE = {"symbol":"ABUK","company":"Abu Qir","period":"2025","currency":"EGP","basis":"consolidated",
 "source":"third-party feed","source_url":"https://data.example/abuk","data_status":"third_party",
 "as_of":"2026-01-01","revenue":1000,"net_income":100}
PRICE = {"symbol":"ABUK","date":"2026-11-03","currency":"EGP","source":"vendor",
 "source_url":"https://data.example/prices","data_status":"third_party","as_of":"2026-11-03",
 "open":10,"high":12,"low":9,"close":11,"volume":1000,"ingested_at":"2026-11-04T00:00:00+00:00"}

class DatabaseTests(unittest.TestCase):
    def test_idempotent_append_and_source_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "history.sqlite3")
            official = dict(FIN_BASE, source="issuer filing", source_url="https://issuer.example/report",
                            data_status="official", as_of="2026-02-01", revenue=1200)
            first = store_records(db, "financial", [FIN_BASE, official])
            second = store_records(db, "financial", [FIN_BASE, official])
            self.assertEqual(first["inserted"], 2)
            self.assertEqual(second["inserted"], 0)
            best = get_best_financial(db, "ABUK", "2025", "consolidated")
            self.assertEqual(best["revenue"], 1200)
            self.assertEqual(best["data_status"], "official")
            self.assertEqual(database_summary(db)["financial_observations"], 2)

    def test_lower_priority_does_not_replace_official(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "history.sqlite3")
            official = dict(FIN_BASE, data_status="official", source="issuer", source_url="https://issuer.example")
            estimate = dict(FIN_BASE, data_status="estimate", source="estimate", source_url="https://estimate.example", revenue=9999)
            store_records(db, "financial", [official, estimate])
            self.assertEqual(get_best_financial(db, "ABUK", "2025", "consolidated")["revenue"], 1000)

    def test_price_history_keeps_one_best_row_per_day(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "history.sqlite3")
            official = dict(PRICE, data_status="official", source="EGX bulletin",
                            source_url="https://egx.example/prices", close=11.5)
            store_records(db, "prices", [PRICE, official])
            rows = get_price_history(db, "ABUK")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["close"], 11.5)

    def test_csv_import_tracks_valid_and_rejected_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "history.sqlite3")
            source = Path(folder) / "financial.csv"
            fields = list(FIN_BASE)
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(FIN_BASE)
                writer.writerow(dict(FIN_BASE, source_url=""))
            result = import_csv(db, str(source), "financial")
            self.assertEqual(result["accepted"], 1)
            self.assertEqual(len(result["rejected"]), 1)
            self.assertEqual(database_summary(db)["financial_observations"], 1)

if __name__ == "__main__":
    unittest.main()
