"""Fundamental ratio calculations from source-documented financial statements."""

def safe_div(a, b):
    try:
        a, b = float(a), float(b)
        return a / b if b else None
    except (TypeError, ValueError):
        return None

def analyze_fundamentals(row):
    revenue=float(row['revenue']); gross=float(row['gross_profit']); operating=float(row['operating_profit'])
    net=float(row['net_income']); assets=float(row['total_assets']); equity=float(row['total_equity'])
    debt=float(row.get('total_debt') or 0); cash=float(row.get('cash_and_equivalents') or 0)
    prior=row.get('prior_revenue')
    cfo=row.get('operating_cash_flow'); capex=row.get('capital_expenditure')
    cfo=float(cfo) if cfo not in (None, '') else None
    capex=float(capex) if capex not in (None, '') else None
    return {
      'revenue_growth': safe_div(revenue-float(prior),abs(float(prior))) if prior not in (None, '', 0, '0') else None,
      'gross_margin':safe_div(gross,revenue), 'operating_margin':safe_div(operating,revenue),
      'net_margin':safe_div(net,revenue), 'roe':safe_div(net,equity), 'roa':safe_div(net,assets),
      'debt_to_equity':safe_div(debt,equity), 'net_debt':debt-cash,
      'current_ratio':safe_div(row.get('current_assets'),row.get('current_liabilities')),
      'operating_cash_flow':cfo, 'free_cash_flow':cfo-abs(capex) if cfo is not None and capex is not None else None,
      'earnings_quality_flag':bool(cfo is not None and net>0 and cfo<net),
      'source':row.get('source','unspecified'), 'period':row.get('period','unspecified'),
      'currency':row.get('currency','EGP'), 'data_status':row.get('data_status','user_supplied')
    }
