# Corporate actions and adjusted historical prices

## Import
Use the template `data/templates/corporate_actions.csv` and run:

```bash
python -m src.db_cli import actions data/corporate_actions.csv
```

Supported events:
- `cash_dividend`: cash_per_share and reference_close
- `split`: new_shares_per_old_share (e.g. 2 for a 2-for-1 split)
- `bonus_issue`: bonus_shares_per_old_share (e.g. 0.5 for one bonus share per two held)
- `rights_issue`: rights_per_old_share, subscription_price, reference_close

Every event must include its ex-date, currency, source URL, source status, and as-of date. Optional record_date and payment_date are stored when supplied.

## Adjustment method
Raw OHLC prices are immutable. `get_adjusted_price_history` calculates a backward-adjusted OHLC series for each historical bar by multiplying factors for verified events whose ex-date is later than the bar date:
- Cash dividend: (reference close - dividend per share) / reference close
- Split: 1 / new shares per old share
- Bonus issue: 1 / (1 + bonus shares per old share)
- Rights issue: TERP / reference close, where TERP = (reference close + rights ratio × subscription price) / (1 + rights ratio)

The action's reference_close must be the official previous cum-entitlement close in the same currency. This explicit input avoids silently guessing the reference price. Multiple event factors are multiplied. The raw records and event source remain available for audit.

## Important controls and limits
- This is a transparent price adjustment approximation for charting and return comparability, not a tax or total-shareholder-return ledger.
- Cash dividend adjustment removes the mechanical ex-dividend price gap; it does not reinvest dividends.
- Rights issue adjustments are theoretical and assume the stated subscription terms and full mathematical entitlement.
- Suspended trading, partial rights exercise, fractional shares, withholding tax, special dividends, capital reductions, mergers, spin-offs, ticker changes, and currency redenominations require dedicated event handling and are not auto-adjusted.
- Do not mix a vendor-adjusted close with this independently adjusted series. Vendor adjusted close is retained as a source field for reconciliation only.
- If an event is missing, wrong, or has a wrong ex-date/reference close, historical indicators and returns can be wrong. Keep unverified events out of official calculations.
- Best-event selection uses source priority (official, third-party, user-supplied, estimate), then newest as-of date. All competing observations remain stored.

## Commands
```bash
python -m src.db_cli init
python -m src.db_cli import actions data/corporate_actions.csv
python -m src.db_cli summary
```

## Technical-indicator integration

For long-run indicators, use the adjusted bars rather than raw closes:

```python
from src.database import get_adjusted_price_history
from src.technical import analyze_price_history

bars = get_adjusted_price_history("data/egx_history.sqlite3", "ABUK")
indicators = analyze_price_history(bars)  # defaults to adjusted_close
```

The helper requires chronological, unique dates and a populated positive price field. It does not silently fall back to raw close when adjusted prices are missing.
