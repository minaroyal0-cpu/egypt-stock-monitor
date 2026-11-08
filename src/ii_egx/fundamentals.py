"""Transparent financial-ratio calculations from sourced statement CSV rows.

Expected numeric columns: revenue, operating_profit, net_income, total_assets,
total_equity, total_debt, cash, current_assets, current_liabilities,
operating_cash_flow, capex. symbol, as_of, source_name, source_url are required.
Blank metrics remain null; ratios are never fabricated.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def num(row: dict, key: str):
    raw = (row.get(key) or "").strip().replace(",", "")
    if raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"Invalid {key}: {raw!r}")


def safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 4)


def analyze_row(row: dict) -> dict:
    required = ("symbol", "as_of", "source_name", "source_url")
    missing = [key for key in required if not (row.get(key) or "").strip()]
    if missing:
        raise ValueError(f"Missing provenance fields: {', '.join(missing)}")
    values = {key: num(row, key) for key in (
        "revenue", "operating_profit", "net_income", "total_assets",
        "total_equity", "total_debt", "cash", "current_assets",
        "current_liabilities", "operating_cash_flow", "capex"
    )}
    revenue, op, ni = values["revenue"], values["operating_profit"], values["net_income"]
    fcf = None
    if values["operating_cash_flow"] is not None and values["capex"] is not None:
        fcf = round(values["operating_cash_flow"] - values["capex"], 2)
    return {
        "symbol": row["symbol"].strip().upper(),
        "as_of": row["as_of"].strip(),
        "source_name": row["source_name"].strip(),
        "source_url": row["source_url"].strip(),
        "revenue_egp": revenue,
        "operating_margin": safe_div(op, revenue),
        "net_margin": safe_div(ni, revenue),
        "roe": safe_div(ni, values["total_equity"]),
        "roa": safe_div(ni, values["total_assets"]),
        "debt_to_equity": safe_div(values["total_debt"], values["total_equity"]),
        "current_ratio": safe_div(values["current_assets"], values["current_liabilities"]),
        "free_cash_flow_egp": fcf,
        "cash_egp": values["cash"],
        "operating_cash_flow_egp": values["operating_cash_flow"],
        "data_status": "user_supplied_source_not_independently_verified",
        "limitations": [
            "Ratios depend on the accounting period and statement type supplied.",
            "ROE/ROA use supplied period-end balances, not average balances.",
            "Capex should be entered as a positive cash outflow.",
            "Bank and insurance companies need sector-specific metrics.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate transparent EGX financial ratios")
    parser.add_argument("input_csv")
    parser.add_argument("output_jsonl")
    args = parser.parse_args()
    count = 0
    with open(args.input_csv, newline="", encoding="utf-8-sig") as src, open(
        args.output_jsonl, "w", encoding="utf-8"
    ) as dst:
        for row in csv.DictReader(src):
            dst.write(json.dumps(analyze_row(row), ensure_ascii=False) + "\n")
            count += 1
    print(f"Analyzed {count} statement rows -> {args.output_jsonl}")


if __name__ == "__main__":
    main()
