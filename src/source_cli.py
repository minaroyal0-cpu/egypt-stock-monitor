"""Print the EGX source registry and current integration readiness."""
import argparse
import json

from src.source_registry import classify_source_url, readiness_report


def main():
    parser = argparse.ArgumentParser(description="Inspect EGX data-source readiness.")
    parser.add_argument("--check-url", help="Classify a source URL against the registry.")
    args = parser.parse_args()
    result = classify_source_url(args.check_url) if args.check_url else readiness_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
