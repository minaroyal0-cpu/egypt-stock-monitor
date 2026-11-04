import tempfile,unittest
from pathlib import Path
from src.database import store_records,get_price_history,get_adjusted_price_history,get_corporate_actions,database_summary,adjustment_factor
from src.ingestion import normalize_action_row

BASE={"symbol":"ABUK","date":"2025-01-01","currency":"EGP","source":"EGX filing","source_url":"https://example.org/price","data_status":"official","as_of":"2025-01-01","open":100,"high":105,"low":98,"close":100,"volume":1000}
def action(kind,ex_date,**kwargs):
    row={"symbol":"ABUK","ex_date":ex_date,"currency":"EGP","action_type":kind,"source":"issuer disclosure","source_url":"https://example.org/action","data_status":"official","as_of":"2025-02-01",**kwargs}
    return normalize_action_row(row)

class CorporateActionTests(unittest.TestCase):
    def test_split_adjusts_prior_prices_without_mutating_raw(self):
        with tempfile.TemporaryDirectory() as d:
            db=str(Path(d)/"db.sqlite3")
            store_records(db,"prices",[BASE])
            store_records(db,"actions",[action("split","2025-02-01",new_shares_per_old_share="2")])
            raw=get_price_history(db,"ABUK")
            adjusted=get_adjusted_price_history(db,"ABUK")
            self.assertEqual(raw[0]["close"],100)
            self.assertEqual(adjusted[0]["adjusted_close"],50)
            self.assertEqual(adjusted[0]["corporate_action_factor"],0.5)

    def test_cash_dividend_factor(self):
        a=action("cash_dividend","2025-02-01",cash_per_share="5",reference_close="100")
        self.assertAlmostEqual(adjustment_factor(a),0.95)

    def test_rights_issue_terp_factor(self):
        a=action("rights_issue","2025-02-01",rights_per_old_share="0.25",subscription_price="40",reference_close="100")
        self.assertAlmostEqual(adjustment_factor(a),0.88)

    def test_bonus_issue_factor(self):
        a=action("bonus_issue","2025-02-01",bonus_shares_per_old_share="0.5")
        self.assertAlmostEqual(adjustment_factor(a),2/3)

    def test_rejects_bad_action_ratio(self):
        with self.assertRaises(ValueError):
            action("split","2025-02-01",new_shares_per_old_share="0")

    def test_action_storage_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            db=str(Path(d)/"db.sqlite3"); a=action("split","2025-02-01",new_shares_per_old_share="2")
            self.assertEqual(store_records(db,"actions",[a])["inserted"],1)
            self.assertEqual(store_records(db,"actions",[a])["inserted"],0)
            self.assertEqual(database_summary(db)["corporate_actions"],1)

    def test_multiple_action_types_on_same_ex_date_are_both_applied(self):
        with tempfile.TemporaryDirectory() as d:
            db=str(Path(d)/"db.sqlite3")
            store_records(db,"prices",[BASE])
            split=action("split","2025-02-01",new_shares_per_old_share="2")
            dividend=action("cash_dividend","2025-02-01",cash_per_share="5",reference_close="100")
            store_records(db,"actions",[split,dividend])
            rows=get_adjusted_price_history(db,"ABUK")
            self.assertEqual(len(rows[0]["applied_actions"]),2)
            self.assertAlmostEqual(rows[0]["corporate_action_factor"],0.5*0.95)

if __name__=="__main__": unittest.main()
