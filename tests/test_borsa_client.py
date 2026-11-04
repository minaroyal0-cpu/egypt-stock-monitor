import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.borsa_client import BorsaError, normalize_quote
from src.database import get_latest_quote, store_quote_snapshot


VALID = {
    "symbol":"COMI", "price":136.0, "currency":"EGP",
    "timestamp":"2026-11-03T12:00:00+02:00", "source":"Yahoo Finance (COMI.CA)",
    "api_symbol":"COMI.CA", "change":1.2, "change_percent":0.89, "volume":1000,
    "high":137.0, "low":134.0,
    "attribution":{"provider":"Yahoo Finance","url":"https://finance.yahoo.com"},
}


class BorsaQuoteTests(unittest.TestCase):
    def test_normalizes_quote_with_attribution(self):
        quote=normalize_quote(VALID,"COMI")
        self.assertEqual(quote["price"],136.0)
        self.assertEqual(quote["currency"],"EGP")
        self.assertEqual(quote["data_status"],"third_party")
        self.assertFalse(quote["historical_ohlcv_eligible"])
        self.assertEqual(quote["provider"],"Yahoo Finance")

    def test_rejects_symbol_mismatch(self):
        with self.assertRaises(BorsaError):
            normalize_quote(VALID,"ETEL")

    def test_rejects_missing_timezone(self):
        row=dict(VALID,timestamp="2026-11-03T12:00:00")
        with self.assertRaises(BorsaError):
            normalize_quote(row,"COMI")

    def test_rejects_non_positive_price(self):
        row=dict(VALID,price=0)
        with self.assertRaises(BorsaError):
            normalize_quote(row,"COMI")

    def test_rejects_non_egp_currency(self):
        row=dict(VALID,currency="USD")
        with self.assertRaises(BorsaError):
            normalize_quote(row,"COMI")

    def test_quote_snapshot_is_separate_and_idempotent(self):
        quote=normalize_quote(VALID,"COMI")
        with tempfile.TemporaryDirectory() as folder:
            db=str(Path(folder)/"egx.sqlite")
            self.assertEqual(store_quote_snapshot(db,quote)["inserted"],1)
            self.assertTrue(store_quote_snapshot(db,quote)["duplicate"])
            self.assertEqual(get_latest_quote(db,"COMI")["price"],136.0)


if __name__=="__main__":
    unittest.main()
