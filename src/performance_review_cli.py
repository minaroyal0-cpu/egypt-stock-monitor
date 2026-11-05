"""CLI for provenance-checked stock-versus-benchmark event review.

Usage: python -m src.performance_review_cli PRICES.csv SYMBOL EVENT_DATE END_DATE
"""
import argparse
import json

from .performance_review import review_event_window_from_csv


def main():
    parser = argparse.ArgumentParser(
        description="Compare a stock and benchmark over shared, sourced trading dates."
    )
    parser.add_argument("prices_csv", help="Daily prices CSV with source metadata")
    parser.add_argument("symbol", help="Share ticker, e.g. ABUK")
    parser.add_argument("event_date", help="Window start, YYYY-MM-DD")
    parser.add_argument("end_date", help="Window end, YYYY-MM-DD")
    parser.add_argument("--benchmark", default="EGX30", help="Benchmark symbol (default: EGX30)")
    args = parser.parse_args()

    try:
        result = review_event_window_from_csv(
            args.prices_csv, args.symbol, args.event_date, args.end_date, args.benchmark
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
