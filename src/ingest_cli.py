"""Command line: python -m src.ingest_cli financial input.csv output.jsonl"""
import argparse
import json
from .ingestion import ingest_csv

def main():
    parser = argparse.ArgumentParser(description="Validate and ingest sourced EGX CSV data")
    parser.add_argument("kind", choices=("financial", "prices"))
    parser.add_argument("input_csv")
    parser.add_argument("output_jsonl")
    args = parser.parse_args()
    result = ingest_csv(args.input_csv, args.output_jsonl, args.kind)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["rejected"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
