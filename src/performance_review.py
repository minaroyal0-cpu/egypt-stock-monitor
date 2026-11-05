"""Backward-looking event-window calculations from explicitly sourced prices.

This module does not fetch prices, infer causality, or generate trade signals.
"""
from __future__ import annotations

from datetime import date
from math import isfinite
import csv


def _positive_finite_price(value: float) -> float:
    price = float(value)
    if not isfinite(price) or price <= 0:
        raise ValueError("Prices must be finite numbers greater than zero.")
    return price


def percentage_return(start_price: float, end_price: float) -> float:
    """Return simple price change as a percentage."""
    start = _positive_finite_price(start_price)
    end = _positive_finite_price(end_price)
    return ((end / start) - 1.0) * 100.0


def _iso_date(value: str, field_name: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid ISO date (YYYY-MM-DD).") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.")
    return parsed


def review_event_window(
    symbol: str,
    event_date: str,
    end_date: str,
    start_price: float,
    end_price: float,
    benchmark_start: float,
    benchmark_end: float,
    benchmark_symbol: str = "EGX30",
) -> dict:
    """Compare share and benchmark simple returns over the same supplied window."""
    clean_symbol = str(symbol or "").strip().upper()
    clean_benchmark = str(benchmark_symbol or "").strip().upper()
    if not clean_symbol or not clean_benchmark:
        raise ValueError("Symbol and benchmark_symbol are required.")

    start_day = _iso_date(event_date, "event_date")
    end_day = _iso_date(end_date, "end_date")
    if end_day <= start_day:
        raise ValueError("end_date must be later than event_date.")

    stock_return = percentage_return(start_price, end_price)
    benchmark_return = percentage_return(benchmark_start, benchmark_end)
    return {
        "symbol": clean_symbol,
        "benchmark_symbol": clean_benchmark,
        "event_date": event_date,
        "end_date": end_date,
        "window_calendar_days": (end_day - start_day).days,
        "stock_return_pct": round(stock_return, 4),
        "benchmark_return_pct": round(benchmark_return, 4),
        "relative_return_pct_points": round(stock_return - benchmark_return, 4),
        "method": "simple_stock_return_minus_simple_benchmark_return",
        "interpretation": (
            "وصف تاريخي للفترة فقط؛ لا يثبت أن الخبر سبب الحركة، "
            "ولا يراعي التوزيعات أو السيولة أو اختلاف المخاطر."
        ),
        "source_prices_required": True,
    }

def review_event_window_from_csv(
    csv_path: str,
    symbol: str,
    event_date: str,
    end_date: str,
    benchmark_symbol: str = "EGX30",
) -> dict:
    """Review two instruments using shared trading dates in a provenance-labelled CSV."""
    import re

    start_day = _iso_date(event_date, "event_date")
    end_day = _iso_date(end_date, "end_date")
    if end_day <= start_day:
        raise ValueError("end_date must be later than event_date.")

    target = str(symbol or "").strip().upper()
    benchmark = str(benchmark_symbol or "").strip().upper()
    if not target or not benchmark or target == benchmark:
        raise ValueError("Provide two different, non-empty instrument symbols.")

    series = {target: {}, benchmark: {}}
    provenance = {target: {}, benchmark: {}}
    required = {"symbol", "date", "close", "source", "source_url", "data_status", "as_of"}
    allowed_status = {"official", "third_party", "user_supplied"}
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("CSV is missing required price or provenance columns.")
        for line_no, row in enumerate(reader, start=2):
            row_symbol = str(row.get("symbol") or "").strip().upper()
            if row_symbol not in series:
                continue
            day_text = str(row.get("date") or "").strip()
            day = _iso_date(day_text, f"line_{line_no}_date")
            if not (start_day <= day <= end_day):
                continue
            if day_text in series[row_symbol]:
                raise ValueError(f"duplicate_price:{row_symbol}:{day_text}")
            if not row.get("source", "").strip():
                raise ValueError(f"missing_source:line_{line_no}")
            if not re.match(r"^https://", row.get("source_url", "").strip(), re.I):
                raise ValueError(f"invalid_source_url:line_{line_no}")
            if row.get("data_status", "").strip() not in allowed_status:
                raise ValueError(f"invalid_data_status:line_{line_no}")
            _iso_date(str(row.get("as_of") or "").strip(), f"line_{line_no}_as_of")
            series[row_symbol][day_text] = _positive_finite_price(row.get("close"))
            provenance[row_symbol][day_text] = {
                "source": row["source"].strip(),
                "source_url": row["source_url"].strip(),
                "data_status": row["data_status"].strip(),
            }

    common_days = sorted(set(series[target]) & set(series[benchmark]))
    if len(common_days) < 2:
        raise ValueError("At least two shared trading dates are required for both instruments.")
    first_day, last_day = common_days[0], common_days[-1]
    result = review_event_window(
        target, first_day, last_day,
        series[target][first_day], series[target][last_day],
        series[benchmark][first_day], series[benchmark][last_day],
        benchmark,
    )
    result.update({
        "requested_event_date": event_date,
        "requested_end_date": end_date,
        "actual_start_date": first_day,
        "actual_end_date": last_day,
        "shared_trading_days": len(common_days),
        "stock_price_provenance_start": provenance[target][first_day],
        "stock_price_provenance_end": provenance[target][last_day],
        "benchmark_price_provenance_start": provenance[benchmark][first_day],
        "benchmark_price_provenance_end": provenance[benchmark][last_day],
    })
    return result
