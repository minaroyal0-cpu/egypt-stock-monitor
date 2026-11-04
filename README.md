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

The current version does not automatically ingest EGX/FRA disclosures or live prices. EGID publishes API documentation for delayed and other market-data feeds, but access terms, credentials, usage rights, and rate limits have not yet been confirmed. No live data connection is claimed. See [docs/data_sources.md](docs/data_sources.md).

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

## Source registry

Inspect registered sources and connection readiness:
```bash
python -m src.source_cli
python -m src.source_cli --check-url https://beta.egx.com.eg/en
```

The registry distinguishes public reference pages from authorized automated feeds. A URL matching a registered domain does not prove that a particular document is authentic.

## Corporate actions and adjusted technical indicators

Import sourced dividends, splits, bonus issues, and rights issues with the corporate-actions template. Raw prices are never overwritten. Adjusted OHLC is calculated separately using explicit event data and reference prices. For long histories, use `get_adjusted_price_history` with `analyze_price_history`; the technical analyzer does not silently fall back to raw closes.
