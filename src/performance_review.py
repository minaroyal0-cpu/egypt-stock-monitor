"""Backward-looking event-window calculations from explicitly sourced prices.

This module does not fetch prices, infer causality, or generate trade signals.
"""
from __future__ import annotations


def percentage_return(start_price: float, end_price: float) -> float:
    """Return simple price change as a percentage."""
    start = float(start_price)
    end = float(end_price)
    if start <= 0 or end <= 0:
        raise ValueError("Prices must be greater than zero.")
    return ((end / start) - 1.0) * 100.0


def review_event_window(
    symbol: str,
    event_date: str,
    end_date: str,
    start_price: float,
    end_price: float,
    benchmark_start: float,
    benchmark_end: float,
) -> dict:
    """Compare a share's observed return with a benchmark over the same window."""
    if not symbol or not event_date or not end_date:
        raise ValueError("Symbol, event_date and end_date are required.")
    stock_return = percentage_return(start_price, end_price)
    benchmark_return = percentage_return(benchmark_start, benchmark_end)
    return {
        "symbol": symbol.strip().upper(),
        "event_date": event_date,
        "end_date": end_date,
        "stock_return_pct": round(stock_return, 4),
        "benchmark_return_pct": round(benchmark_return, 4),
        "relative_return_pct_points": round(stock_return - benchmark_return, 4),
        "method": "price_change_minus_benchmark_change",
        "interpretation": (
            "وصف تاريخي للفترة فقط؛ لا يثبت أن الخبر سبب الحركة، "
            "ولا يراعي التوزيعات أو السيولة أو اختلاف المخاطر."
        ),
        "source_prices_required": True,
    }
