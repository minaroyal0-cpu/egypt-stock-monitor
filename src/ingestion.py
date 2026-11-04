"""CSV ingestion for sourced EGX financial statements and daily OHLCV.

No prices or statements are invented or fetched from an undocumented endpoint.
Input files must carry source and as-of metadata; rejected rows are reported.
"""
import csv
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path

FINANCIAL_NUMBERS = {
    "revenue", "gross_profit", "operating_profit", "net_income", "total_assets",
    "total_equity", "total_debt", "cash_and_equivalents", "current_assets",
    "current_liabilities", "operating_cash_flow", "capital_expenditure",
    "shares_outstanding", "eps", "book_value_per_share", "dividend_per_share",
}
PRICE_NUMBERS = {"open", "high", "low", "close", "volume", "turnover_egp", "adjusted_close"}
STATUSES = {"official", "third_party", "user_supplied", "estimate"}

def _number(value, field, allow_empty=False):
    if value in (None, "") and allow_empty:
        return None
    try:
        n = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ValueError(f"invalid_number:{field}")
    if not math.isfinite(n):
        raise ValueError(f"non_finite_number:{field}")
    return n

def _valid_date(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise ValueError("date_must_be_YYYY_MM_DD")

def _validate_source(row):
    if not row.get("source"):
        raise ValueError("missing:source")
    if not row.get("source_url", "").startswith(("https://", "http://")):
        raise ValueError("missing_or_invalid:source_url")
    if row.get("data_status") not in STATUSES:
        raise ValueError("data_status_must_be_one_of:" + ",".join(sorted(STATUSES)))
    if not row.get("as_of"):
        raise ValueError("missing:as_of")
    _valid_date(row["as_of"])

def normalize_financial_row(row):
    row = {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
    for field in ("symbol", "company", "period", "currency", "basis"):
        if not row.get(field):
            raise ValueError("missing:" + field)
    if not re.fullmatch(r"[A-Z0-9]{3,12}", row["symbol"].upper()):
        raise ValueError("invalid:symbol")
    row["symbol"] = row["symbol"].upper()
    if not re.fullmatch(r"[A-Z]{3}", row["currency"].upper()):
        raise ValueError("currency_must_be_3_letter_code")
    row["currency"] = row["currency"].upper()
    if not re.fullmatch(r"^\d{4}(-Q[1-4]|-\d{2}(-\d{2})?)?$", row["period"]):
        raise ValueError("period_must_be_YYYY_or_YYYY-Qn_or_YYYY-MM_or_YYYY-MM-DD")
    _validate_source(row)
    for field in FINANCIAL_NUMBERS:
        if field in row:
            row[field] = _number(row[field], field, allow_empty=True)
    row["ingested_at"] = datetime.now(timezone.utc).isoformat()
    return row

def normalize_price_row(row):
    row = {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
    for field in ("symbol", "date", "currency", "source", "source_url", "data_status", "as_of"):
        if not row.get(field):
            raise ValueError("missing:" + field)
    row["symbol"] = row["symbol"].upper()
    if not re.fullmatch(r"[A-Z0-9]{3,12}", row["symbol"]):
        raise ValueError("invalid:symbol")
    row["date"] = _valid_date(row["date"])
    row["currency"] = row["currency"].upper()
    if not re.fullmatch(r"[A-Z]{3}", row["currency"]):
        raise ValueError("currency_must_be_3_letter_code")
    _validate_source(row)
    for field in PRICE_NUMBERS:
        if field not in row:
            if field in ("adjusted_close", "turnover_egp"):
                continue
            raise ValueError("missing:" + field)
        row[field] = _number(row[field], field, allow_empty=(field in ("adjusted_close", "turnover_egp")))
    if min(row["open"], row["high"], row["low"], row["close"]) <= 0 or row["volume"] < 0:
        raise ValueError("prices_must_be_positive_and_volume_non_negative")
    if row["low"] > min(row["open"], row["close"]) or row["high"] < max(row["open"], row["close"]) or row["low"] > row["high"]:
        raise ValueError("inconsistent_ohlc_range")
    row["ingested_at"] = datetime.now(timezone.utc).isoformat()
    return row

def ingest_csv(input_path, output_path, kind):
    if kind not in ("financial", "prices"):
        raise ValueError("kind must be financial or prices")
    normalizer = normalize_financial_row if kind == "financial" else normalize_price_row
    accepted, rejected, seen = [], [], set()
    with open(input_path, newline="", encoding="utf-8-sig") as handle:
        for line_no, row in enumerate(csv.DictReader(handle), start=2):
            try:
                record = normalizer(row)
                key = ((record["symbol"], record["period"], record["basis"]) if kind == "financial"
                       else (record["symbol"], record["date"]))
                if key in seen:
                    raise ValueError("duplicate_record_in_input")
                seen.add(key)
                accepted.append(record)
            except Exception as exc:
                rejected.append({"line": line_no, "error": str(exc)})
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Replace atomically so a failed write never leaves a partial dataset.
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text("".join(json.dumps(item, ensure_ascii=False) + "\\n" for item in accepted), encoding="utf-8")
    temp.replace(output)
    return {"accepted": len(accepted), "rejected": rejected, "output": str(output)}

