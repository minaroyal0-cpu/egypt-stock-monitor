"""Run an educational SMA crossover backtest on sourced SQLite prices."""
import argparse
import json

from .backtest import moving_average_backtest
from .database import get_adjusted_price_history


def main():
    parser = argparse.ArgumentParser(description="Historical, cost-aware educational backtest")
    parser.add_argument("symbol")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--currency")
    parser.add_argument("--db", default="data/egx_history.sqlite3")
    parser.add_argument("--cash", type=float, default=100000.0)
    parser.add_argument("--fast", type=int, default=10)
    parser.add_argument("--slow", type=int, default=30)
    parser.add_argument("--commission", type=float, default=0.001,
                        help="commission fraction per side; default 0.001 = 0.10%%")
    parser.add_argument("--slippage", type=float, default=0.001,
                        help="adverse slippage fraction per side; default 0.001 = 0.10%%")
    args = parser.parse_args()
    bars = get_adjusted_price_history(args.db, args.symbol, args.start, args.end, args.currency)
    currencies = {bar["currency"] for bar in bars}
    if len(currencies) > 1:
        raise SystemExit("Multiple currencies found; specify --currency to avoid mixing series.")
    if not bars:
        raise SystemExit("No sourced price history found for the requested symbol and period.")
    result = moving_average_backtest(
        bars, initial_cash=args.cash, fast_window=args.fast, slow_window=args.slow,
        commission_rate=args.commission, slippage_rate=args.slippage,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
