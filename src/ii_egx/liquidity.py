"""Liquidity classification from user-supplied daily OHLCV CSV.

Required columns: symbol,date,close,volume. Optional: name,sector,value_egp.
If value_egp is absent, turnover is estimated as close * volume and explicitly
labelled as an estimate. No live market data is fetched by this module.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path


def _number(value: str, field: str) -> float:
    try:
        result = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ValueError(f"Invalid numeric value for {field}: {value!r}")
    if result < 0:
        raise ValueError(f"Negative value for {field}: {value!r}")
    return result


def load_rows(path: str | Path) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"symbol", "date", "close", "volume"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")
        for line, row in enumerate(reader, start=2):
            symbol = (row.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            day = date.fromisoformat((row.get("date") or "").strip())
            close = _number(row.get("close", ""), "close")
            volume = _number(row.get("volume", ""), "volume")
            raw_value = (row.get("value_egp") or "").strip()
            turnover = _number(raw_value, "value_egp") if raw_value else close * volume
            grouped[symbol].append({
                "symbol": symbol,
                "name": (row.get("name") or "").strip(),
                "sector": (row.get("sector") or "").strip(),
                "date": day.isoformat(),
                "close": close,
                "volume": volume,
                "turnover_egp": turnover,
                "turnover_basis": "reported_value_egp" if raw_value else "estimated_close_times_volume",
            })
    for symbol in grouped:
        grouped[symbol].sort(key=lambda item: item["date"])
    return grouped


def classify_liquidity(rows_by_symbol: dict[str, list[dict]]) -> list[dict]:
    """Rank by 20-session median turnover; thresholds are screening defaults, not EGX rules."""
    output = []
    for symbol, rows in rows_by_symbol.items():
        recent = rows[-20:]
        turnovers = [r["turnover_egp"] for r in recent]
        positive_days = sum(1 for r in recent if r["volume"] > 0)
        median_turnover = statistics.median(turnovers) if turnovers else 0.0
        average_turnover = statistics.mean(turnovers) if turnovers else 0.0
        # Transparent starter bands in EGP/day; configurable in a later release.
        if median_turnover >= 5_000_000:
            band, score = "مرتفع", 5
        elif median_turnover >= 1_000_000:
            band, score = "جيد", 4
        elif median_turnover >= 250_000:
            band, score = "متوسط", 3
        elif median_turnover >= 50_000:
            band, score = "منخفض", 2
        else:
            band, score = "ضعيف", 1
        latest = rows[-1] if rows else {}
        output.append({
            "symbol": symbol,
            "name": latest.get("name", ""),
            "sector": latest.get("sector", ""),
            "observations": len(recent),
            "latest_date": latest.get("date"),
            "median_daily_turnover_egp_20d": round(median_turnover, 2),
            "average_daily_turnover_egp_20d": round(average_turnover, 2),
            "traded_days_20d": positive_days,
            "traded_day_ratio_20d": round(positive_days / len(recent), 4) if recent else 0,
            "liquidity_band": band,
            "liquidity_score": score,
            "turnover_basis": latest.get("turnover_basis", "unknown"),
            "classification_note": "Indicative screening bands; not official EGX classifications.",
        })
    return sorted(output, key=lambda item: (
        item["liquidity_score"],
        item["median_daily_turnover_egp_20d"],
    ), reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify EGX stocks by daily liquidity")
    parser.add_argument("input_csv")
    parser.add_argument("output_json")
    args = parser.parse_args()
    result = classify_liquidity(load_rows(args.input_csv))
    Path(args.output_json).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Classified {len(result)} symbols -> {args.output_json}")


if __name__ == "__main__":
    main()
