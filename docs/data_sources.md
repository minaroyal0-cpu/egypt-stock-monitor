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
| EGID | EGX-owned market-data and technology provider | Public API documentation lists delayed-feed and feed operations | Not connected; access and usage terms unverified |

Reference links:
- EGX: https://beta.egx.com.eg/en
- FRA: https://fra.gov.eg/en/press-releases/
- EGID: https://www.egidegypt.com/
- EGID API documentation: https://ticker.egidegypt.com/index.html

EGID's public API documentation is useful evidence that documented feed
operations exist. It does not establish that this repository has credentials,
a free entitlement, permission to store or redistribute the data, or permission
to automate every listed operation. No undocumented endpoint is used.

## Current capabilities

- `python -m src.source_cli` prints the source registry and integration status.
- `python -m src.source_cli --check-url https://beta.egx.com.eg/en` classifies
  whether a URL belongs to a registered source domain.
- URL classification is not document authentication, legal clearance, or
  validation of the contents of a filing.
- Existing CSV ingestion remains the controlled path for importing data whose
  source and reporting metadata have been reviewed.

## Required checks before a live adapter is enabled

1. Confirm access terms and permitted use with EGX, FRA, EGID, or the relevant vendor.
2. Confirm whether access is free, delayed, paid, credentialed, or restricted.
3. Confirm allowed history depth, request limits, storage duration, and redistribution.
4. Confirm the exact response schema and timestamps from an authorized test account.
5. Implement a provider-specific adapter with retries, timeouts, pagination, and
   schema validation; never silently reinterpret missing values as zero.
6. Preserve the raw response or a reproducible source reference alongside normalized
   observations, subject to the provider's storage terms.
7. Mark data with source, retrieval time, source publication/as-of time, currency,
   delay, and validation status.

## Important distinction

The registry currently reports `live_data_connected: false` and
`automatic_disclosure_ingestion: false`. This is deliberate. The next
implementation step is to obtain and verify an authorized data entitlement,
then connect a real adapter. A mock feed or an unlicensed scrape must not be
presented as live official market data.
