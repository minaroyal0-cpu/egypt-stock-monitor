"""Read a small EGID delayed-feed endpoint with an authorized bearer token."""
import argparse
import json

from src.egid_client import ALLOWED_PATHS, fetch_delayed_feed


def main():
    parser = argparse.ArgumentParser(description="Fetch an authorized EGID delayed feed.")
    parser.add_argument("--endpoint", choices=sorted(ALLOWED_PATHS), required=True)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    print(json.dumps(
        fetch_delayed_feed(args.endpoint, timeout=args.timeout),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
