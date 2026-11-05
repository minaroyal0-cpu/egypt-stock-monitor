import unittest

from src.audit_log import append_bounded, make_audit_record


class AuditLogTests(unittest.TestCase):
    def test_record_keeps_decision_context_without_claiming_price_impact(self):
        item = {"title": "خبر", "link": "https://example.com/a", "source": "Publisher"}
        impact = {
            "important": True, "symbols": ["ABUK"], "match_type": "مباشر",
            "review_priority": "أولوية مرتفعة", "review_score": 75,
            "score_reasons": ["حدث مؤسسي محتمل (+40)"], "headline_tone": "محايدة/غير واضحة",
        }
        source = {"source_class": "غير معروف", "source_domain": "example.com"}
        record = make_audit_record(item, impact, source, True)
        self.assertEqual(record["symbols"], ["ABUK"])
        self.assertTrue(record["alerted"])
        self.assertIn("ليس قياسًا للعائد", record["assessment_type"])

    def test_append_keeps_only_newest_records(self):
        result = append_bounded([{"n": 1}, {"n": 2}], {"n": 3}, limit=2)
        self.assertEqual(result, [{"n": 2}, {"n": 3}])

    def test_limit_is_at_least_one(self):
        self.assertEqual(append_bounded([], {"n": 1}, limit=0), [{"n": 1}])


if __name__ == "__main__":
    unittest.main()
