# Historical SQLite database

## Why this stage exists
The CSV importer currently emits validated JSONL files. This stage adds a local,
dependency-free SQLite history store. It does not fetch market data or create
sample prices/fundamentals.

## Commands
Initialize:
```bash
python -m src.db_cli init
```

Import financial statements:
```bash
python -m src.db_cli import financial data/your_financials.csv
```

Import daily OHLCV:
```bash
python -m src.db_cli import prices data/your_prices.csv
```

Show counts:
```bash
python -m src.db_cli summary
```

Use `--db path/to/file.sqlite3` to choose another database path.

## Storage and source policy
- Financial and price observations are append-only. Imports do not overwrite previous source observations.
- Re-importing an identical record is idempotent and does not create a duplicate.
- The same period/day may retain observations from multiple sources.
- Best-record reads rank `official > third_party > user_supplied > estimate`, then use the newest `as_of` date within the same status.
- Price history returns one best-ranked observation per trading day while preserving all alternatives in storage.
- Every stored record retains its source name, exact source URL, data status, as-of date, currency, and original normalized fields.
- The database is a local working artifact and is not committed with market data. Do not store brokerage credentials, account identifiers, or private holdings data in it.

## Important limitations
No source adapter or live EGX/FRA/EGID connection is enabled. A database is only a durable store;
it does not make the input data accurate. Verify source documents, reporting basis,
corporate actions, and licensing before analysis. Do not calculate adjusted long-run
returns until corporate actions have been normalized consistently.
