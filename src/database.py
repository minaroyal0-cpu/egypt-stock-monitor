"""Append-only SQLite storage for sourced EGX observations and corporate actions."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS financial_observations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, period TEXT NOT NULL,
 basis TEXT NOT NULL, currency TEXT NOT NULL, source TEXT NOT NULL, source_url TEXT NOT NULL,
 data_status TEXT NOT NULL, as_of TEXT NOT NULL, record_hash TEXT NOT NULL UNIQUE,
 payload_json TEXT NOT NULL, ingested_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_financial_lookup ON financial_observations(symbol,period,basis,currency);
CREATE TABLE IF NOT EXISTS price_observations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, date TEXT NOT NULL,
 currency TEXT NOT NULL, source TEXT NOT NULL, source_url TEXT NOT NULL, data_status TEXT NOT NULL,
 as_of TEXT NOT NULL, record_hash TEXT NOT NULL UNIQUE, payload_json TEXT NOT NULL, ingested_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_prices_lookup ON price_observations(symbol,date,currency);
CREATE TABLE IF NOT EXISTS corporate_actions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, ex_date TEXT NOT NULL,
 currency TEXT NOT NULL, action_type TEXT NOT NULL, source TEXT NOT NULL, source_url TEXT NOT NULL,
 data_status TEXT NOT NULL, as_of TEXT NOT NULL, record_hash TEXT NOT NULL UNIQUE,
 payload_json TEXT NOT NULL, ingested_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_actions_lookup ON corporate_actions(symbol,ex_date,currency);
CREATE TABLE IF NOT EXISTS ingestion_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, input_name TEXT NOT NULL,
 accepted INTEGER NOT NULL, rejected INTEGER NOT NULL, created_at TEXT NOT NULL);
"""

def connect(db_path):
    path=Path(db_path); path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(str(path)); conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL"); conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA); return conn

def _hash(record):
    stable={k:v for k,v in record.items() if k!="ingested_at"}
    raw=json.dumps(stable,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def store_records(db_path,kind,records,input_name="manual"):
    tables={"financial":("financial_observations",("symbol","period","basis","currency","source","source_url","data_status","as_of")),
            "prices":("price_observations",("symbol","date","currency","source","source_url","data_status","as_of")),
            "actions":("corporate_actions",("symbol","ex_date","currency","action_type","source","source_url","data_status","as_of"))}
    if kind not in tables: raise ValueError("kind must be financial, prices, or actions")
    table,keys=tables[kind]; inserted=0
    with connect(db_path) as conn:
        for record in records:
            digest=_hash(record); payload=json.dumps(record,ensure_ascii=False,sort_keys=True)
            columns=keys+("record_hash","payload_json","ingested_at")
            values=[record[k] for k in keys]+[digest,payload,record.get("ingested_at") or datetime.now(timezone.utc).isoformat()]
            sql=f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({','.join(['?']*len(columns))})"
            inserted += conn.execute(sql,values).rowcount
    return {"inserted":inserted,"duplicates":len(records)-inserted}

def get_best_financial(db_path,symbol,period,basis,currency=None):
    q="""SELECT payload_json FROM financial_observations WHERE symbol=? AND period=? AND basis=?"""
    args=[symbol.upper(),period,basis]
    if currency: q+=" AND currency=?"; args.append(currency.upper())
    q+=""" ORDER BY CASE data_status WHEN 'official' THEN 4 WHEN 'third_party' THEN 3
    WHEN 'user_supplied' THEN 2 WHEN 'estimate' THEN 1 ELSE 0 END DESC,as_of DESC,id DESC LIMIT 1"""
    with connect(db_path) as conn: row=conn.execute(q,args).fetchone()
    return json.loads(row["payload_json"]) if row else None

def _best_rows(rows,key):
    chosen={}
    for row in rows: chosen.setdefault(row[key],json.loads(row["payload_json"]))
    return [chosen[k] for k in sorted(chosen)]

def get_price_history(db_path,symbol,start_date=None,end_date=None,currency=None):
    q="SELECT * FROM price_observations WHERE symbol=?"; args=[symbol.upper()]
    if start_date: q+=" AND date>=?"; args.append(start_date)
    if end_date: q+=" AND date<=?"; args.append(end_date)
    if currency: q+=" AND currency=?"; args.append(currency.upper())
    q+=""" ORDER BY date ASC,CASE data_status WHEN 'official' THEN 4 WHEN 'third_party' THEN 3
    WHEN 'user_supplied' THEN 2 WHEN 'estimate' THEN 1 ELSE 0 END DESC,as_of DESC,id DESC"""
    with connect(db_path) as conn: rows=conn.execute(q,args).fetchall()
    return _best_rows(rows,"date")

def get_corporate_actions(db_path,symbol,start_date=None,end_date=None,currency=None):
    q="SELECT * FROM corporate_actions WHERE symbol=?"; args=[symbol.upper()]
    if start_date: q+=" AND ex_date>=?"; args.append(start_date)
    if end_date: q+=" AND ex_date<=?"; args.append(end_date)
    if currency: q+=" AND currency=?"; args.append(currency.upper())
    q+=""" ORDER BY ex_date ASC,CASE data_status WHEN 'official' THEN 4 WHEN 'third_party' THEN 3
    WHEN 'user_supplied' THEN 2 WHEN 'estimate' THEN 1 ELSE 0 END DESC,as_of DESC,id DESC"""
    with connect(db_path) as conn: rows=conn.execute(q,args).fetchall()
    return _best_rows(rows,"ex_date")

def adjustment_factor(action):
    """Return backward price factor. reference_close must be the prior cum-right/entitlement close."""
    kind=action["action_type"]
    if kind=="split": factor=1.0/float(action["new_shares_per_old_share"])
    elif kind=="bonus_issue": factor=1.0/(1.0+float(action["bonus_shares_per_old_share"]))
    else:
        close=float(action["reference_close"])
        if close<=0: raise ValueError("reference_close must be positive")
        if kind=="cash_dividend":
            amount=float(action["cash_per_share"])
            if amount<0 or amount>=close: raise ValueError("cash dividend must be >=0 and below reference_close")
            factor=(close-amount)/close
        elif kind=="rights_issue":
            ratio=float(action["rights_per_old_share"]); sub=float(action["subscription_price"])
            if ratio<=0 or sub<0: raise ValueError("invalid rights ratio or subscription price")
            terp=(close+ratio*sub)/(1.0+ratio)
            factor=terp/close
        else: raise ValueError("unsupported corporate action type")
    if not 0 < factor <= 1.5: raise ValueError("corporate action factor outside safety bounds; verify event inputs")
    return factor

def get_adjusted_price_history(db_path,symbol,start_date=None,end_date=None,currency=None):
    """Adjust historical OHLC backward for later verified actions; raw observations remain untouched."""
    prices=get_price_history(db_path,symbol,start_date,end_date,currency)
    actions=get_corporate_actions(db_path,symbol,currency=currency)
    result=[]
    for bar in prices:
        factor=1.0; applied=[]
        for action in actions:
            if action["ex_date"]>bar["date"]:
                f=adjustment_factor(action); factor*=f; applied.append({"ex_date":action["ex_date"],"type":action["action_type"],"factor":f})
        adjusted=dict(bar)
        for field in ("open","high","low","close"):
            if bar.get(field) is not None: adjusted["adjusted_"+field]=float(bar[field])*factor
        adjusted["corporate_action_factor"]=factor
        adjusted["applied_actions"]=applied
        adjusted["adjustment_method"]="backward_price_adjustment_from_verified_events"
        result.append(adjusted)
    return result

def record_ingestion_result(db_path,kind,input_name,accepted,rejected):
    with connect(db_path) as conn:
        conn.execute("INSERT INTO ingestion_runs(kind,input_name,accepted,rejected,created_at) VALUES(?,?,?,?,?)",
        (kind,str(input_name),accepted,rejected,datetime.now(timezone.utc).isoformat()))

def database_summary(db_path):
    with connect(db_path) as conn:
        return {table:conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("financial_observations","price_observations","corporate_actions","ingestion_runs")}
