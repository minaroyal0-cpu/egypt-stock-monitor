# EGX Impact Intelligence

A free, conservative EGX news monitor and financial-analysis foundation. It discovers headlines, maps them to portfolio companies or relevant sectors, and sends Telegram alerts only when a rule finds a plausible connection.

## What it does

- Scans Google News RSS searches every 15 minutes through GitHub Actions.
- Deduplicates links in `seen.json` and prioritizes the newest available publication dates.
- Maps direct company mentions and indirect macro/sector channels to the configured watchlist.
- Separates headline wording from actual share-price impact. The engine never calls a headline "bullish" or "bearish" for a stock based on wording alone.
- Sends portfolio-related alerts to Telegram; unrelated headlines are filtered.
- Runs automated unit tests on branch pushes and pull requests.

## Current watchlist

Edit `config/portfolio.json` and keep only symbols you want monitored. This file contains symbols only, not quantities, average prices, balances, or account credentials. The repository is public, so do not add personal holdings data or secrets.

## Setup

Add these repository Actions secrets under Settings → Secrets and variables → Actions:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Then enable GitHub Actions. Use the **Investor Intelligence RSS Monitor** workflow for a manual test. The scheduled workflow checks approximately every 15 minutes, subject to GitHub Actions scheduling delays and availability.

## Source quality and verification

Google News RSS is a discovery layer, not an official disclosure source. An alert must be checked against the original publisher and, where relevant, the Egyptian Exchange (EGX) disclosure page or the Financial Regulatory Authority (FRA).

Official reference pages:
- EGX: https://beta.egx.com.eg/en
- FRA: https://fra.gov.eg/en/press-releases/
- EGID: https://www.egidegypt.com/

EGID publishes a Swagger API with delayed-feed endpoints. A restricted client scaffold is included, but the repository has no EGID-issued credentials and no verified data-use agreement. It does not claim a live data connection. See [docs/data_sources.md](docs/data_sources.md).

## Important analytical limits

- This is a transparent rules-based screening tool, not an AI research analyst, price predictor, or investment recommendation.
- It reads RSS headlines and source labels, not the full article or original disclosure.
- Sector links are indirect watch items and deliberately carry very low confidence.
- The actual direction of stock impact is left undetermined until the full facts, financial exposure, valuation, and market expectations are reviewed.
- A news event may already be reflected in the share price.
- No trades are placed and no brokerage account is accessed.

## Claude integration

There is no Anthropic API integration in this version. A Claude chat subscription does not automatically provide API access. Do not add an API key to source files. If an API integration is added later, use a GitHub Actions secret named `ANTHROPIC_API_KEY`, set an explicit spending limit with the provider, and keep the rules-only mode available as a fallback.

## Local tests

```bash
python -m unittest discover -s tests -v
```

## Financial and market-data ingestion

Import sourced financial-statement CSVs:
```bash
python -m src.ingest_cli financial INPUT.csv OUTPUT.jsonl
python -m src.ingest_cli prices INPUT.csv OUTPUT.jsonl
```
Use templates in `data/templates/`. Each row must include source name, URL, status, and as-of date. Invalid rows are reported rather than silently accepted.

## Historical SQLite database

The analyst branch includes an append-only local SQLite store for sourced financial statements, daily OHLCV observations, and corporate actions. It preserves competing source observations, ranks declared official data ahead of third-party, user-supplied, and estimate records, and makes identical imports idempotent.

```bash
python -m src.db_cli init
python -m src.db_cli import financial data/your_financials.csv
python -m src.db_cli import prices data/your_prices.csv
python -m src.db_cli import actions data/corporate_actions.csv
python -m src.db_cli summary
```

The database defaults to `data/egx_history.sqlite3`. It stores records you supply; it does not create live market data or connect to a broker.

## Source registry and EGID delayed-feed scaffold

```bash
python -m src.source_cli
python -m src.egid_cli --endpoint /api/DelayedFeed/getEGXMarketWatch
```

The EGID command requires a vendor-issued `EGID_BEARER_TOKEN` and confirmation that automated use is permitted. It returns raw, unnormalized JSON and does not import it into the analyst database.

## Corporate actions and adjusted technical indicators

Import sourced dividends, splits, bonus issues, and rights issues with the corporate-actions template. Raw prices are never overwritten. Adjusted OHLC is calculated separately using explicit event data and reference prices. For long histories, use `get_adjusted_price_history` with `analyze_price_history`; the technical analyzer does not silently fall back to raw closes.


## Historical risk diagnostics

The analyst includes historical volatility, maximum drawdown, historical VaR/CVaR and portfolio position-size concentration. These are backward-looking, not forecasts. See [risk methodology](docs/risk.md) and run `python -m src.db_cli risk SYMBOL` after importing verified daily prices and corporate actions.

## Batch historical news-event study

The market-model event-study module can analyze a CSV register of historical news events against a separately sourced daily-prices CSV. It does not fetch market prices or infer which company an article affects; the event register must be reviewed and mapped to the correct ticker by a human.

Create an event register with these columns:
- Required: `event_id,symbol,event_date`
- Optional: `benchmark,estimation_window,event_window_start,event_window_end`

An example header and row are available in [data/templates/event_register.csv](data/templates/event_register.csv). Defaults are benchmark `EGX30`, 60 pre-event return observations, and event offsets -1 through +1. Offsets are trading sessions, not calendar days. Offset 0 is the return ending on the event date.

Run:
```bash
python -m src.event_study_batch --events data/events.csv --prices data/daily_prices.csv --output data/event_study_results.jsonl
```

Each input event produces one JSONL result. A bad event row is recorded as an error without discarding successful rows; the command exits non-zero if any row failed. Results report abnormal returns and CAR in percentage points. They remain descriptive, are not causal evidence or a trading signal, and depend on the quality and adjustment of the supplied prices.

## Human-review RSS event inbox

The RSS monitor also appends newly discovered headlines to `event_inbox.csv`. Each article URL is deduplicated and receives a stable `event_id`. The monitor deliberately leaves `verified_symbol` and `verified_event_date` blank and sets `review_status=needs_review`: a person must check the original disclosure and identify the correct company and event date before copying a verified row into the batch event register. RSS publication time is retained separately and must not be treated as the event date.

The scheduled workflow commits both `seen.json` and `event_inbox.csv`. The inbox is capped at the latest 2,000 rows. It is a review queue, not a source of verified disclosures or trading recommendations.
