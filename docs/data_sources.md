# EGX data-source registry and connection policy

## Why this exists

The analyst must distinguish a source being publicly discoverable from having
permission and technical access to automate its data. A source URL being present
in an imported CSV is provenance supplied by the importer; it is not independent
proof that the document is authentic or that the values were parsed correctly.

## Registered sources

| Source | Role | What is known | Current integration |
|---|---|---|---|
| Egyptian Exchange (EGX) | Primary exchange | Official exchange website and issuer disclosure reference | Not connected |
| Financial Regulatory Authority (FRA) | Regulator | Official press releases and regulatory information | Not connected |
| EGID | EGX-owned market-data and technology provider | Public API documentation lists delayed-feed and market-watch operations | Client scaffold; credentials and access terms unverified |

Reference links:
- EGX: https://beta.egx.com.eg/en
- FRA: https://fra.gov.eg/en/press-releases/
- EGID: https://www.egidegypt.com/
- EGID delayed-feed API documentation: https://ticker.egidegypt.com/index.html

EGID describes itself as an EGX-owned data provider. Its public API documentation
lists delayed-feed routes such as `getEGXMarketWatch`, `getMarketSummary`,
and `getMarketStatus`. This establishes that documented API routes exist; it
does not establish that this repository has a free entitlement, valid credentials,
permission to store or redistribute responses, or a particular delay/history depth.

## EGID client scaffold

A restricted client is available for three documented delayed-feed routes. It:
- Uses HTTPS and a fixed EGID host.
- Requires a vendor-issued bearer token via `EGID_BEARER_TOKEN`.
- Does not guess the undocumented token-acquisition request schema.
- Does not scrape the site or access undocumented routes.
- Returns raw JSON only and marks it `not_normalized`; it does not write data
  into SQLite or feed indicators until field meanings and terms are reviewed.

Run after EGID has issued credentials and confirmed permitted use:
```bash
export EGID_BEARER_TOKEN="vendor-issued-token"
python -m src.egid_cli --endpoint /api/DelayedFeed/getEGXMarketWatch
```

Do not commit credentials to the public repository. Use a local environment
variable for local testing and GitHub Actions secrets only after the account
holder has confirmed the agreement and authorized use.

## Alternative historical-data sources

- EGID: request the permitted historical dataset, delay, format, license, and
  pricing directly from the provider.
- DirectFN Egypt: publicly describes delayed market data and market summaries,
  but the public page is a product description, not an open API entitlement.
- ICE: lists Egyptian Exchange delayed, end-of-day, and historical data products;
  commercial access and licensing need to be confirmed.

No source is selected as a free historical-data provider until the rights,
coverage, adjustment policy, and cost are verified. Avoid unofficial scraping
or treating third-party chart pages as a licensed bulk-data feed.

## Required checks before production ingestion

1. Confirm access terms and permitted use with EGX, FRA, EGID, or the vendor.
2. Confirm whether access is free, delayed, paid, credentialed, or restricted.
3. Confirm allowed history depth, request limits, storage duration, and redistribution.
4. Confirm exact response schemas and timestamps from an authorized test account.
5. Implement provider-specific normalization with retries, timeouts, pagination,
   schema validation, and explicit source timestamps.
6. Preserve a reproducible source reference alongside normalized observations,
   subject to provider storage terms.
7. Mark data with source, retrieval time, publication/as-of time, currency,
   delay, and validation status.

## Important distinction

The source registry still reports `live_data_connected: false` and
`automatic_disclosure_ingestion: false`. The EGID client scaffold is not an
active feed until authorized credentials are configured and a real response is
validated. A successful HTTP response alone is not proof of complete, licensed,
or investment-grade data.
