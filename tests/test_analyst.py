import unittest
from src.data_quality import validate_financial_record, compare_periods
from src.financial_analysis import analyze_fundamentals
from src.valuation import dcf_value_per_share, multiple_valuation
from src.technical import sma, rsi, macd
from src.report import build_report

class AnalystTests(unittest.TestCase):
    def test_fundamentals(self):
        row = {"revenue": 200, "gross_profit": 80, "operating_profit": 40, "net_income": 20,
               "total_assets": 100, "total_equity": 50, "prior_revenue": 100,
               "operating_cash_flow": 25, "capital_expenditure": 5, "source": "test",
               "period": "2025-Q4", "currency": "EGP"}
        result = analyze_fundamentals(row)
        self.assertAlmostEqual(result["revenue_growth"], 1.0)
        self.assertAlmostEqual(result["gross_margin"], 0.4)
        self.assertAlmostEqual(result["free_cash_flow"], 20)
    def test_missing_required_field_fails(self):
        with self.assertRaises(ValueError):
            analyze_fundamentals({"revenue": 10})
    def test_quality_provenance(self):
        row = {"company":"ABC","period":"2025-12-31","currency":"EGP","source":"EGX",
               "source_url":"https://example.com","revenue":10,"net_income":2,"data_status":"official"}
        self.assertTrue(validate_financial_record(row)["valid"])
    def test_currency_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            compare_periods({"currency":"EGP"},{"currency":"USD"})
    def test_valuation(self):
        self.assertEqual(multiple_valuation(10, earnings_per_share=2)["pe"], 5)
        self.assertGreater(dcf_value_per_share(100, .15, .03, 10)["value_per_share"], 0)
    def test_technical(self):
        self.assertEqual(sma([1,2,3],2), [None,1.5,2.5])
        self.assertEqual(len(rsi(list(range(20)))), 20)
        self.assertEqual(len(macd(list(range(40)))["histogram"]), 40)
    def test_report_warns_about_missing_data(self):
        report = build_report("TEST")
        self.assertIn("not supplied", report)
        self.assertIn("not a buy/sell", report)
        self.assertIn("Historical risk diagnostics", report)
        self.assertIn("Not calculated", report)

if __name__ == "__main__":
    unittest.main()
