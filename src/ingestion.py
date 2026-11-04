"""CSV ingestion and validation for sourced EGX financials, prices and corporate actions."""
import csv,json,math,re
from datetime import date,datetime,timezone
from pathlib import Path

FINANCIAL_NUMBERS={"revenue","gross_profit","operating_profit","net_income","total_assets","total_equity","total_debt","cash_and_equivalents","current_assets","current_liabilities","operating_cash_flow","capital_expenditure","shares_outstanding","eps","book_value_per_share","dividend_per_share"}
PRICE_NUMBERS={"open","high","low","close","volume","turnover_egp","adjusted_close"}
STATUSES={"official","third_party","user_supplied","estimate"}
ACTION_TYPES={"cash_dividend","split","bonus_issue","rights_issue"}

def _number(value,field,allow_empty=False):
    if value in (None,"") and allow_empty: return None
    try: n=float(str(value).replace(",","").strip())
    except (TypeError,ValueError): raise ValueError("invalid_number:"+field)
    if not math.isfinite(n): raise ValueError("non_finite_number:"+field)
    return n

def _valid_date(value):
    try: return date.fromisoformat(str(value)).isoformat()
    except ValueError: raise ValueError("date_must_be_YYYY_MM_DD")

def _validate_source(row):
    if not row.get("source"): raise ValueError("missing:source")
    if not row.get("source_url","").startswith(("https://","http://")): raise ValueError("missing_or_invalid:source_url")
    if row.get("data_status") not in STATUSES: raise ValueError("invalid_data_status")
    if not row.get("as_of"): raise ValueError("missing:as_of")
    _valid_date(row["as_of"])

def _clean(row): return {str(k).strip():(v.strip() if isinstance(v,str) else v) for k,v in row.items()}

def normalize_financial_row(row):
    row=_clean(row)
    for f in ("symbol","company","period","currency","basis"):
        if not row.get(f): raise ValueError("missing:"+f)
    row["symbol"]=row["symbol"].upper(); row["currency"]=row["currency"].upper()
    if not re.fullmatch(r"[A-Z0-9]{3,12}",row["symbol"]): raise ValueError("invalid:symbol")
    if not re.fullmatch(r"[A-Z]{3}",row["currency"]): raise ValueError("invalid_currency")
    if not re.fullmatch(r"^\d{4}(-Q[1-4]|-\d{2}(-\d{2})?)?$",row["period"]): raise ValueError("invalid_period")
    _validate_source(row)
    for f in FINANCIAL_NUMBERS:
        if f in row: row[f]=_number(row[f],f,True)
    row["ingested_at"]=datetime.now(timezone.utc).isoformat(); return row

def normalize_price_row(row):
    row=_clean(row)
    for f in ("symbol","date","currency","source","source_url","data_status","as_of"):
        if not row.get(f): raise ValueError("missing:"+f)
    row["symbol"]=row["symbol"].upper(); row["currency"]=row["currency"].upper()
    if not re.fullmatch(r"[A-Z0-9]{3,12}",row["symbol"]): raise ValueError("invalid:symbol")
    if not re.fullmatch(r"[A-Z]{3}",row["currency"]): raise ValueError("invalid_currency")
    row["date"]=_valid_date(row["date"]); _validate_source(row)
    for f in PRICE_NUMBERS:
        if f not in row:
            if f in ("adjusted_close","turnover_egp"): continue
            raise ValueError("missing:"+f)
        row[f]=_number(row[f],f,f in ("adjusted_close","turnover_egp"))
    if min(row["open"],row["high"],row["low"],row["close"])<=0 or row["volume"]<0: raise ValueError("invalid_price_or_volume")
    if row["low"]>min(row["open"],row["close"]) or row["high"]<max(row["open"],row["close"]) or row["low"]>row["high"]: raise ValueError("inconsistent_ohlc")
    row["ingested_at"]=datetime.now(timezone.utc).isoformat(); return row

def normalize_action_row(row):
    row=_clean(row)
    for f in ("symbol","ex_date","currency","action_type"): 
        if not row.get(f): raise ValueError("missing:"+f)
    row["symbol"]=row["symbol"].upper(); row["currency"]=row["currency"].upper()
    if not re.fullmatch(r"[A-Z0-9]{3,12}",row["symbol"]): raise ValueError("invalid:symbol")
    if not re.fullmatch(r"[A-Z]{3}",row["currency"]): raise ValueError("invalid_currency")
    row["ex_date"]=_valid_date(row["ex_date"])
    if row["action_type"] not in ACTION_TYPES: raise ValueError("unsupported_action_type")
    _validate_source(row)
    numeric_by_type={
      "cash_dividend":("cash_per_share","reference_close"),
      "split":("new_shares_per_old_share",),
      "bonus_issue":("bonus_shares_per_old_share",),
      "rights_issue":("rights_per_old_share","subscription_price","reference_close")}
    for f in numeric_by_type[row["action_type"]]:
        row[f]=_number(row.get(f),f)
        if row[f]<0: raise ValueError("negative_action_value:"+f)
    if row["action_type"] in ("split","bonus_issue") and row[numeric_by_type[row["action_type"]][0]]<=0: raise ValueError("share_ratio_must_be_positive")
    if row["action_type"]=="cash_dividend" and row["cash_per_share"]>=row["reference_close"]: raise ValueError("dividend_must_be_below_reference_close")
    if row["action_type"]=="rights_issue" and row["rights_per_old_share"]<=0: raise ValueError("rights_ratio_must_be_positive")
    for optional in ("record_date","payment_date"):
        if row.get(optional): row[optional]=_valid_date(row[optional])
    row["ingested_at"]=datetime.now(timezone.utc).isoformat(); return row

def ingest_csv(input_path,output_path,kind):
    normalizers={"financial":normalize_financial_row,"prices":normalize_price_row,"actions":normalize_action_row}
    if kind not in normalizers: raise ValueError("kind must be financial, prices, or actions")
    normalizer=normalizers[kind]; accepted=[]; rejected=[]; seen=set()
    with open(input_path,newline="",encoding="utf-8-sig") as handle:
        for line_no,row in enumerate(csv.DictReader(handle),start=2):
            try:
                record=normalizer(row)
                key=((record["symbol"],record["period"],record["basis"]) if kind=="financial" else
                     (record["symbol"],record["date"]) if kind=="prices" else
                     (record["symbol"],record["ex_date"],record["action_type"]))
                if key in seen: raise ValueError("duplicate_record_in_input")
                seen.add(key); accepted.append(record)
            except (ValueError,TypeError) as exc: rejected.append({"line":line_no,"error":str(exc)})
    output=Path(output_path); output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_suffix(output.suffix+".tmp")
    temp.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in accepted),encoding="utf-8")
    temp.replace(output)
    return {"accepted":len(accepted),"rejected":rejected,"output":str(output)}
