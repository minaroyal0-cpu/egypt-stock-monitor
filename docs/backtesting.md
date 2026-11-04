# Historical backtesting (educational)

The backtest module currently implements one transparent example strategy: a fast/slow simple-moving-average crossover. It is a test harness, not a buy/sell recommendation or a claim that this strategy is profitable.

## Execution and look-ahead controls

- A signal is calculated only after a session's close.
- The order is eligible at the **next available session's open**, never at the close that generated the signal.
- The final bar cannot generate an executed order because no following open exists.
- The default strategy is long-only, unlevered, and does not short or borrow.
- By default, whole shares are used; fractional shares can be enabled in the Python API only.
- Missing/nonpositive open or close values, duplicate/out-of-order dates, and mixed currencies are rejected.
- If adjusted OHLC fields exist on every bar, they are used consistently; otherwise raw OHLC is used and the output labels that basis.

## Costs

Commission and adverse slippage are fractions of executed notional and apply independently on buys and sells. CLI defaults are 0.10% commission and 0.10% slippage per side. These are illustrative assumptions, **not verified EGX broker tariffs**. Replace them with the applicable broker, exchange, tax, and transaction-cost schedule before interpreting a result. The simulator does not model market impact, queue priority, price limits, partial fills, liquidity constraints, settlement delays, or lot-size rules.

## Metrics

The report includes total return, calendar-time CAGR, annualized sample volatility, maximum drawdown, turnover, executed orders, closed round trips, and win rate. Win rate is calculated on closed round trips after modeled execution costs. CAGR uses elapsed calendar days; volatility uses the supplied session count convention (252 by default). Open positions are marked to the final close and are not force-liquidated at the end.

## Corporate actions and limitations

Use sourced, consistently adjusted OHLC prices and verify all corporate actions. The repository's adjustment method is a backward price adjustment; it does not reinvest cash dividends or create a full shareholder cash ledger. This is therefore not a fully accurate total-return backtest. Adjusted prices can be inappropriate for modeling actual historical execution levels; they are used here to avoid mechanical split/dividend price discontinuities in a simplified educational simulator. A production-grade engine needs event-aware share/cash accounting and verified execution prices.

Never use fabricated data as market evidence. Unit tests may use synthetic bars solely to verify mechanics; those tests are not market backtests and say nothing about strategy performance. No real EGX performance result is claimed until licensed/verified historical data, corporate actions, and actual cost schedules are supplied and independently checked.

## CLI

After importing a sourced daily-price CSV and verified corporate actions:

```bash
python -m src.backtest_cli ABUK --start 2024-01-01 --end 2025-12-31 --currency EGP
```

Options include `--cash`, `--fast`, `--slow`, `--commission`, and `--slippage`. Rates are decimal fractions (0.001 = 0.10%). Outputs are descriptive historical simulations, not forecasts, guarantees, or personalized investment instructions.
