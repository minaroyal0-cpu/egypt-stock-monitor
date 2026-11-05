"""Batch historical event studies from an event register and sourced prices CSV.

Event register columns: event_id,symbol,event_date. Optional columns:
benchmark,estimation_window,event_window_start,event_window_end.
Each output JSONL record is either an analysis result or a row-level error.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.event_study import load_shared_price_series, market_model_event_study

_REQUIRED_EVENTS = {"event_id", "symbol", "event_date"}
_DEFAULTS = {
    "benchmark": "EGX30",
    "estimation_window": 60,
    "event_window_start": -1,
    "event_window_end": 1,
}


def _integer(value: str, field: str, default: int) -> int:
    if value is None or not str(value).strip():
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid_{field}") from None


def run_batch(events_csv: str, prices_csv: str) -> list[dict]:
    """Run each event independently; preserve row-level failures in the output."""
    with open(events_csv, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not _REQUIRED_EVENTS.issubset(reader.fieldnames):
            raise ValueError("missing_required_event_columns")
        events = list(reader)

    seen_ids: set[str] = set()
    price_cache: dict[tuple[str, str], dict] = {}
    output: list[dict] = []
    for row_number, event in enumerate(events, start=2):
        event_id = str(event.get("event_id") or "").strip()
        symbol = str(event.get("symbol") or "").strip().upper()
        event_date = str(event.get("event_date") or "").strip()
        try:
            if not event_id:
                raise ValueError("missing_event_id")
            if event_id in seen_ids:
                raise ValueError("duplicate_event_id")
            seen_ids.add(event_id)
            if not symbol or not event_date:
                raise ValueError("missing_symbol_or_event_date")

            benchmark = str(event.get("benchmark") or _DEFAULTS["benchmark"]).strip().upper()
            estimation = _integer(
                event.get("estimation_window"), "estimation_window",
                _DEFAULTS["estimation_window"],
            )
            window_start = _integer(
                event.get("event_window_start"), "event_window_start",
                _DEFAULTS["event_window_start"],
            )
            window_end = _integer(
                event.get("event_window_end"), "event_window_end",
                _DEFAULTS["event_window_end"],
            )
            cache_key = (symbol, benchmark)
            if cache_key not in price_cache:
                price_cache[cache_key] = load_shared_price_series(
                    prices_csv, symbol, benchmark
                )
            loaded = price_cache[cache_key]
            result = market_model_event_study(
                loaded["dates"], loaded["prices"][symbol],
                loaded["prices"][benchmark], event_date,
                estimation, window_start, window_end, symbol, benchmark,
            )
            result["event_id"] = event_id
            result["price_data_provenance"] = {
                ticker: {
                    "first_shared_date": loaded["dates"][0],
                    "last_shared_date": loaded["dates"][-1],
                    "shared_observations": len(loaded["dates"]),
                    "source_status_is_not_independently_verified": True,
                }
                for ticker in (symbol, benchmark)
            }
            output.append({"status": "ok", **result})
        except (ValueError, OSError, KeyError) as exc:
            output.append({
                "status": "error",
                "event_id": event_id or None,
                "row_number": row_number,
                "symbol": symbol or None,
                "event_date": event_date or None,
                "error": str(exc),
            })
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run market-model event studies for multiple historical news events."
    )
    parser.add_argument("--events", required=True, help="CSV event register")
    parser.add_argument("--prices", required=True, help="CSV with sourced stock and benchmark closes")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    args = parser.parse_args(argv)

    results = run_batch(args.events, args.prices)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")

    succeeded = sum(item["status"] == "ok" for item in results)
    failed = len(results) - succeeded
    print(f"Event studies complete: {succeeded} succeeded, {failed} failed; output={output_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
