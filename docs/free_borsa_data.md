# Free EGX quote experiment (Borsa)

This integration uses Borsa's public demo endpoint:
`GET https://demo.borsa.ashh.me/demo/quote/{symbol}`.

The public demo is shared and limited to 50 requests/day across visitors.
Treat it as an evaluation endpoint, not a production feed or guaranteed SLA.
Borsa normalizes data from configured third-party providers; the quote response
includes provider attribution where available. Provider coverage and freshness
vary by symbol and upstream source.

## Run

```bash
python -m src.borsa_cli COMI --db data/egx.sqlite
```

The command fetches one quote and stores it in `quote_snapshots`. Repeating an
identical response is idempotent. No API key is required for the public demo.

## Critical separation

A quote snapshot is NOT a daily OHLCV bar. It is deliberately stored in its
own table and marked `historical_ohlcv_eligible: false`. It must not be passed
to technical indicators, backtests, or the investment decision engine.
The response timestamp and upstream provider attribution are preserved.
Missing timestamps, timezone, wrong symbol, non-EGP currency, invalid prices,
HTTP errors, and rate limits fail closed.

## Limitations

- This connector has not been granted an EGX data licence.
- Borsa is an aggregator; it is not the Egyptian Exchange and does not guarantee
  upstream provider accuracy, coverage, or update timing.
- Its demo quota is shared and may be exhausted by other users.
- The current integration retrieves one symbol per request; do not sweep the
  whole market against the shared demo quota.
- Historical OHLCV and financial statements are not supplied by this connector.
- Review Borsa's and upstream providers' terms before operational or commercial use.
