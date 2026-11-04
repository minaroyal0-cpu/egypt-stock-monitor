"""Transparent fundamental ratios with an attached data-readiness assessment."""
from .data_quality import as_number, assess_record_quality


def safe_div(a, b):
    a, b = as_number(a), as_number(b)
    return a / b if a is not None and b not in (None, 0) else None


def analyze_fundamentals(row, analysis_date=None, max_age_days=None):
    """Calculate ratios and attach explainable data-quality metadata.

    Ratios remain available for research continuity, but callers and reports
    receive a quality decision so incomplete/stale inputs are not presented
    as fully trusted. Freshness is never inferred without analysis_date.
    """
    required = ("revenue", "gross_profit", "operating_profit", "net_income", "total_assets", "total_equity")
    missing = [key for key in required if as_number(row.get(key)) is None]
    if missing:
        raise ValueError("Missing or invalid required financial fields: " + ", ".join(missing))
    quality = assess_record_quality(
        row, record_type="financial", analysis_date=analysis_date,
        max_age_days=max_age_days,
    )
    revenue, gross = as_number(row["revenue"]), as_number(row["gross_profit"])
    operating, net = as_number(row["operating_profit"]), as_number(row["net_income"])
    assets, equity = as_number(row["total_assets"]), as_number(row["total_equity"])
    debt = as_number(row.get("total_debt"))
    cash = as_number(row.get("cash_and_equivalents"))
    prior = as_number(row.get("prior_revenue"))
    cfo = as_number(row.get("operating_cash_flow"))
    capex = as_number(row.get("capital_expenditure"))
    return {
        "revenue_growth": safe_div(revenue - prior, abs(prior)) if prior not in (None, 0) else None,
        "gross_margin": safe_div(gross, revenue),
        "operating_margin": safe_div(operating, revenue),
        "net_margin": safe_div(net, revenue),
        "roe": safe_div(net, equity), "roa": safe_div(net, assets),
        "debt_to_equity": safe_div(debt, equity) if debt is not None else None,
        "net_debt": debt - cash if debt is not None and cash is not None else None,
        "current_ratio": safe_div(row.get("current_assets"), row.get("current_liabilities")),
        "operating_cash_flow": cfo,
        "free_cash_flow": cfo - abs(capex) if cfo is not None and capex is not None else None,
        "earnings_quality_flag": bool(cfo is not None and net > 0 and cfo < net),
        "source": row.get("source"), "source_url": row.get("source_url"),
        "period": row.get("period"), "currency": row.get("currency"),
        "data_status": row.get("data_status", "user_supplied"),
        "data_quality": quality,
    }
