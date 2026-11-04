"""SQLite commands for sourced EGX research data and historical risk diagnostics."""
import argparse,csv,json
from .database import connect,store_records,record_ingestion_result,database_summary,get_adjusted_price_history
from .ingestion import normalize_financial_row,normalize_price_row,normalize_action_row
from .risk import historical_risk,portfolio_concentration

def import_csv(db_path,input_path,kind):
    normalizers={"financial":normalize_financial_row,"prices":normalize_price_row,"actions":normalize_action_row}
    if kind not in normalizers: raise ValueError("invalid import kind")
    accepted=[]; rejected=[]
    with open(input_path,newline="",encoding="utf-8-sig") as handle:
        for line_no,row in enumerate(csv.DictReader(handle),start=2):
            try: accepted.append(normalizers[kind](row))
            except (ValueError,TypeError) as exc: rejected.append({"line":line_no,"error":str(exc)})
    result=store_records(db_path,kind,accepted,input_name=input_path)
    record_ingestion_result(db_path,kind,input_path,len(accepted),len(rejected))
    return {**result,"accepted":len(accepted),"rejected":rejected,"database":str(db_path)}

def main():
    parser=argparse.ArgumentParser(description="Historical SQLite store for sourced EGX data")
    sub=parser.add_subparsers(dest="command",required=True)
    init=sub.add_parser("init"); init.add_argument("--db",default="data/egx_history.sqlite3")
    imp=sub.add_parser("import"); imp.add_argument("kind",choices=("financial","prices","actions")); imp.add_argument("input_csv"); imp.add_argument("--db",default="data/egx_history.sqlite3")
    summary=sub.add_parser("summary"); summary.add_argument("--db",default="data/egx_history.sqlite3")
    risk=sub.add_parser("risk",help="Historical risk metrics for one symbol")
    risk.add_argument("symbol"); risk.add_argument("--start"); risk.add_argument("--end")
    risk.add_argument("--periods-per-year",type=int,default=252); risk.add_argument("--currency",help="Required when the symbol has price history in multiple currencies"); risk.add_argument("--db",default="data/egx_history.sqlite3")
    concentration=sub.add_parser("concentration",help="Position-size concentration from a JSON object")
    concentration.add_argument("positions_json",help='Example: \'{"ABUK":750,"FWRY":250}\'')
    args=parser.parse_args()
    if args.command=="init": connect(args.db).close(); result={"initialized":True,"database":args.db}
    elif args.command=="import": result=import_csv(args.db,args.input_csv,args.kind)
    elif args.command=="risk":
        bars=get_adjusted_price_history(args.db,args.symbol,args.start,args.end,args.currency)
        currencies=sorted({bar["currency"] for bar in bars})
        if len(currencies)>1: raise SystemExit("Multiple currencies found; rerun with --currency CODE to avoid mixing price series.")
        if len(bars)<3: raise SystemExit("Insufficient sourced price history: at least 3 adjusted closes are required.")
        result={"symbol":args.symbol.upper(),"currency":currencies[0],"price_basis":"backward_adjusted_close","adjustment_as_of":args.end or "latest stored action","risk":historical_risk([bar["adjusted_close"] for bar in bars],args.periods_per_year)}
    elif args.command=="concentration":
        try: positions=json.loads(args.positions_json)
        except json.JSONDecodeError as exc: raise SystemExit("positions_json must be a valid JSON object") from exc
        if not isinstance(positions,dict): raise SystemExit("positions_json must be a JSON object")
        result=portfolio_concentration(positions)
    else: result=database_summary(args.db)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.command=="import" and result["rejected"]: raise SystemExit(2)
if __name__=="__main__": main()
