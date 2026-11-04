# Explainable data-quality scoring

`src.data_quality.assess_record_quality(record, record_type, analysis_date)`
returns a 0–100 data-readiness score, a decision, reasons, and warnings.

## What the score means

The score is **not** a probability that a number is true, and it does not verify
the contents of a source URL. It measures whether the record has useful
provenance, required identifying metadata, and (when explicitly requested)
reasonable freshness.

| Dimension | Maximum |
|---|---:|
| Declared source status | 30 |
| Source identity | 8 |
| Valid HTTP(S) source URL | 12 |
| Symbol | 8 |
| Currency | 6 |
| Period/basis or event/price date | 10 |
| Freshness against an explicit analysis date | 30 |

Source-status points: official 30, third_party 22, user_supplied 14, estimate 6.
This is a declared classification, not independent verification of the publisher.

## Decisions

- `analysis_ready`: score at least 80 and no blocking metadata warnings.
- `conditional`: score at least 60 and no blocking metadata warnings.
- `review_required`: freshness was not assessed, or the record is stale/future-dated.
- `estimate_only`: estimates remain visibly separate from reported actuals.
- `insufficient`: required provenance or identity metadata is missing/invalid.

Missing analysis date means freshness contributes no points and the record is
not called analysis-ready. Default freshness windows are 7 days for prices and
550 days for financial statements and corporate actions; callers can override
these explicitly for a particular analysis. These defaults are policy choices,
not exchange rules.

The function does not silently convert currencies, infer missing dates, verify
URLs, establish source authenticity, or claim a record is suitable for trading.
