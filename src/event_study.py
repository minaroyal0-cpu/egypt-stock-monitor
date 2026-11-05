"""Market-model event study using shared, explicitly sourced daily close prices.

This is a descriptive research tool, not a causal test or trading signal.
"""
from __future__ import annotations

import csv
from datetime import date
from math import isfinite
from urllib.parse import urlsplit

_REQUIRED = {"symbol", "date", "close", "source", "source_url", "data_status", "as_of"}
_ALLOWED_STATUS = {"official", "third_party", "user_supplied"}


def _day(value: str) -> date:
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValueError(f"invalid_date:{value}") from None
    if parsed.isoformat() != value:
        raise ValueError(f"invalid_date:{value}")
    return parsed


def _price(value: str, row_number: int) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid_close:row_{row_number}") from None
    if not isfinite(number) or number <= 0:
        raise ValueError(f"invalid_close:row_{row_number}")
    return number


def _validate_source(row: dict, row_number: int) -> dict:
    source = str(row.get("source") or "").strip()
    url = str(row.get("source_url") or "").strip()
    status = str(row.get("data_status") or "").strip()
    as_of = str(row.get("as_of") or "").strip()
    try:
        parsed = urlsplit(url)
        valid_url = parsed.scheme.lower() == "https" and bool(parsed.hostname)
    except ValueError:
        valid_url = False
    if not source:
        raise ValueError(f"missing_source:row_{row_number}")
    if not valid_url:
        raise ValueError(f"invalid_source_url:row_{row_number}")
    if status not in _ALLOWED_STATUS:
        raise ValueError(f"invalid_data_status:row_{row_number}")
    _day(as_of)
    return {
        "source": source,
        "source_url": url,
        "data_status": status,
        "as_of": as_of,
        "status_is_source_assertion_not_independent_verification": True,
    }


def load_shared_price_series(csv_path: str, symbol: str, benchmark: str = "EGX30") -> dict:
    """Load close prices on shared dates; preserve provenance for each observation."""
    symbol, benchmark = symbol.strip().upper(), benchmark.strip().upper()
    if not symbol or not benchmark or symbol == benchmark:
        raise ValueError("two different non-empty symbols are required")
    prices = {symbol: {}, benchmark: {}}
    provenance = {symbol: {}, benchmark: {}}
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not _REQUIRED.issubset(reader.fieldnames):
            raise ValueError("missing_required_csv_columns")
        for row_number, row in enumerate(reader, start=2):
            ticker = str(row.get("symbol") or "").strip().upper()
            if ticker not in prices:
                continue
            day_text = str(row.get("date") or "").strip()
            _day(day_text)
            if day_text in prices[ticker]:
                raise ValueError(f"duplicate_observation:{ticker}:{day_text}")
            prices[ticker][day_text] = _price(row.get("close"), row_number)
            provenance[ticker][day_text] = _validate_source(row, row_number)

    shared_dates = sorted(set(prices[symbol]) & set(prices[benchmark]))
    if len(shared_dates) < 3:
        raise ValueError("at_least_three_shared_trading_dates_required")
    return {
        "dates": shared_dates,
        "prices": {
            ticker: [prices[ticker][day] for day in shared_dates]
            for ticker in (symbol, benchmark)
        },
        "provenance": provenance,
        "symbol": symbol,
        "benchmark": benchmark,
    }


def market_model_event_study(
    dates: list[str],
    stock_closes: list[float],
    benchmark_closes: list[float],
    event_date: str,
    estimation_window: int = 60,
    event_window_start: int = -1,
    event_window_end: int = 1,
    symbol: str = "STOCK",
    benchmark_symbol: str = "EGX30",
) -> dict:
    """Estimate OLS market model on pre-event daily returns and report AR/CAR.

    Event-window offsets are trading sessions relative to the event-date close.
    Offset 0 is the return ending on event_date.
    """
    if estimation_window < 3:
        raise ValueError("estimation_window_must_be_at_least_3")
    if event_window_start > event_window_end or event_window_end < 0:
        raise ValueError("invalid_event_window_offsets")
    if not (len(dates) == len(stock_closes) == len(benchmark_closes)):
        raise ValueError("dates_and_price_series_must_have_equal_lengths")
    if len(set(dates)) != len(dates) or dates != sorted(dates):
        raise ValueError("dates_must_be_unique_and_ascending")
    for item in dates:
        _day(item)
    stock = [_price(value, i + 1) for i, value in enumerate(stock_closes)]
    market = [_price(value, i + 1) for i, value in enumerate(benchmark_closes)]
    try:
        event_index = dates.index(event_date)
    except ValueError:
        raise ValueError("event_date_not_found_in_shared_trading_dates") from None

    # Daily simple returns indexed by the session on which the return ends.
    stock_returns = [None] + [
        (stock[i] / stock[i - 1] - 1.0) * 100.0 for i in range(1, len(stock))
    ]
    market_returns = [None] + [
        (market[i] / market[i - 1] - 1.0) * 100.0 for i in range(1, len(market))
    ]
    estimation_indices = list(range(event_index - estimation_window, event_index))
    if not estimation_indices or estimation_indices[0] < 1:
        raise ValueError("insufficient_pre_event_estimation_observations")

    xs = [market_returns[i] for i in estimation_indices]
    ys = [stock_returns[i] for i in estimation_indices]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    variance_x = sum((x - mean_x) ** 2 for x in xs)
    if variance_x <= 1e-15:
        raise ValueError("benchmark_estimation_returns_have_zero_variance")
    beta = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / variance_x
    alpha = mean_y - beta * mean_x

    event_indices = list(range(event_index + event_window_start, event_index + event_window_end + 1))
    if not event_indices or event_indices[0] < 1 or event_indices[-1] >= len(dates):
        raise ValueError("event_window_outside_available_shared_prices")

    rows = []
    for index in event_indices:
        expected = alpha + beta * market_returns[index]
        abnormal = stock_returns[index] - expected
        rows.append({
            "trading_session_offset": index - event_index,
            "date": dates[index],
            "stock_return_pct": round(stock_returns[index], 6),
            "benchmark_return_pct": round(market_returns[index], 6),
            "expected_stock_return_pct": round(expected, 6),
            "abnormal_return_pct_points": round(abnormal, 6),
        })

    car = sum(row["abnormal_return_pct_points"] for row in rows)
    return {
        "symbol": symbol.strip().upper(),
        "benchmark_symbol": benchmark_symbol.strip().upper(),
        "event_date": event_date,
        "estimation_observations": len(estimation_indices),
        "estimation_window_start": dates[estimation_indices[0]],
        "estimation_window_end": dates[estimation_indices[-1]],
        "event_window_start_offset": event_window_start,
        "event_window_end_offset": event_window_end,
        "market_model_alpha_daily_pct": round(alpha, 8),
        "market_model_beta": round(beta, 8),
        "abnormal_returns": rows,
        "cumulative_abnormal_return_pct_points": round(car, 6),
        "method": "OLS market model on pre-event daily simple returns",
        "limitations": [
            "تحليل تاريخي وصفي ولا يثبت أن الخبر سبب حركة السهم.",
            "النتيجة حساسة لاختيار نافذة التقدير والمؤشر والفترة.",
            "لا يعالج التوزيعات أو الأحداث المتزامنة أو تغيرات السيولة والمخاطر.",
            "بيانات المصدر ووسم حالتها مدخلات يعلنها المصدر وليست تحققاً مستقلاً.",
            "لا ينتج توصية شراء أو بيع.",
        ],
    }


def event_study_from_csv(
    csv_path: str,
    symbol: str,
    event_date: str,
    benchmark: str = "EGX30",
    estimation_window: int = 60,
    event_window_start: int = -1,
    event_window_end: int = 1,
) -> dict:
    loaded = load_shared_price_series(csv_path, symbol, benchmark)
    result = market_model_event_study(
        loaded["dates"], loaded["prices"][loaded["symbol"]],
        loaded["prices"][loaded["benchmark"]], event_date,
        estimation_window, event_window_start, event_window_end,
        loaded["symbol"], loaded["benchmark"],
    )
    result["price_data_provenance"] = {
        ticker: {
            "first_shared_date": loaded["dates"][0],
            "last_shared_date": loaded["dates"][-1],
            "shared_observations": len(loaded["dates"]),
            "source_status_is_not_independently_verified": True,
        }
        for ticker in (loaded["symbol"], loaded["benchmark"])
    }
    return result
