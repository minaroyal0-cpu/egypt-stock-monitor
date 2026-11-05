import csv
import tempfile
import unittest
from pathlib import Path

from src.event_inbox import append_candidates, FIELDS


class EventInboxTests(unittest.TestCase):
    def test_appends_new_urls_once_and_leaves_mapping_unverified(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "event_inbox.csv"
            items = [
                {"title": "Company disclosure", "link": "https://news.example/1",
                 "published": "Mon, 02 Nov 2026 10:00:00 GMT", "source": "Publisher"},
                {"title": "Company disclosure", "link": "https://news.example/1",
                 "published": "Mon, 02 Nov 2026 10:00:00 GMT", "source": "Publisher"},
            ]
            self.assertEqual(append_candidates(path, items), 1)
            self.assertEqual(append_candidates(path, items), 0)
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(list(rows[0]), FIELDS)
        self.assertEqual(rows[0]["review_status"], "needs_review")
        self.assertEqual(rows[0]["verified_symbol"], "")
        self.assertEqual(rows[0]["verified_event_date"], "")

    def test_rejects_incompatible_existing_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "event_inbox.csv"
            path.write_text("url,title\nhttps://news.example/1,old\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "event_inbox_schema_mismatch"):
                append_candidates(path, [{"title": "new", "link": "https://news.example/2"}])


if __name__ == "__main__":
    unittest.main()
