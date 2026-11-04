import unittest

from src.source_registry import (
    classify_source_url,
    get_source,
    list_sources,
    readiness_report,
)


class SourceRegistryTests(unittest.TestCase):
    def test_registry_contains_primary_egyptian_sources(self):
        ids = {item["source_id"] for item in list_sources()}
        self.assertTrue({"egx", "fra", "egid"}.issubset(ids))

    def test_egid_is_not_misrepresented_as_connected(self):
        egid = get_source("egid")
        self.assertEqual(egid["automation_status"], "not_connected")
        self.assertEqual(egid["access_status"], "documented_api_access_unverified")

    def test_registered_host_is_classified_without_claiming_document_verification(self):
        result = classify_source_url("https://beta.egx.com.eg/en/news")
        self.assertTrue(result["registered"])
        self.assertEqual(result["source_id"], "egx")
        self.assertFalse(result["verified_document"])

    def test_unregistered_and_http_urls_are_not_trusted(self):
        self.assertFalse(classify_source_url("https://example.com/report")["registered"])
        self.assertEqual(
            classify_source_url("http://fra.gov.eg/report")["reason"],
            "https_url_required",
        )

    def test_readiness_does_not_claim_live_data(self):
        report = readiness_report()
        self.assertFalse(report["live_data_connected"])
        self.assertFalse(report["automatic_disclosure_ingestion"])
        self.assertGreaterEqual(len(report["next_requirements"]), 4)

    def test_unknown_source_raises(self):
        with self.assertRaises(KeyError):
            get_source("not-a-source")


if __name__ == "__main__":
    unittest.main()
