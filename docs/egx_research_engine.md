# EGX research engine (phase 1)

This package adds transparent, reproducible screening to the existing news monitor.

## Commands

```bash
python -m unittest discover -s tests -v
python -m src.ii_egx.liquidity data/templates/egx_daily_prices.csv /tmp/egx_liquidity.json
python -m src.ii_egx.fundamentals data/templates/egx_fundamentals.csv /tmp/egx_fundamentals.jsonl
python -m src.ii_egx.report data/templates/egx_daily_prices.csv /tmp/egx_report.md --fundamentals-csv data/templates/egx_fundamentals.csv
```

Replace template rows with actual sourced records before interpreting results. The example row is intentionally zero/blank and is not market data.

## Liquidity methodology

- Groups daily observations by symbol and sorts by date.
- Uses the latest 20 supplied observations for each symbol.
- Ranks by median daily turnover, reducing the influence of one unusually active day.
- Counts sessions with nonzero volume.
- If value_egp is present, it is used as reported turnover. Otherwise turnover is estimated as close × volume and explicitly labelled.
- Initial bands: >= EGP 5m high, >= EGP 1m good, >= EGP 250k medium, >= EGP 50k low, otherwise weak. These are internal thresholds, not official EGX rules.

A production universe needs a current official EGX security master and reliable, licensed daily history for every active instrument. The engine does not infer a complete universe from a watchlist.

## Fundamentals methodology

The CSV must contain symbol, period, source name and source URL. Ratios are calculated only when required source values are present. ROE and ROA use supplied period-end balances; this is a screening approximation. Banks, insurers, real estate developers and holding companies need sector-aware metrics before fair-value comparisons.

## Data integrity

Never mix standalone and consolidated statements, different reporting periods, adjusted and unadjusted prices, or currencies without explicit normalization. Preserve source, retrieval date, period, statement type and verification status. Do not treat a missing field as zero.

## Current scope

This phase does not download EGX prices, scrape protected sites, claim real-time access, calculate fair value, detect insider trades, or issue recommendations. It provides a safe foundation for imported data and later source adapters.
