# Historical risk analytics

The `src.risk` module adds descriptive risk statistics without pretending to forecast prices.

## Price-series metrics

`historical_risk(prices, periods_per_year=252, confidence=0.95)` accepts positive closes in chronological order and reports:

- Annualized sample volatility from simple close-to-close returns.
- Maximum peak-to-trough drawdown in the supplied window.
- Historical VaR and CVaR as positive loss fractions using the empirical left tail.
- Observation counts, annualization convention, confidence level, and a warning.

Use adjusted closes when the purpose is a total-return-like historical price comparison, and verify all corporate actions and source rights first. Do not mix currencies, venues, frequencies, or raw and adjusted prices. The default 252 sessions is a convention, not a claim about every EGX instrument or trading calendar.

Historical VaR is not the worst possible loss, and historical CVaR is not a guarantee. Both are highly sample-dependent; a short or calm period can materially understate risk. They do not model liquidity gaps, suspensions, price limits, slippage, or future regime changes.

## Portfolio concentration

`portfolio_concentration({"ABUK": 750, "FWRY": 250})` returns position weights, largest position weight, Herfindahl-Hirschman concentration index, and effective number of equal-sized positions.

This measures position-size concentration only. It does not measure correlation, common sector exposure, currency exposure, liquidity, leverage, or the user's ability to bear losses.

## Example

```python
from src.risk import historical_risk, portfolio_concentration

risk = historical_risk([100, 102, 99, 101, 97, 100])
concentration = portfolio_concentration({"ABUK": 750, "FWRY": 250})
print(risk)
print(concentration)
```

All outputs are educational historical diagnostics, not forecasts or buy/sell instructions.

## Historical risk CLI

After importing a licensed/verified daily-price CSV and the relevant corporate actions:

```bash
python -m src.db_cli risk ABUK --start 2025-01-01 --end 2025-12-31
python -m src.db_cli concentration '{"ABUK":750,"FWRY":250}'
```

The risk command uses the locally derived backward-adjusted close series. It requires at least three sourced price observations. Historical volatility, drawdown, VaR and CVaR are backward-looking diagnostics, not forecasts or maximum-loss guarantees. Position concentration measures size only, not correlation or liquidity.
