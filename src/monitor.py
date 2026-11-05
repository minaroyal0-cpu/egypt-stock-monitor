import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from email.utils import parsedate_to_datetime

from impact import analyze_headline
from source_check import classify_source_url
from audit_log import append_bounded, make_audit_record

ROOT = Path(__file__).resolve().parents[1]
SEEN_FILE = ROOT / "seen.json"
AUDIT_FILE = ROOT / "audit.json"
MAX_AUDIT_RECORDS = 1000
MAX_ITEMS_PER_RUN = 8
MAX_SEEN = 500

# Google News RSS queries. These are discovery feeds, not official disclosures.
QUERIES = [
    'البورصة المصرية EGX',
    'البورصة المصرية إفصاح شركة',
    'الرقابة المالية مصر إفصاح',
    'البنك المركزي المصري أسعار الفائدة',
    'Egyptian Exchange EGX stocks',
    'Egypt stocks company disclosure',
]


def fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "InvestorIntelligenceFree/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def get_items(query: str):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query,
        "hl": "ar",
        "gl": "EG",
        "ceid": "EG:ar",
    })
    try:
        root = ET.fromstring(fetch(url))
    except Exception as exc:
        print(f"RSS fetch failed for {query!r}: {exc}")
        return []
    items = []
    for node in root.findall("./channel/item"):
        def get(tag):
            el = node.find(tag)
            return (el.text or "").strip() if el is not None else ""
        title, link = get("title"), get("link")
        if not title or not link:
            continue
        items.append({
            "title": title,
            "link": link,
            "published": get("pubDate"),
            "source": (node.findtext("source") or "Google News RSS").strip(),
            "source_url": (node.find("source").get("url", "") if node.find("source") is not None else ""),
            "query": query,
        })
    return items


def load_seen():
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def telegram_send(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID secret")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError("Telegram API returned ok=false")


def main():
    seen_list = load_seen()
    seen = set(seen_list)
    try:
        audit_records = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
        if not isinstance(audit_records, list):
            audit_records = []
    except (OSError, ValueError):
        audit_records = []
    gathered = {}
    for query in QUERIES:
        for item in get_items(query):
            gathered[item["link"]] = item

    fresh = [item for link, item in gathered.items() if link not in seen]
    # Prefer the newest RSS items; malformed/missing dates sort to the end.
    def published_key(item):
        try:
            return parsedate_to_datetime(item["published"]).timestamp()
        except Exception:
            return 0
    fresh.sort(key=published_key, reverse=True)
    fresh = fresh[:MAX_ITEMS_PER_RUN]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if not fresh:
        print(f"No new items at {now}.")
        return

    for item in fresh:
        title = re.sub(r"\s+", " ", item["title"]).strip()
        impact = analyze_headline(title, source_name=item["source"])
        source_check = classify_source_url(item.get("source_url"))
        alerted = False
        if impact["important"]:
            msg = (
                f"📡 EGX Impact Intelligence — {impact['review_priority']}\n\n"
                f"{title}\n\n"
                f"أولوية المراجعة: {impact['review_priority']}\n"
                f"السبب: {impact['priority_reason']}\n"
                f"درجة المراجعة: {impact['review_score']}/100 (ليست توقعًا سعريًا)\n"
                f"المصدر الظاهر: {impact['source_context']}\n"
                f"فحص النطاق: {source_check['source_class']} — {source_check['source_label']}\n"
                f"النطاق: {source_check['source_domain'] or 'غير متاح'}\n"
                f"ملاحظة التحقق: {source_check['source_note']}\n\n"
                f"{impact['analysis']}\n\n"
                f"المصدر التجميعي: {item['source']}\n"
                f"تاريخ النشر كما ورد في RSS: {item['published'] or 'غير متاح'}\n"
                f"تم الفحص: {now}\n\n"
                f"الرابط: {item['link']}\n\n"
                "مهم: الرصد مبني على عنوان RSS فقط. تحقق من المصدر الأصلي والإفصاح، ولا تعتبره توصية أو توقعًا لحركة السعر."
            )
            telegram_send(msg[:3900])
            alerted = True
            print(f"Alert sent: {title}")
        else:
            print(f"Skipped (not portfolio-relevant/important): {title}")
        # Mark both alerted and filtered items as processed to avoid rescanning them forever.
        audit_records = append_bounded(
            audit_records,
            make_audit_record(item, impact, source_check, alerted),
            MAX_AUDIT_RECORDS,
        )
        seen.add(item["link"])

    AUDIT_FILE.write_text(
        json.dumps(audit_records, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8"
    )

    # Save a bounded history; workflow commits this file back to the repository.
    ordered = list(seen_list)
    for item in fresh:
        if item["link"] not in ordered:
            ordered.append(item["link"])
    SEEN_FILE.write_text(json.dumps(ordered[-MAX_SEEN:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        raise
