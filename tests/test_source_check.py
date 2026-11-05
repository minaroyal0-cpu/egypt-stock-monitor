import unittest

from src.source_check import classify_source_url


class SourceCheckTests(unittest.TestCase):
    def test_exact_official_domain_is_classified(self):
        result = classify_source_url("https://www.egx.com.eg/en/News.aspx")
        self.assertEqual(result["source_class"], "نطاق مؤسسة رسمية مدرج")
        self.assertEqual(result["source_label"], "البورصة المصرية")

    def test_subdomain_is_allowed(self):
        result = classify_source_url("https://portal.fra.gov.eg/disclosures")
        self.assertEqual(result["source_class"], "نطاق مؤسسة رسمية مدرج")

    def test_lookalike_domain_is_not_official(self):
        result = classify_source_url("https://egx.com.eg.example.net/news")
        self.assertNotEqual(result["source_class"], "نطاق مؤسسة رسمية مدرج")

    def test_missing_url_is_unknown(self):
        result = classify_source_url("")
        self.assertEqual(result["source_class"], "غير معروف")

    def test_malformed_url_is_unknown(self):
        result = classify_source_url("http://[invalid")
        self.assertEqual(result["source_class"], "غير معروف")


if __name__ == "__main__":
    unittest.main()
