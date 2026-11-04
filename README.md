# EGX Impact Intelligence

A free, conservative EGX news monitor for a configurable watchlist. It discovers headlines, maps them to portfolio companies or relevant sectors, and sends Telegram alerts only when a rule finds a plausible connection.

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

Google News RSS is a discovery layer, not an official disclosure source. An alert must be checked against the original publisher and, where relevant, the Egyptian Exchange (EGX) disclosure page or the Financial Regulatory Authority (FRA). Official reference pages:
- EGX beta website and disclosure/news center: https://beta.egx.com.eg/en
- FRA press releases: https://fra.gov.eg/en/press-releases/
- FRA capital-market overview: https://fra.gov.eg/en/سوق-المال/

The current version does **not** yet ingest the EGX/FRA sites directly or verify a news story against an official filing. It also does not fetch live prices, financial statements, valuation multiples, cash flows, or insider transactions.

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


## Financial and market-data ingestion (first version)

- Import sourced financial-statement CSVs: `python -m src.ingest_cli financial INPUT.csv OUTPUT.jsonl`
- Import sourced daily OHLCV CSVs: `python -m src.ingest_cli prices INPUT.csv OUTPUT.jsonl`
- Use the templates in `data/templates/` and read `docs/data_pipeline.md` before importing.
- Every row must include provenance and a source URL. Invalid rows are reported, not silently accepted.
- No live EGX feed or automatic disclosure scraper is enabled in this version; vendor licensing and source verification remain explicit requirements.


## Historical SQLite database (new)

The analyst branch now includes an append-only local SQLite store for sourced financial statements and daily OHLCV observations. It preserves multiple source observations, ranks official data ahead of third-party, user-supplied, and estimate records, and makes identical imports idempotent.

```bash
python -m src.db_cli init
python -m src.db_cli import financial data/your_financials.csv
python -m src.db_cli import prices data/your_prices.csv
python -m src.db_cli summary
```

The database defaults to `data/egx_history.sqlite3`. Use `--db path/to/file.sqlite3` to select another location. See `docs/database.md` for the storage policy and limitations. The database stores only records you supply; it does not create live market data or connect to a broker.

## Corporate actions and price adjustments

Import sourced dividends, splits, bonus issues, and rights issues with `python -m src.db_cli import actions data/corporate_actions.csv`. The event template is `data/templates/corporate_actions.csv`; formulas, assumptions, unsupported event types, and safeguards are documented in `docs/corporate_actions.md`. Raw prices are never overwritten. Adjusted OHLC is calculated separately from event data with explicit reference prices. Do not mix vendor-adjusted prices with the internally adjusted series.
