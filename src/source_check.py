"""Conservative domain-level source classification for Egyptian market news.

A matching hostname is a routing hint only. It does not authenticate an article,
prove that a disclosure exists, or guarantee that the page content is genuine.
"""
from __future__ import annotations

from urllib.parse import urlparse

# Keep this allowlist intentionally small and explicit. Add domains only after
# independently checking the institution's official website.
OFFICIAL_DOMAINS = {
    "egx.com.eg": "البورصة المصرية",
    "fra.gov.eg": "الهيئة العامة للرقابة المالية",
    "cbe.org.eg": "البنك المركزي المصري",
}


def classify_source_url(url: str | None) -> dict:
    """Classify the URL host without following redirects or trusting publisher text."""
    raw = (url or "").strip()
    if not raw:
        return {
            "source_class": "غير معروف",
            "source_label": "رابط الناشر غير متاح في RSS",
            "source_domain": None,
            "source_note": "لا يمكن التحقق من النطاق؛ اسم الناشر وحده لا يثبت الرسمية.",
        }

    candidate = raw if "://" in raw else f"https://{raw}"
    try:
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        host = ""

    if not host:
        return {
            "source_class": "غير معروف",
            "source_label": "رابط غير صالح",
            "source_domain": None,
            "source_note": "تعذر استخراج نطاق صالح من رابط RSS.",
        }

    for domain, label in OFFICIAL_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return {
                "source_class": "نطاق مؤسسة رسمية مدرج",
                "source_label": label,
                "source_domain": host,
                "source_note": "النطاق يطابق قائمة المؤسسات الرسمية المسموح بها؛ تحقق من صفحة الإفصاح نفسها.",
            }

    return {
        "source_class": "ناشر/مصدر غير مصنف رسميًا",
        "source_label": "مصدر غير مدرج في القائمة الرسمية",
        "source_domain": host,
        "source_note": "لا يعني ذلك أن المصدر غير موثوق؛ لم يُطابق نطاقًا مدرجًا في القائمة.",
    }
