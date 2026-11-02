import unittest

from src.impact import analyze_headline


class ImpactTests(unittest.TestCase):
    def test_direct_company_and_event_match(self):
        result = analyze_headline("أبو قير للأسمدة تعلن نتائج الأعمال السنوية", ["ABUK"])
        self.assertTrue(result["important"])
        self.assertEqual(result["symbols"], ["ABUK"])
        self.assertEqual(result["match_type"], "مباشر")
        self.assertEqual(result["direction"], "غير محسوم من العنوان وحده")

    def test_macro_sector_news_maps_to_portfolio_indirectly(self):
        result = analyze_headline("البنك المركزي يعلن خفض سعر الفائدة", ["BQDC", "TMGH"])
        self.assertTrue(result["important"])
        self.assertEqual(set(result["symbols"]), {"BQDC", "TMGH"})
        self.assertEqual(result["match_type"], "قطاعي غير مباشر")

    def test_unrelated_headline_is_not_alerted(self):
        result = analyze_headline("افتتاح معرض فني في القاهرة", ["ABUK"])
        self.assertFalse(result["important"])

    def test_sector_news_without_company_name_can_be_watch_item(self):
        result = analyze_headline("ارتفاع أسعار الأسمدة عالميًا", ["ABUK"])
        self.assertTrue(result["important"])
        self.assertEqual(result["match_type"], "قطاعي غير مباشر")

    def test_haln_fintech_link(self):
        result = analyze_headline("حالا توسع خدمات التكنولوجيا المالية", ["HALN"])
        self.assertTrue(result["important"])
        self.assertEqual(result["symbols"], ["HALN"])
        self.assertEqual(result["match_type"], "مباشر")

    def test_tone_is_not_stock_direction(self):
        result = analyze_headline("فوري تعلن زيادة الإيرادات", ["FWRY"])
        self.assertEqual(result["headline_tone"], "إيجابية لغويًا فقط")
        self.assertEqual(result["direction"], "غير محسوم من العنوان وحده")

    def test_invalid_symbol_is_ignored(self):
        result = analyze_headline("خبر عن بنك القاهرة", ["NOT_A_REAL_SYMBOL"])
        self.assertFalse(result["important"])


if __name__ == "__main__":
    unittest.main()
