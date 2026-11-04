"""Fetch one free Borsa demo quote and persist it as a quote snapshot.

Usage: python -m src.borsa_cli COMI --db data/egx.sqlite
"""
import argparse
import json
from .borsa_client import fetch_quote
from .database import store_quote_snapshot


def main():
    parser=argparse.ArgumentParser(description="Fetch a third-party EGX demo quote")
    parser.add_argument("symbol")
    parser.add_argument("--db",default="data/egx.sqlite")
    args=parser.parse_args()
    quote=fetch_quote(args.symbol)
    stored=store_quote_snapshot(args.db,quote)
    print(json.dumps({"quote":quote,"storage":stored},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
