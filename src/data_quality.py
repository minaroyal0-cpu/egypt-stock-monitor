"""Input validation and provenance helpers; deliberately performs no web scraping."""
from datetime import date

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
