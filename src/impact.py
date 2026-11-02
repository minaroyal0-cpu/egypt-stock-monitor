"""Conservative, headline-only EGX portfolio impact screening.

This is a transparent rules engine, not a price predictor or investment recommendation.
It deliberately avoids assigning an impact when the headline does not identify a clear channel.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "config" / "portfolio.json"

# Each rule is intentionally broad only at the sector level. Company-specific matches
# are preferred; macro rules are used only when the headline names a relevant channel.
RULES = [
    {
        "id": "rates",
        "terms": ["سعر الفائدة", "أسعار الفائدة", "خفض الفائدة", "رفع الفائدة", "الفائدة", "interest rate", "rate cut", "rate hike"],
        "sectors": ["banking", "real_estate", "consumer", "utilities"],
        "channel": "تكلفة التمويل والطلب والعائد على الودائع/القروض",
        "horizon": "متوسط الأجل",
        "note": "تغير الفائدة قد يغير تكلفة التمويل والطلب وهوامش البنوك؛ الاتجاه النهائي يختلف حسب الشركة ومقدار ما كان متوقعًا بالفعل.",
        "strength": "متوسط",
    },
    {
        "id": "fx",
        "terms": ["سعر الصرف", "الجنيه", "الدولار", "تحرير سعر الصرف", "خفض قيمة العملة", "devaluation", "exchange rate", "egyptian pound"],
        "sectors": ["fertilizers", "telecom", "real_estate", "utilities", "banking"],
        "channel": "تكلفة المدخلات المستوردة والديون الأجنبية والإيرادات المرتبطة بالعملة",
        "horizon": "قصير إلى متوسط الأجل",
        "note": "الأثر يعتمد على صافي التعرض للعملات الأجنبية، وليس على حركة سعر الصرف وحدها.",
        "strength": "متوسط",
    },
    {
        "id": "energy",
        "terms": ["الغاز", "الطاقة", "الكهرباء", "الوقود", "أسعار الغاز", "oil", "gas", "fuel", "electricity", "energy"],
        "sectors": ["fertilizers", "utilities"],
        "channel": "تكلفة الطاقة والإنتاج أو إيرادات نشاط الطاقة",
        "horizon": "قصير إلى متوسط الأجل",
        "note": "قد تتغير تكلفة التشغيل أو الإيرادات؛ يلزم معرفة التعريفة والعقود ومزيج الوقود.",
        "strength": "متوسط",
    },
    {
        "id": "fertilizer",
        "terms": ["الأسمدة", "اليوريا", "الأمونيا", "تصدير الأسمدة", "fertilizer", "urea", "ammonia"],
        "sectors": ["fertilizers"],
        "channel": "أسعار البيع وحجم الصادرات وتكلفة الغاز ومدخلات الإنتاج",
        "horizon": "قصير إلى متوسط الأجل",
        "note": "قد يؤثر على شركات الأسمدة، لكن أثره على ABUK يتوقف على الأسعار والكميات والتكلفة الفعلية.",
        "strength": "متوسط",
    },
    {
        "id": "real_estate",
        "terms": ["العقارات", "التطوير العقاري", "مبيعات عقارية", "تسليم وحدات", "real estate", "property developer"],
        "sectors": ["real_estate"],
        "channel": "المبيعات الجديدة والتحصيلات وتكلفة مواد البناء والتمويل",
        "horizon": "متوسط إلى طويل الأجل",
        "note": "العنوان وحده لا يوضح جودة المبيعات أو التحصيل أو هوامش المشروعات.",
        "strength": "متوسط",
    },
    {
        "id": "fintech",
        "terms": ["التكنولوجيا المالية", "الخدمات المالية الرقمية", "الشمول المالي", "التمويل الرقمي", "fintech", "digital financial services", "financial inclusion"],
        "sectors": ["fintech", "payments"],
        "channel": "نمو العملاء والمعاملات والتمويل الرقمي وتكلفة اكتساب العميل",
        "horizon": "متوسط إلى طويل الأجل",
        "note": "نمو نشاط التكنولوجيا المالية لا يساوي تلقائيًا نمو أرباح HALN؛ جودة الإيرادات والتكلفة والتنظيم والتمويل عوامل حاسمة.",
        "strength": "متوسط",
    },
    {
        "id": "payments",
        "terms": ["المدفوعات الإلكترونية", "الدفع الإلكتروني", "المحافظ الإلكترونية", "التكنولوجيا المالية", "fintech", "digital payments", "e-payments"],
        "sectors": ["payments"],
        "channel": "حجم المعاملات والعمولات وانتشار الخدمات الرقمية",
        "horizon": "متوسط إلى طويل الأجل",
        "note": "نمو القطاع لا يضمن نمو أرباح كل شركة؛ المنافسة والهوامش والتنظيم مهمة.",
        "strength": "متوسط",
    },
    {
        "id": "telecom",
        "terms": ["الاتصالات", "شبكات المحمول", "الترددات", "telecom", "mobile network", "spectrum"],
        "sectors": ["telecom"],
        "channel": "الإيرادات التشغيلية والإنفاق الرأسمالي وتكلفة الترددات",
        "horizon": "متوسط الأجل",
        "note": "الأثر يتوقف على الشركة المعنية والتسعير والإنفاق الاستثماري.",
        "strength": "متوسط",
    },
    {
        "id": "banking",
        "terms": ["البنوك", "القطاع المصرفي", "الودائع", "القروض", "الائتمان", "banks", "banking", "deposits", "loans"],
        "sectors": ["banking"],
        "channel": "صافي هامش العائد وجودة الأصول ونمو الائتمان",
        "horizon": "متوسط الأجل",
        "note": "لا يمكن استنتاج أثر صافٍ على بنك بعينه دون بيانات الهامش وجودة القروض.",
        "strength": "متوسط",
    },
]

COMPANIES = {
    "ETEL": {"name": "المصرية للاتصالات", "sector": "telecom", "aliases": ["المصرية للاتصالات", "we", "telecom egypt"]},
    "ABUK": {"name": "أبو قير للأسمدة", "sector": "fertilizers", "aliases": ["أبو قير للأسمدة", "ابو قير للاسمدة", "abu qir fertilizers"]},
    "TMGH": {"name": "مجموعة طلعت مصطفى", "sector": "real_estate", "aliases": ["طلعت مصطفى", "مجموعة طلعت مصطفى", "talaat moustafa", "tmgh"]},
    "TAQA": {"name": "طاقة عربية", "sector": "utilities", "aliases": ["طاقة عربية", "taqa arabia"]},
    "HALN": {"name": "حالا", "sector": "fintech", "aliases": ["حالا", "halan"]},
    "FWRY": {"name": "فوري", "sector": "payments", "aliases": ["فوري", "fawry"]},
    "BQDC": {"name": "بنك القاهرة", "sector": "banking", "aliases": ["بنك القاهرة", "banque du caire"]},
}

DIRECTION_TERMS = {
    "positive": ["ارتفاع", "زيادة", "نمو", "تحسن", "خفض", "تراجع تكلفة", "ربحية", "صادرات قياسية", "increase", "growth", "improved", "cut"],
    "negative": ["انخفاض", "تراجع", "هبوط", "خسائر", "أزمة", "زيادة تكلفة", "غرامة", "إيقاف", "decline", "loss", "crisis", "fine", "suspend", "higher cost"],
}


def _norm(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"[إأآا]", "ا", value)
    value = re.sub(r"[ىي]", "ي", value)
    value = re.sub(r"\s+", " ", value)
    return value


def load_portfolio() -> list[str]:
    try:
        data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        return [s for s in data.get("symbols", []) if s in COMPANIES]
    except (OSError, ValueError, TypeError):
        return list(COMPANIES)


def analyze_headline(title: str, portfolio: list[str] | None = None) -> dict:
    text = _norm(title)
    portfolio = portfolio if portfolio is not None else load_portfolio()
    matched_companies = []
    for symbol in portfolio:
        company = COMPANIES.get(symbol)
        if not company:
            continue
        if symbol.lower() in text or any(_norm(alias) in text for alias in company["aliases"]):
            matched_companies.append(symbol)

    matched_rules = [rule for rule in RULES if any(_norm(term) in text for term in rule["terms"])]
    sectors = {COMPANIES[s]["sector"] for s in matched_companies}
    for rule in matched_rules:
        if sectors.intersection(rule["sectors"]):
            continue
        # Sector-only macro links are shown as watch items, not direct company impacts.
    relevant = bool(matched_companies)
    applicable = [r for r in matched_rules if any(COMPANIES[s]["sector"] in r["sectors"] for s in matched_companies)]
    if not matched_companies and matched_rules:
        relevant = False

    positive = any(_norm(term) in text for term in DIRECTION_TERMS["positive"])
    negative = any(_norm(term) in text for term in DIRECTION_TERMS["negative"])
    direction = "مختلط/غير محسوم"
    if positive and not negative:
        direction = "إشارة إيجابية محتملة"
    elif negative and not positive:
        direction = "إشارة سلبية محتملة"
    elif positive and negative:
        direction = "مختلط"

    important = relevant and bool(applicable)
    if not important:
        return {
            "important": False,
            "relevant": relevant,
            "symbols": matched_companies,
            "direction": direction,
            "analysis": "لا توجد صلة مباشرة كافية بمحفظتك من عنوان الخبر وحده؛ لم يتم تصنيفه كتنبيه مهم.",
        }

    rules_text = " | ".join(dict.fromkeys(r["channel"] for r in applicable))
    notes = " ".join(dict.fromkeys(r["note"] for r in applicable))
    horizons = "، ".join(dict.fromkeys(r["horizon"] for r in applicable))
    names = "، ".join(f"{s} ({COMPANIES[s]['name']})" for s in matched_companies)
    return {
        "important": True,
        "relevant": True,
        "symbols": matched_companies,
        "direction": direction,
        "analysis": (
            f"📌 صلة بالمحفظة: {names}\n"
            f"الاتجاه: {direction}\n"
            f"قناة التأثير المحتملة: {rules_text}\n"
            f"الأفق: {horizons}\n"
            f"التفسير والتحفظ: {notes}\n"
            "الثقة: منخفضة؛ التحليل مبني على العنوان فقط وليس متن الخبر أو الإفصاح. "
            "لا يثبت أن السعر سيتحرك، وقد يكون الأثر محسوبًا بالفعل في السعر. "
            "ما قد يبطل القراءة: اختلاف تفاصيل الخبر أو عدم انعكاسه على نتائج الشركة."
        ),
    }
