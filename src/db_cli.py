"""SQLite commands for historical EGX research data."""
import argparse,csv,json
from .database import connect,store_records,record_ingestion_result,database_summary
from .ingestion import normalize_financial_row,normalize_price_row,normalize_action_row

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
    args=parser.parse_args()
    if args.command=="init": connect(args.db).close(); result={"initialized":True,"database":args.db}
    elif args.command=="import": result=import_csv(args.db,args.input_csv,args.kind)
    else: result=database_summary(args.db)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.command=="import" and result["rejected"]: raise SystemExit(2)
if __name__=="__main__": main()
