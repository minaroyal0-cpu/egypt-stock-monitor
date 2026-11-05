"""Transparent EGX headline screening for the configured watchlist.

Discovery-only rules engine: it does not verify disclosures, read full articles, value
securities, forecast prices, or generate trading instructions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "config" / "portfolio.json"

COMPANIES = {
    "ETEL": {"name": "المصرية للاتصالات", "sector": "telecom", "aliases": ["المصرية للاتصالات", "we", "telecom egypt"]},
    "ABUK": {"name": "أبو قير للأسمدة", "sector": "fertilizers", "aliases": ["أبو قير للأسمدة", "ابو قير للاسمدة", "abu qir fertilizers"]},
    "TMGH": {"name": "مجموعة طلعت مصطفى", "sector": "real_estate", "aliases": ["طلعت مصطفى", "مجموعة طلعت مصطفى", "talaat moustafa", "tmgh"]},
    "TAQA": {"name": "طاقة عربية", "sector": "utilities", "aliases": ["طاقة عربية", "taqa arabia"]},
    "HALN": {"name": "حالا", "sector": "fintech", "aliases": ["حالا", "halan"]},
    "FWRY": {"name": "فوري", "sector": "payments", "aliases": ["فوري", "fawry"]},
    "BQDC": {"name": "بنك القاهرة", "sector": "banking", "aliases": ["بنك القاهرة", "banque du caire"]},
}

ALL_SECTORS = sorted({company["sector"] for company in COMPANIES.values()})

# "حالا" is also a common Arabic word meaning "currently/now". Require
# financial-services context before treating that word as a direct HALN mention.
HALN_CONTEXT_TERMS = [
    "التكنولوجيا المالية", "الخدمات المالية", "التمويل", "تقسيط",
    "مدفوعات", "محفظة إلكترونية", "خدمات مالية", "halan", "fintech",
]

RULES = [
    {
        "id": "corporate_event",
        "terms": ["القوائم المالية", "نتائج الأعمال", "النتائج المالية", "نتائج الاعمال", "مجلس الإدارة", "مجلس الادارة", "توزيعات", "زيادة رأس المال", "زيادة راس المال", "تخفيض رأس المال", "عقد جديد", "توقيع عقد", "استحواذ", "اندماج", "بيع أصول", "بيع اصول", "إيقاف", "ايقاف", "غرامة", "دعوى", "قرض جديد", "تمويل جديد", "financial results", "board of directors", "dividend", "capital increase", "acquisition", "merger", "new contract", "fine", "lawsuit"],
        "sectors": ALL_SECTORS,
        "channel": "الأرباح والتدفقات النقدية والديون والحوكمة وتوقعات النشاط",
        "horizon": "قصير إلى طويل الأجل حسب طبيعة الحدث",
        "note": "الحدث قد يكون جوهريًا، لكن يلزم قراءة الإفصاح والأرقام والشروط والأثر على التدفقات النقدية.",
    },
    {
        "id": "rates",
        "terms": ["سعر الفائدة", "أسعار الفائدة", "خفض الفائدة", "رفع الفائدة", "الفائدة", "interest rate", "rate cut", "rate hike"],
        "sectors": ["banking", "real_estate", "utilities", "fintech", "payments"],
        "channel": "تكلفة التمويل والطلب وهوامش البنوك وتقييم التدفقات النقدية",
        "horizon": "متوسط الأجل",
        "note": "الأثر يختلف حسب صافي الدين وهيكل التمويل وحساسية الودائع والقروض، وقد يكون القرار متوقعًا بالفعل.",
    },
    {
        "id": "fx",
        "terms": ["سعر الصرف", "الجنيه", "الدولار", "تحرير سعر الصرف", "خفض قيمة العملة", "devaluation", "exchange rate", "egyptian pound"],
        "sectors": ["fertilizers", "telecom", "real_estate", "utilities", "banking", "payments", "fintech"],
        "channel": "تكلفة المدخلات المستوردة والديون الأجنبية والإيرادات المرتبطة بالعملة",
        "horizon": "قصير إلى متوسط الأجل",
        "note": "الأثر يعتمد على صافي التعرض للعملات الأجنبية والتحوط والتسعير، وليس على حركة سعر الصرف وحدها.",
    },
    {
        "id": "energy",
        "terms": ["الغاز", "الطاقة", "الكهرباء", "الوقود", "أسعار الغاز", "oil", "gas", "fuel", "electricity", "energy"],
        "sectors": ["fertilizers", "utilities"],
        "channel": "تكلفة الطاقة والإنتاج أو إيرادات نشاط الطاقة",
        "horizon": "قصير إلى متوسط الأجل",
        "note": "يلزم معرفة التعريفة والعقود ومزيج الوقود؛ زيادة السعر ليست إيجابية أو سلبية لكل الشركات.",
    },
    {
        "id": "fertilizer",
        "terms": ["الأسمدة", "اليوريا", "الأمونيا", "تصدير الأسمدة", "fertilizer", "urea", "ammonia"],
        "sectors": ["fertilizers"],
        "channel": "أسعار البيع وحجم الصادرات وتكلفة الغاز ومدخلات الإنتاج",
        "horizon": "قصير إلى متوسط الأجل",
        "note": "الأثر على ABUK يتوقف على أسعار البيع والكميات وتكلفة الغاز ومزيج التصدير والمحلي.",
    },
    {
        "id": "real_estate",
        "terms": ["العقارات", "التطوير العقاري", "مبيعات عقارية", "تسليم وحدات", "real estate", "property developer"],
        "sectors": ["real_estate"],
        "channel": "المبيعات والتحصيلات وتكلفة مواد البناء والتمويل",
        "horizon": "متوسط إلى طويل الأجل",
        "note": "نمو المبيعات المعلنة لا يكفي وحده؛ التحصيل وهوامش المشروعات والالتزامات مهمة.",
    },
    {
        "id": "fintech",
        "terms": ["التكنولوجيا المالية", "الخدمات المالية الرقمية", "الشمول المالي", "التمويل الرقمي", "fintech", "digital financial services", "financial inclusion"],
        "sectors": ["fintech", "payments"],
        "channel": "نمو العملاء والمعاملات والتمويل الرقمي وتكلفة اكتساب العميل",
        "horizon": "متوسط إلى طويل الأجل",
        "note": "نمو القطاع لا يساوي تلقائيًا نمو أرباح HALN أو FWRY؛ المنافسة والهوامش والتنظيم عوامل حاسمة.",
    },
    {
        "id": "telecom",
        "terms": ["الاتصالات", "شبكات المحمول", "الترددات", "telecom", "mobile network", "spectrum"],
        "sectors": ["telecom"],
        "channel": "الإيرادات التشغيلية والإنفاق الرأسمالي وتكلفة الترددات",
        "horizon": "متوسط الأجل",
        "note": "الأثر على ETEL يتوقف على التسعير والمنافسة والإنفاق الاستثماري والتزامات الترددات.",
    },
    {
        "id": "banking",
        "terms": ["البنوك", "القطاع المصرفي", "الودائع", "القروض", "الائتمان", "banks", "banking", "deposits", "loans"],
        "sectors": ["banking"],
        "channel": "صافي هامش العائد وجودة الأصول ونمو الائتمان",
        "horizon": "متوسط الأجل",
        "note": "لا يمكن استنتاج أثر صافٍ على BQDC دون بيانات الهامش وجودة القروض والتكلفة.",
    },
    {
        "id": "payments",
        "terms": ["المدفوعات الإلكترونية", "الدفع الإلكتروني", "المحافظ الإلكترونية", "digital payments", "e-payments"],
        "sectors": ["payments"],
        "channel": "حجم المعاملات والعمولات وانتشار الخدمات الرقمية",
        "horizon": "متوسط إلى طويل الأجل",
        "note": "نمو المدفوعات لا يضمن نمو أرباح FWRY؛ المنافسة والعمولات وتكاليف التشغيل مهمة.",
    },
]

TONE_TERMS = {
    "positive": ["ارتفاع", "زيادة", "نمو", "تحسن", "خفض", "تراجع تكلفة", "ربحية", "صادرات قياسية", "increase", "growth", "improved", "cut"],
    "negative": ["انخفاض", "تراجع", "هبوط", "خسائر", "أزمة", "زيادة تكلفة", "غرامة", "إيقاف", "decline", "loss", "crisis", "fine", "suspend", "higher cost"],
}


def normalize(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"[إأآا]", "ا", value)
    value = re.sub(r"[ىي]", "ي", value)
    value = re.sub(r"\s+", " ", value)
    return value


def load_portfolio() -> list[str]:
    try:
        data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        symbols = data.get("symbols", [])
        return [symbol for symbol in symbols if symbol in COMPANIES]
    except (OSError, ValueError, TypeError):
        return []


def _matches_company(text: str, symbol: str, company: dict) -> bool:
    # Match ticker tokens, not accidental substrings inside longer words.
    if re.search(r"(?<![a-z0-9])" + re.escape(symbol.lower()) + r"(?![a-z0-9])", text):
        return True
    for alias in company["aliases"]:
        normalized_alias = normalize(alias)
        if symbol == "HALN" and normalized_alias == normalize("حالا"):
            if not any(normalize(term) in text for term in HALN_CONTEXT_TERMS):
                continue
        if normalized_alias and normalized_alias in text:
            return True
    return False


def analyze_headline(title: str, portfolio: list[str] | None = None) -> dict:
    text = normalize(title)
    portfolio = portfolio if portfolio is not None else load_portfolio()
    portfolio = [symbol for symbol in portfolio if symbol in COMPANIES]

    direct = []
    for symbol in portfolio:
        if _matches_company(text, symbol, COMPANIES[symbol]):
            direct.append(symbol)

    matched_rules = [rule for rule in RULES if any(normalize(term) in text for term in rule["terms"])]
    relevant_rules = [
        rule for rule in matched_rules
        if any(COMPANIES[symbol]["sector"] in rule["sectors"] for symbol in portfolio)
    ]
    indirectly_relevant = [
        symbol for symbol in portfolio
        if COMPANIES[symbol]["sector"] in {sector for rule in relevant_rules for sector in rule["sectors"]}
    ]
    symbols = list(dict.fromkeys(direct + indirectly_relevant))
    applicable = [
        rule for rule in relevant_rules
        if any(COMPANIES[symbol]["sector"] in rule["sectors"] for symbol in symbols)
    ]

    positive = any(normalize(term) in text for term in TONE_TERMS["positive"])
    negative = any(normalize(term) in text for term in TONE_TERMS["negative"])
    if positive and negative:
        headline_tone = "مختلطة"
    elif positive:
        headline_tone = "إيجابية لغويًا فقط"
    elif negative:
        headline_tone = "سلبية لغويًا فقط"
    else:
        headline_tone = "محايدة/غير واضحة"

    match_type = "مباشر" if direct else ("قطاعي غير مباشر" if indirectly_relevant else "لا توجد صلة محددة")
    important = bool(symbols and applicable)
    if direct and any(rule["id"] == "corporate_event" for rule in applicable):
        review_priority = "أولوية مرتفعة"
        priority_reason = "ذكر مباشر لشركة مع حدث مؤسسي محتمل؛ راجع الإفصاح الأصلي أولًا."
    elif important:
        review_priority = "أولوية عادية"
        priority_reason = "صلة قطاعية أو اقتصادية محتملة؛ راجع التفاصيل قبل تحديد الأثر."
    else:
        review_priority = "لا أولوية"
        priority_reason = "لم تتحقق صلة كافية بالمحفظة وفق قواعد العنوان الحالية."

    if not important:
        return {
            "important": False,
            "symbols": [],
            "direct_symbols": [],
            "match_type": match_type,
            "direction": "غير محسوم من العنوان وحده",
            "headline_tone": headline_tone,
            "review_priority": review_priority,
            "priority_reason": priority_reason,
            "analysis": "لم تظهر صلة كافية بمحفظتك وفق قواعد الفحص؛ لم يُرسل تنبيه.",
        }

    channels = " | ".join(dict.fromkeys(rule["channel"] for rule in applicable))
    notes = " ".join(dict.fromkeys(rule["note"] for rule in applicable))
    horizons = "، ".join(dict.fromkeys(rule["horizon"] for rule in applicable))
    names = "، ".join(f"{symbol} ({COMPANIES[symbol]['name']})" for symbol in symbols)
    confidence = "منخفضة جدًا" if not direct else "منخفضة"
    return {
        "important": True,
        "symbols": symbols,
        "direct_symbols": direct,
        "match_type": match_type,
        "direction": "غير محسوم من العنوان وحده",
        "headline_tone": headline_tone,
        "review_priority": review_priority,
        "priority_reason": priority_reason,
        "analysis": (
            f"أولوية المراجعة: {review_priority} — {priority_reason}\n"
            f"📌 الأسهم المرتبطة: {names}\n"
            f"نوع الصلة: {match_type}\n"
            "اتجاه الأثر على السعر: غير محسوم من العنوان وحده\n"
            f"نبرة العنوان فقط: {headline_tone}\n"
            f"قنوات التأثير المحتملة: {channels}\n"
            f"الأفق المحتمل: {horizons}\n"
            f"الثقة: {confidence}\n"
            f"التحفظ: {notes}\n"
            "ما قد يبطل القراءة: تفاصيل الخبر أو العقود أو الأرقام قد تغير الأثر؛ وقد يكون الخبر محسوبًا في السعر بالفعل. "
            "يلزم فتح المصدر الأصلي والإفصاح وقراءة الأرقام قبل أي استنتاج."
        ),
    }
