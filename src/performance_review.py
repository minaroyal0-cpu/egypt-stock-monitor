"""Backward-looking event-window calculations from explicitly sourced prices.

This module does not fetch prices, infer causality, or generate trade signals.
"""
from __future__ import annotations

from datetime import date
from math import isfinite


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
