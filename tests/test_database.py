import csv
import tempfile
import unittest
from pathlib import Path
from src.database import (store_records, get_best_financial, get_price_history,
    get_adjusted_price_history, database_summary)
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

    def test_financial_lookup_requires_currency_if_ambiguous(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "history.sqlite3")
            usd = dict(FIN_BASE, currency="USD")
            store_records(db, "financial", [FIN_BASE, usd])
            with self.assertRaisesRegex(ValueError, "currency_required"):
                get_best_financial(db, "ABUK", "2025", "consolidated")
            self.assertEqual(get_best_financial(db, "ABUK", "2025", "consolidated", "USD")["currency"], "USD")

    def test_price_history_keeps_one_best_row_per_day_and_currency(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "history.sqlite3")
            official = dict(PRICE, data_status="official", source="EGX bulletin",
                            source_url="https://egx.example/prices", close=11.5)
            usd = dict(PRICE, currency="USD", close=10.5)
            store_records(db, "prices", [PRICE, official, usd])
            rows = get_price_history(db, "ABUK")
            self.assertEqual(len(rows), 2)
            egp = next(row for row in rows if row["currency"]=="EGP")
            self.assertEqual(egp["close"], 11.5)

    def test_adjusted_close_is_created_and_future_actions_are_capped_at_as_of(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "history.sqlite3")
            store_records(db, "prices", [PRICE])
            action = {"symbol":"ABUK","ex_date":"2026-11-05","currency":"EGP",
                "action_type":"split","new_shares_per_old_share":2,"source":"issuer",
                "source_url":"https://issuer.example/action","data_status":"official",
                "as_of":"2026-11-04"}
            store_records(db, "actions", [action])
            before_event = get_adjusted_price_history(db,"ABUK",end_date="2026-11-04",currency="EGP")
            after_event = get_adjusted_price_history(db,"ABUK",end_date="2026-11-06",currency="EGP")
            self.assertEqual(before_event[0]["adjusted_close"],11)
            self.assertEqual(after_event[0]["adjusted_close"],5.5)

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
