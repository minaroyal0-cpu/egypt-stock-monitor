# EGX data pipeline

## Current implementation

The first ingestion layer accepts normalized CSV files and writes validated JSON Lines:
- Financial statements: `python -m src.ingest_cli financial INPUT.csv OUTPUT.jsonl`
- Daily prices: `python -m src.ingest_cli prices INPUT.csv OUTPUT.jsonl`

Templates are in `data/templates/`. Each row carries a source name, source URL, status, and as-of date. Status values are `official`, `third_party`, `user_supplied`, or `estimate`. The pipeline rejects missing provenance, malformed dates, invalid numbers, duplicate keys, and impossible OHLC ranges. Rejected line numbers and reasons are printed; the CLI exits non-zero if any row is rejected.

Financial periods are annual, quarterly, monthly, or exact-date labels. Keep the reporting basis explicit (for example, `standalone` or `consolidated`) and never combine them without normalization. Currency is preserved; cross-currency comparisons are not silently converted.

## Source hierarchy

1. Issuer filings and original disclosures on EGX / FRA; record the exact filing URL and publication/as-of date.
2. Issuer investor-relations annual and interim reports, with auditor and reporting basis retained.
3. Licensed market-data vendors, explicitly labelled `third_party`.
4. User-provided files, explicitly labelled `user_supplied`.
5. Estimates, explicitly labelled `estimate` and never mixed with reported actuals.

Official reference portals:
- EGX: https://beta.egx.com.eg/en
- FRA: https://fra.gov.eg/en/press-releases/
- EGID, EGX market-data subsidiary: https://egidegypt.com/index.html

Market data access may require a commercial license or vendor subscription. No undocumented endpoint, scraping bypass, or paid feed is silently enabled. This release does not automatically download EGX disclosures or live prices.

## Price-history controls

The importer stores raw OHLCV and optional adjusted close. Do not calculate long-run returns or technical indicators across splits, dividends, rights issues, or other corporate actions unless the series is adjusted consistently. The importer does not infer adjustment factors.

## Output contract

Each accepted record retains its original source fields plus ingestion timestamp. A missing field is not zero. A rejected row is not silently dropped: its line number and validation reason are reported to the caller.
