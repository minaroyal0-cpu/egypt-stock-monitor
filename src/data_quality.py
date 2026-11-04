"""Explainable provenance and freshness scoring for imported market records.

The score is a data-readiness indicator, not a probability that a value is correct.
"""
from datetime import date
from urllib.parse import urlparse

SOURCE_POINTS = {
    "official": 26,
    "third_party": 20,
    "user_supplied": 12,
    "estimate": 5,
}
DEFAULT_MAX_AGE_DAYS = {"financial": 550, "prices": 7, "actions": 550}


def _valid_iso_date(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError):
        return None


def assess_record_quality(record, record_type="financial", analysis_date=None,
                          max_age_days=None):
    """Return a transparent 0-100 quality score and explicit analysis warnings.

    Freshness is scored only when analysis_date is supplied. Missing or invalid
    provenance/date metadata prevents a record from being marked analysis-ready.
    """
    if record_type not in DEFAULT_MAX_AGE_DAYS:
        raise ValueError("record_type must be financial, prices, or actions")

    score = 0
    reasons = []
    warnings = []
    status = str(record.get("data_status", "")).strip().lower()
    if status in SOURCE_POINTS:
        score += SOURCE_POINTS[status]
        reasons.append("source_status:" + status)
    else:
        warnings.append("unknown_or_missing_data_status")

    source = str(record.get("source", "")).strip()
    if source:
        score += 8
        reasons.append("source_identity_present")
    else:
        warnings.append("source_identity_missing")

    source_url = str(record.get("source_url", "")).strip()
    parsed = urlparse(source_url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        score += 12
        reasons.append("source_url_present")
    else:
        warnings.append("source_url_missing_or_invalid")

    symbol = str(record.get("symbol", "")).strip()
    if symbol:
        score += 8
        reasons.append("symbol_present")
    else:
        warnings.append("symbol_missing")

    currency = str(record.get("currency", "")).strip()
    if len(currency) == 3 and currency.isalpha():
        score += 6
        reasons.append("currency_present")
    else:
        warnings.append("currency_missing_or_invalid")

    if record_type == "financial":
        key_date = record.get("as_of")
        if str(record.get("period", "")).strip():
            score += 5
            reasons.append("reporting_period_present")
        else:
            warnings.append("reporting_period_missing")
        if str(record.get("basis", "")).strip():
            score += 5
            reasons.append("reporting_basis_present")
        else:
            warnings.append("reporting_basis_missing")
    elif record_type == "prices":
        key_date = record.get("date")
        if _valid_iso_date(key_date):
            score += 10
            reasons.append("price_date_present")
        else:
            warnings.append("price_date_missing_or_invalid")
    else:
        key_date = record.get("ex_date")
        if _valid_iso_date(key_date):
            score += 10
            reasons.append("ex_date_present")
        else:
            warnings.append("ex_date_missing_or_invalid")

    as_of = _valid_iso_date(record.get("as_of"))
    if not as_of:
        warnings.append("as_of_missing_or_invalid")
    else:
        reasons.append("as_of_date_valid")

    freshness_assessed = False
    if analysis_date is None:
        warnings.append("freshness_not_assessed_supply_analysis_date")
    else:
        reference = _valid_iso_date(analysis_date)
        if not reference:
            raise ValueError("analysis_date must be YYYY-MM-DD")
        if not as_of:
            warnings.append("freshness_unavailable_without_as_of")
        else:
            freshness_assessed = True
            age_days = (date.fromisoformat(reference) - date.fromisoformat(as_of)).days
            if age_days < 0:
                warnings.append("as_of_date_is_in_the_future")
            else:
                limit = max_age_days if max_age_days is not None else DEFAULT_MAX_AGE_DAYS[record_type]
                if not isinstance(limit, int) or limit <= 0:
                    raise ValueError("max_age_days must be a positive integer")
                freshness_points = max(0, 30 * (1 - age_days / limit))
                score += round(freshness_points)
                reasons.append("freshness_age_days:" + str(age_days))
                if age_days > limit:
                    warnings.append("stale_data_exceeds_max_age")

    score = min(100, max(0, score))
    hard_blocks = {
        "unknown_or_missing_data_status", "source_identity_missing",
        "source_url_missing_or_invalid", "symbol_missing",
        "currency_missing_or_invalid", "as_of_missing_or_invalid",
    }
    if record_type == "financial":
        hard_blocks.update(("reporting_period_missing", "reporting_basis_missing"))
    elif record_type == "prices":
        hard_blocks.add("price_date_missing_or_invalid")
    else:
        hard_blocks.add("ex_date_missing_or_invalid")

    blocked = any(item in hard_blocks for item in warnings)
    if blocked:
        decision = "insufficient"
    elif status == "estimate":
        decision = "estimate_only"
    elif not freshness_assessed:
        decision = "review_required"
    elif "as_of_date_is_in_the_future" in warnings or "stale_data_exceeds_max_age" in warnings:
        decision = "review_required"
    elif score >= 80:
        decision = "analysis_ready"
    elif score >= 60:
        decision = "conditional"
    else:
        decision = "insufficient"

    return {
        "score": score,
        "decision": decision,
        "eligible_for_analysis": decision in ("analysis_ready", "conditional"),
        "freshness_assessed": freshness_assessed,
        "reasons": reasons,
        "warnings": warnings,
        "score_is_probability": False,
    }


def as_number(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def validate_financial_record(row):
    issues = []
    required = ("company", "period", "currency", "source", "revenue", "net_income")
    for key in required:
        if row.get(key) in (None, ""):
            issues.append("missing:" + key)
    if row.get("period"):
        try:
            date.fromisoformat(str(row["period"]) + "-01" if len(str(row["period"])) == 7 else str(row["period"]))
        except ValueError:
            issues.append("invalid_period_format")
    for key, value in row.items():
        if key in ("revenue", "net_income", "gross_profit", "operating_profit", "total_assets",
                   "total_equity", "total_debt", "cash_and_equivalents", "current_assets",
                   "current_liabilities", "operating_cash_flow", "capital_expenditure"):
            if value not in (None, "") and as_number(value) is None:
                issues.append("invalid_number:" + key)
    if row.get("currency") and len(str(row["currency"])) != 3:
        issues.append("invalid_currency_code")
    if not row.get("source_url"):
        issues.append("source_url_missing")
    status = row.get("data_status", "user_supplied")
    if status not in ("official", "third_party", "user_supplied", "estimate"):
        issues.append("unknown_data_status")
    return {"valid": not issues, "issues": issues, "data_status": status}


def compare_periods(current, previous):
    """Reject unsafe comparisons across currency or reporting basis."""
    if current.get("currency") != previous.get("currency"):
        raise ValueError("Cannot compare records with different currencies")
    if current.get("basis", "reported") != previous.get("basis", "reported"):
        raise ValueError("Cannot compare reported and adjusted figures without normalization")
    return True
