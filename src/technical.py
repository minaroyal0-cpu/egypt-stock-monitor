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
