"""Append newly discovered RSS headlines to a human-review event inbox.

No ticker or event date is inferred from a headline. Rows remain pending until
a person verifies the original disclosure, company mapping, and event date.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

FIELDS = [
    "event_id", "title", "url", "rss_published", "publisher_label",
    "review_status", "verified_symbol", "verified_event_date", "review_notes",
]
MAX_ROWS = 2000


def append_candidates(path: str | Path, items: list[dict]) -> int:
    """Append unseen article URLs; return the number of new candidate rows."""
    target = Path(path)
    existing: list[dict] = []
    known_urls: set[str] = set()
    if target.exists() and target.stat().st_size:
        with target.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames and not set(FIELDS).issubset(reader.fieldnames):
                raise ValueError("event_inbox_schema_mismatch")
            for row in reader:
                existing.append({field: row.get(field, "") or "" for field in FIELDS})
                if row.get("url"):
                    known_urls.add(row["url"])

    added = 0
    for item in items:
        url = str(item.get("link") or "").strip()
        title = str(item.get("title") or "").strip()
        if not url or not title or url in known_urls:
            continue
        event_id = "rss-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        existing.append({
            "event_id": event_id,
            "title": title,
            "url": url,
            "rss_published": str(item.get("published") or "").strip(),
            "publisher_label": str(item.get("source") or "").strip(),
            "review_status": "needs_review",
            "verified_symbol": "",
            "verified_event_date": "",
            "review_notes": "",
        })
        known_urls.add(url)
        added += 1

    if added:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(existing[-MAX_ROWS:])
    return added
