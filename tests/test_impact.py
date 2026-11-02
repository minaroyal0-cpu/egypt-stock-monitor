import unittest

from src.impact import analyze_headline


class ImpactTests(unittest.TestCase):
    def test_portfolio_company_and_sector_match(self):
        result = analyze_headline("أبو قير للأسمدة تعلن زيادة صادرات الأسمدة", ["ABUK"])
        self.assertTrue(result["important"])
        self.assertEqual(result["symbols"], ["ABUK"])
        self.assertEqual(result["direction"], "غير محسوم من العنوان وحده")
        self.assertIn("قناة التأثير المحتملة", result["analysis"])

    def test_unrelated_headline_is_not_alerted(self):
        result = analyze_headline("افتتاح معرض فني في القاهرة", ["ABUK"])
        self.assertFalse(result["important"])

    def test_sector_news_without_company_name_is_not_direct_alert(self):
        result = analyze_headline("ارتفاع أسعار الأسمدة عالميًا", ["ABUK"])
        self.assertFalse(result["important"])

    def test_haln_fintech_link(self):
        result = analyze_headline("حالا توسع خدمات التكنولوجيا المالية", ["HALN"])
        self.assertTrue(result["important"])
        self.assertEqual(result["symbols"], ["HALN"])


if __name__ == "__main__":
    unittest.main()
