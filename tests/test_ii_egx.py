import unittest

from src.ii_egx.fundamentals import analyze_row
from src.ii_egx.liquidity import classify_liquidity


class LiquidityTests(unittest.TestCase):
    def test_classification_and_order(self):
        data = {
            "HIGH": [{"date": f"2026-10-{i:02d}", "name": "High", "sector": "X",
                      "turnover_egp": 6_000_000, "volume": 100,
                      "turnover_basis": "reported_value_egp"} for i in range(1, 6)],
            "LOW": [{"date": f"2026-10-{i:02d}", "name": "Low", "sector": "Y",
                     "turnover_egp": 10_000, "volume": 1,
                     "turnover_basis": "estimated_close_times_volume"} for i in range(1, 6)],
        }
        result = classify_liquidity(data)
        self.assertEqual(result[0]["symbol"], "HIGH")
        self.assertEqual(result[0]["liquidity_band"], "مرتفع")
        self.assertEqual(result[1]["liquidity_band"], "ضعيف")


class FundamentalTests(unittest.TestCase):
    def test_ratios_and_provenance(self):
        row = {
            "symbol": "TEST", "as_of": "2026-Q3", "source_name": "Test source",
            "source_url": "https://example.com", "revenue": "1000",
            "operating_profit": "200", "net_income": "100",
            "total_assets": "2000", "total_equity": "500", "total_debt": "250",
            "cash": "50", "current_assets": "400", "current_liabilities": "200",
            "operating_cash_flow": "150", "capex": "40",
        }
        result = analyze_row(row)
        self.assertEqual(result["operating_margin"], 0.2)
        self.assertEqual(result["roe"], 0.2)
        self.assertEqual(result["free_cash_flow_egp"], 110)
        self.assertTrue(result["source_url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
