import unittest
from datetime import date, timedelta

from src.decision_engine import analyze_investment_case


class DecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.financial = {
            "symbol": "TEST", "company": "Test Co", "period": "2025-Q4",
            "basis": "consolidated", "currency": "EGP", "source": "issuer filing",
            "source_url": "https://example.org/report.pdf", "data_status": "official",
            "as_of": "2026-11-01", "revenue": 200, "gross_profit": 80,
            "operating_profit": 40, "net_income": 20, "total_assets": 100,
            "total_equity": 50, "total_debt": 20, "prior_revenue": 180,
            "operating_cash_flow": 25, "capital_expenditure": 5,
            "eps": 2, "book_value_per_share": 10,
        }
        self.bars = []
        start = date(2026, 9, 26)
        for i in range(40):
            day = (start + timedelta(days=i)).isoformat()
            close = 10 + i * 0.1
            self.bars.append({
                "symbol": "TEST", "date": day, "open": close, "high": close + 0.2,
                "low": close - 0.2, "close": close, "adjusted_close": close,
                "currency": "EGP", "source": "test-provider",
                "source_url": "https://example.org/prices",
                "data_status": "official", "as_of": day,
            })

    def test_quality_gates_valid_case(self):
        result = analyze_investment_case(self.financial, self.bars, "2026-11-04",
                                         {"pe": 10, "pb": 2})
        self.assertNotEqual(result["classification"], "insufficient_data")
        self.assertIsNotNone(result["composite_score"])
        self.assertFalse(result["score_is_probability"])

    def test_stale_price_blocks_composite(self):
        bars = [dict(row) for row in self.bars]
        bars[-1]["as_of"] = "2026-10-01"
        result = analyze_investment_case(self.financial, bars, "2026-11-04")
        self.assertEqual(result["classification"], "insufficient_data")
        self.assertIsNone(result["composite_score"])
        self.assertTrue(result["blockers"])

    def test_missing_analysis_date_rejected(self):
        with self.assertRaises(ValueError):
            analyze_investment_case(self.financial, self.bars, None)

    def test_requires_minimum_history(self):
        with self.assertRaises(ValueError):
            analyze_investment_case(self.financial, self.bars[:10], "2026-11-04")

    def test_future_price_bar_rejected(self):
        bars = [dict(row) for row in self.bars]
        bars[-1]["date"] = "2026-11-05"
        with self.assertRaises(ValueError):
            analyze_investment_case(self.financial, bars, "2026-11-04")

    def test_mixed_currencies_rejected(self):
        bars = [dict(row) for row in self.bars]
        bars[-1]["currency"] = "USD"
        with self.assertRaises(ValueError):
            analyze_investment_case(self.financial, bars, "2026-11-04")

    def test_missing_provenance_blocks_score(self):
        financial = dict(self.financial)
        financial.pop("source_url")
        result = analyze_investment_case(financial, self.bars, "2026-11-04")
        self.assertEqual(result["classification"], "insufficient_data")
        self.assertIsNone(result["composite_score"])


if __name__ == "__main__":
    unittest.main()
