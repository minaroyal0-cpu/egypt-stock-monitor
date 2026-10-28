import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEN_FILE = ROOT / "seen.json"
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
    gathered = {}
    for query in QUERIES:
        for item in get_items(query):
            gathered[item["link"]] = item

    fresh = [item for link, item in gathered.items() if link not in seen]
    # Newest-first where RSS date strings are available; stable fallback otherwise.
    fresh = fresh[:MAX_ITEMS_PER_RUN]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if not fresh:
        print(f"No new items at {now}.")
        return

    for item in fresh:
        title = re.sub(r"\s+", " ", item["title"]).strip()
        msg = (
            "📡 Investor Intelligence — خبر جديد\n\n"
            f"{title}\n\n"
            f"المصدر التجميعي: {item['source']}\n"
            f"تاريخ النشر كما ورد في RSS: {item['published'] or 'غير متاح'}\n"
            f"تم الفحص: {now}\n\n"
            f"الرابط: {item['link']}\n\n"
            "تنبيه: هذا رصد آلي أولي، وليس إفصاحًا موثقًا أو توصية استثمارية. افتح المصدر الأصلي وتحقق من الخبر قبل اتخاذ أي قرار."
        )
        telegram_send(msg[:3900])
        seen.add(item["link"])
        print(f"Sent: {title}")

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
