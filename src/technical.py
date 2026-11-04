"""Dependency-free technical indicators over chronological closing prices."""
def sma(values, window):
    if window <= 0:
        raise ValueError("window must be positive")
    values = [float(x) for x in values]
    return [None if i + 1 < window else sum(values[i + 1 - window:i + 1]) / window
            for i in range(len(values))]

def ema(values, window):
    if window <= 0:
        raise ValueError("window must be positive")
    values = [float(x) for x in values]
    if not values:
        return []
    alpha = 2 / (window + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result

def rsi(values, window=14):
    values = [float(x) for x in values]
    if window <= 0:
        raise ValueError("window must be positive")
    if len(values) <= window:
        return [None] * len(values)
    gains = [max(values[i] - values[i-1], 0) for i in range(1, len(values))]
    losses = [max(values[i-1] - values[i], 0) for i in range(1, len(values))]
    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window
    out = [None] * window
    def calc(g, l):
        if l == 0:
            return 100.0 if g > 0 else 50.0
        return 100 - 100 / (1 + g / l)
    out.append(calc(avg_gain, avg_loss))
    for i in range(window, len(gains)):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window
        out.append(calc(avg_gain, avg_loss))
    return out

def macd(values, fast=12, slow=26, signal=9):
    if fast >= slow:
        raise ValueError("fast period must be less than slow period")
    values = [float(x) for x in values]
    fast_line, slow_line = ema(values, fast), ema(values, slow)
    line = [a - b for a, b in zip(fast_line, slow_line)]
    signal_line = ema(line, signal)
    return {"macd": line, "signal": signal_line,
            "histogram": [a - b for a, b in zip(line, signal_line)]}

def analyze_price_history(bars, price_field="adjusted_close"):
    """Calculate indicators from bars, requiring an explicitly selected price field.

    For long histories, pass bars from get_adjusted_price_history and retain
    the default adjusted_close field. Raw close can be selected deliberately
    for a non-adjusted short-window analysis.
    """
    if not bars:
        return []
    dates = [bar.get("date") for bar in bars]
    if any(not day for day in dates) or dates != sorted(dates) or len(set(dates)) != len(dates):
        raise ValueError("bars must have unique dates in chronological order")
    values = []
    for bar in bars:
        value = bar.get(price_field)
        if value is None:
            raise ValueError("missing_price_field:" + price_field)
        number = float(value)
        if number <= 0:
            raise ValueError("prices must be positive")
        values.append(number)
    rsi_values = rsi(values)
    macd_values = macd(values)
    sma20 = sma(values, 20)
    ema20 = ema(values, 20)
    return [
        {"date": dates[i], "price_field": price_field, "price": values[i],
         "sma20": sma20[i], "ema20": ema20[i], "rsi14": rsi_values[i],
         "macd": macd_values["macd"][i], "macd_signal": macd_values["signal"][i],
         "macd_histogram": macd_values["histogram"][i]}
        for i in range(len(values))
    ]
