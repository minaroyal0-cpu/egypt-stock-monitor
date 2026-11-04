# Investment decision engine

The decision engine is a research synthesis layer, not an execution system or
personalized investment recommendation.

## Inputs

Call `analyze_investment_case(fundamental_record, price_bars, analysis_date, ...)`
from `src.decision_engine`. It requires:

- One sourced financial record with symbol, period, basis, currency, source,
  source URL, data status, as-of date, and the financial fields required by
  `analyze_fundamentals`.
- At least 30 chronological daily bars for the same symbol and currency.
  Each bar must include adjusted_close, date, source, source URL, data status,
  and as-of date. Use the existing database adjustment pipeline before calling.
- An explicit analysis_date. The engine never assumes the current date.

Optional peer benchmark medians may include positive P/E and P/B values. They
must be supplied by the caller with their own provenance review; the engine
does not invent sector averages.

## Output

The result includes separate fundamental, technical, historical-risk, and
optional peer-valuation dimensions, evidence strings, data-quality assessments,
facts, assumptions, blockers, and limitations. The composite is a heuristic
weighted summary of available dimensions. Missing optional valuation is
excluded and remaining weights are renormalized.

## Quality gate

Both financial and latest-price quality decisions must be `analysis_ready` or
`conditional`. Otherwise the composite score is suppressed and classification
is `insufficient_data`. This is deliberately fail-closed. A data-quality score
is a readiness/provenance indicator, not a probability that data is correct.

## Classification labels

- `constructive_research_setup`: heuristic score >= 70.
- `mixed_or_neutral`: score 45–69.99.
- `elevated_caution`: score < 45.
- `insufficient_data`: one or more quality gates fail.
- `review_required`: no usable dimensions.

These thresholds are screening conventions, not validated EGX predictive
signals, and are not sector-adjusted. Do not interpret the labels as a trade
instruction.

## Important limits

No fair value is inferred from a score. No future return, probability of profit,
or expected price target is generated. Technical and risk metrics are
backward-looking. The engine does not model liquidity, market impact, taxes,
settlement, investor suitability, or brokerage execution. Validate original
financial statements, share counts, corporate actions, and price-source terms
before relying on an analysis.
