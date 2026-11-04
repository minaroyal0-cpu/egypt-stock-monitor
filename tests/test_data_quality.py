import unittest

from src.data_quality import assess_record_quality


FINANCIAL = {
    "symbol": "ABUK", "period": "2025-Q4", "basis": "consolidated",
    "currency": "EGP", "source": "issuer filing",
    "source_url": "https://example.org/report.pdf",
    "data_status": "official", "as_of": "2026-03-01",
}


class DataQualityScoringTests(unittest.TestCase):
    def test_recent_official_financial_record_is_analysis_ready(self):
        result = assess_record_quality(FINANCIAL, analysis_date="2026-03-10")
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["decision"], "analysis_ready")
        self.assertTrue(result["eligible_for_analysis"])

    def test_missing_analysis_date_never_claims_freshness(self):
        result = assess_record_quality(FINANCIAL)
        self.assertFalse(result["freshness_assessed"])
        self.assertEqual(result["decision"], "review_required")
        self.assertIn("freshness_not_assessed_supply_analysis_date", result["warnings"])

    def test_estimate_is_never_marked_as_actual_analysis_ready(self):
        row = dict(FINANCIAL, data_status="estimate")
        result = assess_record_quality(row, analysis_date="2026-03-10")
        self.assertEqual(result["decision"], "estimate_only")
        self.assertFalse(result["eligible_for_analysis"])

    def test_missing_provenance_blocks_analysis(self):
        row = dict(FINANCIAL, source_url="", source="")
        result = assess_record_quality(row, analysis_date="2026-03-10")
        self.assertEqual(result["decision"], "insufficient")
        self.assertFalse(result["eligible_for_analysis"])
        self.assertIn("source_url_missing_or_invalid", result["warnings"])

    def test_old_price_is_flagged_not_silently_treated_as_current(self):
        row = {
            "symbol": "ABUK", "date": "2025-01-01", "currency": "EGP",
            "source": "vendor", "source_url": "https://example.org/prices",
            "data_status": "third_party", "as_of": "2025-01-01",
        }
        result = assess_record_quality(row, "prices", analysis_date="2026-01-01")
        self.assertEqual(result["decision"], "review_required")
        self.assertIn("stale_data_exceeds_max_age", result["warnings"])

    def test_future_as_of_date_is_flagged(self):
        result = assess_record_quality(FINANCIAL, analysis_date="2026-02-01")
        self.assertEqual(result["decision"], "review_required")
        self.assertIn("as_of_date_is_in_the_future", result["warnings"])

    def test_invalid_analysis_date_and_age_limit_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_record_quality(FINANCIAL, analysis_date="not-a-date")
        with self.assertRaises(ValueError):
            assess_record_quality(FINANCIAL, analysis_date="2026-03-10", max_age_days=0)

    def test_currency_and_basis_are_required(self):
        row = dict(FINANCIAL, currency="", basis="")
        result = assess_record_quality(row, analysis_date="2026-03-10")
        self.assertEqual(result["decision"], "insufficient")
        self.assertIn("currency_missing_or_invalid", result["warnings"])
        self.assertIn("reporting_basis_missing", result["warnings"])


if __name__ == "__main__":
    unittest.main()
