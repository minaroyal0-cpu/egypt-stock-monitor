"""Long-only, next-session-open backtesting with explicit execution costs.

Signals are calculated after a session close and can only execute at the
following session's open. This is a research simulator, not investment advice.
"""
from __future__ import annotations

from math import floor, sqrt
from statistics import stdev
from datetime import date


def _validate_bars(bars):
    if len(bars) < 3:
        raise ValueError("at least 3 daily bars are required")
    dates = [bar.get("date") for bar in bars]
    if any(not d for d in dates) or dates != sorted(dates) or len(set(dates)) != len(dates):
        raise ValueError("bars must have unique chronological dates")
    for bar in bars:
        for field in ("open", "close"):
            value = bar.get("adjusted_" + field, bar.get(field))
            if value is None or float(value) <= 0:
                raise ValueError("each bar requires positive open and close prices")
        if bar.get("currency") and any(
            other.get("currency") != bar.get("currency") for other in bars
        ):
            raise ValueError("mixed currencies are not allowed")


def moving_average_backtest(
    bars, initial_cash=100000.0, fast_window=10, slow_window=30,
    commission_rate=0.001, slippage_rate=0.001, periods_per_year=252,
    integer_shares=True,
):
    """Test an SMA crossover; buy/sell at next open after a close-time signal.

    Costs are fractions of executed notional and are charged on both sides.
    The strategy is long-only, unlevered, and uses no margin. No signal on the
    final bar can execute because there is no next bar.
    """
    _validate_bars(bars)
    if fast_window <= 0 or slow_window <= fast_window:
        raise ValueError("require 0 < fast_window < slow_window")
    if initial_cash <= 0 or periods_per_year <= 0:
        raise ValueError("initial_cash and periods_per_year must be positive")
    if not 0 <= commission_rate < 1 or not 0 <= slippage_rate < 1:
        raise ValueError("commission_rate and slippage_rate must be in [0, 1)")
    close_field = "adjusted_close" if all(b.get("adjusted_close") is not None for b in bars) else "close"
    open_field = "adjusted_open" if all(b.get("adjusted_open") is not None for b in bars) else "open"
    closes = [float(b[close_field]) for b in bars]
    opens = [float(b[open_field]) for b in bars]
    if any(x <= 0 for x in closes + opens):
        raise ValueError("prices must be positive")

    cash = float(initial_cash)
    shares = 0.0
    average_entry_cost = 0.0
    pending = None
    equity_curve = []
    trades = []
    total_buy_notional = 0.0
    total_sell_notional = 0.0
    closed_trade_pnls = []

    def sma_at(end, window):
        return sum(closes[end-window+1:end+1]) / window

    for i, bar in enumerate(bars):
        # Execute only an order generated after the preceding session close.
        if pending is not None:
            side = pending
            raw_open = opens[i]
            execution = raw_open * (1 + slippage_rate if side == "buy" else 1 - slippage_rate)
            if side == "buy" and shares == 0:
                unit_cost = execution * (1 + commission_rate)
                quantity = cash / unit_cost
                if integer_shares:
                    quantity = float(floor(quantity))
                if quantity > 0:
                    notional = quantity * execution
                    fee = notional * commission_rate
                    total_cost = notional + fee
                    if total_cost > cash + 1e-8:
                        raise ArithmeticError("buy would create negative cash")
                    cash -= total_cost
                    shares = quantity
                    average_entry_cost = total_cost
                    total_buy_notional += notional
                    trades.append({"date": bar["date"], "side": "buy", "shares": quantity,
                                   "reference_open": raw_open, "execution_price": execution,
                                   "notional": notional, "commission": fee, "slippage_rate": slippage_rate})
            elif side == "sell" and shares > 0:
                quantity = shares
                notional = quantity * execution
                fee = notional * commission_rate
                proceeds = notional - fee
                pnl = proceeds - average_entry_cost
                cash += proceeds
                total_sell_notional += notional
                trades.append({"date": bar["date"], "side": "sell", "shares": quantity,
                               "reference_open": raw_open, "execution_price": execution,
                               "notional": notional, "commission": fee, "slippage_rate": slippage_rate,
                               "realized_pnl": pnl})
                closed_trade_pnls.append(pnl)
                shares = 0.0
                average_entry_cost = 0.0
            pending = None

        equity = cash + shares * closes[i]
        equity_curve.append({"date": bar["date"], "cash": cash, "shares": shares,
                             "close": closes[i], "equity": equity})

        # Close-of-session signal. It is queued for the next session's open.
        if i >= slow_window - 1:
            fast_now = sma_at(i, fast_window)
            slow_now = sma_at(i, slow_window)
            if i >= slow_window:
                fast_prev = sma_at(i - 1, fast_window)
                slow_prev = sma_at(i - 1, slow_window)
                if fast_prev <= slow_prev and fast_now > slow_now and shares == 0:
                    pending = "buy"
                elif fast_prev >= slow_prev and fast_now < slow_now and shares > 0:
                    pending = "sell"

    final_equity = equity_curve[-1]["equity"]
    total_return = final_equity / initial_cash - 1
    first_day = date.fromisoformat(bars[0]["date"])
    last_day = date.fromisoformat(bars[-1]["date"])
    years = (last_day - first_day).days / 365.25
    cagr = (final_equity / initial_cash) ** (1 / years) - 1 if years > 0 and final_equity > 0 else None
    daily_equity_returns = [
        equity_curve[i]["equity"] / equity_curve[i-1]["equity"] - 1
        for i in range(1, len(equity_curve)) if equity_curve[i-1]["equity"] > 0
    ]
    volatility = stdev(daily_equity_returns) * sqrt(periods_per_year) if len(daily_equity_returns) > 1 else 0.0
    peak = equity_curve[0]["equity"]
    max_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point["equity"])
        max_drawdown = min(max_drawdown, point["equity"] / peak - 1)
    closed = len(closed_trade_pnls)
    average_equity = sum(p["equity"] for p in equity_curve) / len(equity_curve)
    return {
        "strategy": "simple_moving_average_crossover",
        "symbol": bars[0].get("symbol"),
        "currency": bars[0].get("currency"),
        "price_basis": "adjusted_ohlc" if close_field == "adjusted_close" else "raw_ohlc",
        "signal_timing": "signal_after_close_execute_next_session_open",
        "initial_cash": initial_cash, "final_equity": final_equity,
        "cash": cash, "open_shares": shares,
        "total_return": total_return, "cagr": cagr,
        "annualized_volatility": volatility, "max_drawdown": abs(max_drawdown),
        "turnover": (total_buy_notional + total_sell_notional) / average_equity if average_equity else 0.0,
        "trades": trades, "trade_count": len(trades),
        "closed_round_trips": closed,
        "win_rate": (sum(p > 0 for p in closed_trade_pnls) / closed) if closed else None,
        "commission_rate": commission_rate, "slippage_rate": slippage_rate,
        "fast_window": fast_window, "slow_window": slow_window,
        "observations": len(bars),
        "warning": "Educational historical simulation only. Results depend on data quality, costs, liquidity, corporate actions, parameter choices and sample period; they do not predict future returns.",
    }
