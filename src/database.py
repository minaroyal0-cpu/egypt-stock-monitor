"""Append-only SQLite storage for sourced EGX observations.

Observations are never overwritten by later imports. Re-importing the same
source record is idempotent; best-record views rank provenance explicitly.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

STATUS_PRIORITY = {"official": 4, "third_party": 3, "user_supplied": 2, "estimate": 1}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS financial_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    basis TEXT NOT NULL,
    currency TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    data_status TEXT NOT NULL,
    as_of TEXT NOT NULL,
    record_hash TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_financial_lookup
ON financial_observations(symbol, period, basis, currency);
CREATE TABLE IF NOT EXISTS price_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    currency TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    data_status TEXT NOT NULL,
    as_of TEXT NOT NULL,
    record_hash TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prices_lookup
ON price_observations(symbol, date, currency);
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    input_name TEXT NOT NULL,
    accepted INTEGER NOT NULL,
    rejected INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""

def connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn

def _hash(record):
    stable = {k: v for k, v in record.items() if k not in ("ingested_at",)}
    raw = json.dumps(stable, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def store_records(db_path, kind, records, input_name="manual"):
    if kind not in ("financial", "prices"):
        raise ValueError("kind must be financial or prices")
    table = "financial_observations" if kind == "financial" else "price_observations"
    inserted = 0
    with connect(db_path) as conn:
        for record in records:
            digest = _hash(record)
            payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
            cursor = conn.execute(
                f"""INSERT OR IGNORE INTO {table}
                (symbol, { 'period, basis' if kind == 'financial' else 'date' },
                 currency, source, source_url, data_status, as_of,
                 record_hash, payload_json, ingested_at)
                VALUES ({','.join(['?'] * (11 if kind == 'financial' else 10))})""",
                (
                    record["symbol"],
                    *((record["period"], record["basis"]) if kind == "financial" else (record["date"],)),
                    record["currency"], record["source"], record["source_url"],
                    record["data_status"], record["as_of"], digest, payload,
                    record.get("ingested_at") or datetime.now(timezone.utc).isoformat()
                )
            )
            inserted += cursor.rowcount
    return {"inserted": inserted, "duplicates": len(records) - inserted}

def get_best_financial(db_path, symbol, period, basis, currency=None):
    query = """SELECT payload_json FROM financial_observations
               WHERE symbol=? AND period=? AND basis=?"""
    args = [symbol.upper(), period, basis]
    if currency:
        query += " AND currency=?"
        args.append(currency.upper())
    query += """ ORDER BY CASE data_status
                 WHEN 'official' THEN 4 WHEN 'third_party' THEN 3
                 WHEN 'user_supplied' THEN 2 WHEN 'estimate' THEN 1 ELSE 0 END DESC,
                 as_of DESC, id DESC LIMIT 1"""
    with connect(db_path) as conn:
        row = conn.execute(query, args).fetchone()
    return json.loads(row["payload_json"]) if row else None

def get_price_history(db_path, symbol, start_date=None, end_date=None, currency=None):
    query = "SELECT * FROM price_observations WHERE symbol=?"
    args = [symbol.upper()]
    if start_date:
        query += " AND date>=?"
        args.append(start_date)
    if end_date:
        query += " AND date<=?"
        args.append(end_date)
    if currency:
        query += " AND currency=?"
        args.append(currency.upper())
    query += """ ORDER BY date ASC,
        CASE data_status WHEN 'official' THEN 4 WHEN 'third_party' THEN 3
        WHEN 'user_supplied' THEN 2 WHEN 'estimate' THEN 1 ELSE 0 END DESC,
        as_of DESC, id DESC"""
    with connect(db_path) as conn:
        rows = conn.execute(query, args).fetchall()
    # Return one highest-priority observation per trading day, without
    # deleting or overwriting lower-priority source observations.
    chosen = {}
    for row in rows:
        chosen.setdefault(row["date"], json.loads(row["payload_json"]))
    return [chosen[key] for key in sorted(chosen)]

def record_ingestion_result(db_path, kind, input_name, accepted, rejected):
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO ingestion_runs(kind,input_name,accepted,rejected,created_at) VALUES(?,?,?,?,?)",
            (kind, str(input_name), accepted, rejected, datetime.now(timezone.utc).isoformat())
        )

def database_summary(db_path):
    with connect(db_path) as conn:
        return {
            "financial_observations": conn.execute("SELECT COUNT(*) FROM financial_observations").fetchone()[0],
            "price_observations": conn.execute("SELECT COUNT(*) FROM price_observations").fetchone()[0],
            "ingestion_runs": conn.execute("SELECT COUNT(*) FROM ingestion_runs").fetchone()[0],
        }
