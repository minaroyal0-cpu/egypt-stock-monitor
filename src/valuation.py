"""Simple valuation helpers. They are estimates, not investment recommendations."""

def multiple_valuation(price, earnings_per_share=None, book_value_per_share=None,
                       sales_per_share=None, dividend_per_share=None):
    def ratio(a, b):
        try:
            a, b = float(a), float(b)
            return a / b if b else None
        except (TypeError, ValueError):
            return None
    price = float(price)
    return {
        "pe": ratio(price, earnings_per_share),
        "pb": ratio(price, book_value_per_share),
        "ps": ratio(price, sales_per_share),
        "dividend_yield": ratio(dividend_per_share, price),
        "warning": "Multiples are meaningful only with consistent dates, share counts, accounting basis and sector context."
    }

def dcf_value_per_share(fcf, discount_rate, terminal_growth, shares_outstanding,
                        net_debt=0, forecast_years=5):
    """Constant-growth terminal value after explicit flat-FCF forecast; all inputs are assumptions."""
    fcf, rate, growth = float(fcf), float(discount_rate), float(terminal_growth)
    shares, debt = float(shares_outstanding), float(net_debt)
    if shares <= 0 or forecast_years < 1:
        raise ValueError("shares_outstanding and forecast_years must be positive")
    if rate <= growth or growth < 0:
        raise ValueError("discount_rate must exceed non-negative terminal_growth")
    if rate <= -1:
        raise ValueError("discount_rate must be greater than -100%")
    pv = sum(fcf / ((1 + rate) ** year) for year in range(1, forecast_years + 1))
    terminal = (fcf * (1 + growth)) / (rate - growth)
    pv_terminal = terminal / ((1 + rate) ** forecast_years)
    equity_value = pv + pv_terminal - debt
    return {"enterprise_value": pv + pv_terminal, "equity_value": equity_value,
            "value_per_share": equity_value / shares,
            "assumptions": {"fcf": fcf, "discount_rate": rate, "terminal_growth": growth,
                            "forecast_years": forecast_years, "net_debt": debt}}
