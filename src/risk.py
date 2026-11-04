"""Transparent historical risk metrics for educational equity research.

These are descriptive statistics, not forecasts or personalized trading advice.
Prices must be positive, chronological observations from one consistent source,
currency, adjustment basis, and frequency.
"""
from __future__ import annotations

from math import isfinite, sqrt
from statistics import mean, stdev


def _positive_prices(prices):
    values = [float(value) for value in prices]
    if any(not isfinite(value) or value <= 0 for value in values):
        raise ValueError("prices must be positive")
    return values


def daily_returns(prices):
    """Simple close-to-close returns in supplied chronological order."""
    values = _positive_prices(prices)
    return [values[i] / values[i - 1] - 1.0 for i in range(1, len(values))]


def historical_risk(prices, periods_per_year=252, confidence=0.95):
    """Compute realized volatility, max drawdown, historical VaR and CVaR.

    VaR/CVaR are reported as positive loss fractions. Historical estimates
    require enough observations and can materially understate future risk.
    """
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if not 0.5 < confidence < 1:
        raise ValueError("confidence must be between 0.5 and 1")
    values = _positive_prices(prices)
    if len(values) < 3:
        raise ValueError("at least 3 prices are required")
    returns = daily_returns(values)
    volatility = stdev(returns) * sqrt(periods_per_year)
    peak = values[0]
    max_drawdown = 0.0
    for price in values:
        peak = max(peak, price)
        max_drawdown = min(max_drawdown, price / peak - 1.0)
    ordered = sorted(returns)
    tail_count = max(1, int((1.0 - confidence) * len(ordered)))
    tail = ordered[:tail_count]
    var_loss = max(0.0, -ordered[tail_count - 1])
    cvar_loss = max(0.0, -mean(tail))
    return {
        "observations": len(values),
        "return_observations": len(returns),
        "periods_per_year": periods_per_year,
        "annualized_volatility": volatility,
        "max_drawdown": abs(max_drawdown),
        "historical_var": var_loss,
        "historical_cvar": cvar_loss,
        "confidence": confidence,
        "method": "historical_simple_returns",
        "warning": (
            "Historical risk is backward-looking, sample-sensitive, and not a "
            "maximum-loss estimate. Validate adjusted prices and corporate actions."
        ),
    }


def portfolio_concentration(position_values):
    """Return normalized position weights and HHI concentration diagnostics."""
    cleaned = {}
    for symbol, raw_value in position_values.items():
        value = float(raw_value)
        if not isfinite(value):
            raise ValueError("position values must be finite")
        if value < 0:
            raise ValueError("position values cannot be negative")
        if value:
            normalized_symbol = str(symbol).strip().upper()
            if not normalized_symbol:
                raise ValueError("position symbols cannot be empty")
            cleaned[normalized_symbol] = cleaned.get(normalized_symbol, 0.0) + value
    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("at least one positive position value is required")
    weights = {symbol: value / total for symbol, value in sorted(cleaned.items())}
    hhi = sum(weight * weight for weight in weights.values())
    return {
        "total_value": total,
        "weights": weights,
        "largest_position_weight": max(weights.values()),
        "herfindahl_index": hhi,
        "effective_number_of_equal_positions": 1.0 / hhi,
        "warning": "Concentration is not the same as risk; sector, currency and correlation exposures also matter.",
    }
