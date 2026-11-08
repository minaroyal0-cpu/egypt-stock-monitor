"""Build a simple Markdown research report from sourced CSV imports."""
from __future__ import annotations
import argparse, csv
from pathlib import Path
from .liquidity import classify_liquidity, load_rows
from .fundamentals import analyze_row

def build_report(prices_csv: str, fundamentals_csv: str | None, output_md: str) -> None:
    liquidity = classify_liquidity(load_rows(prices_csv))
    fundamentals = {}
    if fundamentals_csv:
        with open(fundamentals_csv, newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                item = analyze_row(row)
                fundamentals[item["symbol"]] = item
    lines = [
        "# EGX Investment Intelligence — Research Snapshot", "",
        "> Research support only. Not a buy/sell recommendation. Verify source documents and prices.", "",
        f"- Symbols ranked by liquidity: **{len(liquidity)}**",
        "- Liquidity window: last 20 supplied observations per symbol.",
        "- Turnover uses reported value_egp where present; otherwise close × volume estimate.",
        "- Classification bands are internal screening thresholds, not official EGX categories.", "",
        "## Liquidity ranking", "",
        "| Rank | Symbol | Name | Sector | Median daily turnover (EGP) | Traded days | Band |",
        "|---:|---|---|---|---:|---:|---|",
    ]
    for rank, item in enumerate(liquidity, 1):
        lines.append(f"| {rank} | {item['symbol']} | {item['name']} | {item['sector']} | {item['median_daily_turnover_egp_20d']:,.2f} | {item['traded_days_20d']}/{item['observations']} | {item['liquidity_band']} |")
    lines += ["", "## Financial ratios", ""]
    if not fundamentals:
        lines.append("No fundamentals CSV supplied. No financial ratios calculated.")
    else:
        lines += ["| Symbol | As of | Operating margin | Net margin | ROE* | Debt/equity | Current ratio | FCF (EGP) |",
                  "|---|---|---:|---:|---:|---:|---:|---:|"]
        def fmt(value):
            return "n/a" if value is None else f"{value:.2%}" if abs(value) <= 1 else f"{value:.2f}"
        for symbol, item in sorted(fundamentals.items()):
            lines.append(f"| {symbol} | {item['as_of']} | {fmt(item['operating_margin'])} | {fmt(item['net_margin'])} | {fmt(item['roe'])} | {fmt(item['debt_to_equity'])} | {fmt(item['current_ratio'])} | {fmt(item['free_cash_flow_egp'])} |")
    lines += ["", "* ROE uses period-end equity, not average equity. Bank and insurer ratios need sector-specific interpretation.", "",
              "## Data-quality checklist", "",
              "- Confirm every symbol against the current official EGX instrument list.",
              "- Check dates, corporate actions, suspensions and currency.",
              "- Prefer official reported turnover; estimated close × volume may omit market-specific details.",
              "- Match financial periods and consolidated/standalone statements.",
              "- Treat missing values as unknown, never as zero.", ""]
    Path(output_md).write_text("\n".join(lines), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prices_csv")
    parser.add_argument("output_md")
    parser.add_argument("--fundamentals-csv")
    args = parser.parse_args()
    build_report(args.prices_csv, args.fundamentals_csv, args.output_md)
    print(f"Report written to {args.output_md}")

if __name__ == "__main__":
    main()
