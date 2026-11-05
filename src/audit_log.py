"""Small, bounded audit trail for headline-screening decisions."""
from __future__ import annotations

from datetime import datetime, timezone


def make_audit_record(item: dict, impact: dict, source_check: dict, alerted: bool) -> dict:
    """Capture what the monitor knew at scan time; never imply later price impact."""
    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": item.get("title", ""),
        "url": item.get("link", ""),
        "published_rss": item.get("published", ""),
        "rss_publisher_label": item.get("source", ""),
        "source_class": source_check.get("source_class", "غير معروف"),
        "source_domain": source_check.get("source_domain"),
        "important": bool(impact.get("important")),
        "symbols": list(impact.get("symbols", [])),
        "match_type": impact.get("match_type", ""),
        "review_priority": impact.get("review_priority", ""),
        "review_score": int(impact.get("review_score", 0)),
        "score_reasons": list(impact.get("score_reasons", [])),
        "headline_tone": impact.get("headline_tone", ""),
        "alerted": bool(alerted),
        "assessment_type": "عنوان RSS فقط؛ ليس قياسًا للعائد أو أثر السعر",
    }


def append_bounded(records: list, record: dict, limit: int = 1000) -> list:
    """Return newest records only, with a defensive minimum limit."""
    safe_limit = max(1, int(limit))
    return (list(records) + [record])[-safe_limit:]
