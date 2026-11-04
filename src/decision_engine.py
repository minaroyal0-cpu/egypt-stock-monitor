"""Explainable, quality-gated investment research synthesis.

This module produces an educational research classification, never an order
or personalized buy/sell instruction. Scores are heuristic summaries, not
probabilities, forecasts, or guarantees.
"""
from __future__ import annotations

from datetime import date
from math import isfinite

from .data_quality import assess_record_quality, as_number
from .financial_analysis import analyze_fundamentals
from .risk import historical_risk
from .technical import analyze_price_history


DIMENSION_WEIGHTS = {"fundamentals": 0.35, "technical": 0.25, "risk": 0.25, "valuation": 0.15}


def _bounded_score(value):
    return max(0.0, min(100.0, float(value)))


def _fundamental_score(metrics):
    score, evidence = 50.0, []
    growth = metrics.get("revenue_growth")
    if growth is not None:
        delta = 10 if growth > 0 else (-10 if growth < 0 else 0)
        score += delta
        evidence.append("revenue_growth:" + ("positive" if delta > 0 else "negative" if delta < 0 else "flat"))
    for key in ("gross_margin", "operating_margin", "net_margin", "roe"):
        value = metrics.get(key)
        if value is not None:
            delta = 5 if value > 0 else (-5 if value < 0 else 0)
            score += delta
            evidence.append(key + ":" + ("positive" if delta > 0 else "negative" if delta < 0 else "zero"))
    leverage = metrics.get("debt_to_equity")
    if leverage is not None:
        delta = 5 if 0 <= leverage <= 1 else (-5 if leverage > 1 else -10)
        score += delta
        evidence.append("debt_to_equity:" + ("at_or_below_1" if delta > 0 else "above_1_or_negative"))
    if metrics.get("earnings_quality_flag"):
        score -= 5
        evidence.append("operating_cash_flow_below_positive_net_income")
    return {"score": _bounded_score(score), "evidence": evidence,
            "method": "directional_heuristic_not_sector_adjusted"}


def _technical_score(latest):
    score, evidence = 50.0, []
    price, sma20 = latest.get("price"), latest.get("sma20")
    if sma20 is not None:
        delta = 15 if price > sma20 else -15 if price < sma20 else 0
        score += delta
        evidence.append("price_vs_sma20:" + ("above" if delta > 0 else "below" if delta < 0 else "equal"))
    histogram = latest.get("macd_histogram")
    if histogram is not None:
        delta = 10 if histogram > 0 else -10 if histogram < 0 else 0
        score += delta
        evidence.append("macd_histogram:" + ("positive" if delta > 0 else "negative" if delta < 0 else "flat"))
    rsi = latest.get("rsi14")
    if rsi is not None:
        if 40 <= rsi <= 65:
            score += 5
            evidence.append("rsi14:middle_range")
        elif rsi >= 75:
            score -= 10
            evidence.append("rsi14:high_momentum_caution")
        elif rsi <= 30:
            score -= 5
            evidence.append("rsi14:weak_momentum")
    return {"score": _bounded_score(score), "evidence": evidence,
            "method": "sma20_macd_rsi14_heuristic"}


def _risk_score(risk):
    score, evidence = 100.0, []
    drawdown, volatility = risk["max_drawdown"], risk["annualized_volatility"]
    if drawdown > 0.40:
        score -= 35
        evidence.append("drawdown:above_40_percent")
    elif drawdown > 0.25:
        score -= 20
        evidence.append("drawdown:25_to_40_percent")
    elif drawdown > 0.10:
        score -= 10
        evidence.append("drawdown:10_to_25_percent")
    else:
        evidence.append("drawdown:at_or_below_10_percent")
    if volatility > 0.80:
        score -= 30
        evidence.append("annualized_volatility:above_80_percent")
    elif volatility > 0.50:
        score -= 20
        evidence.append("annualized_volatility:50_to_80_percent")
    elif volatility > 0.30:
        score -= 10
        evidence.append("annualized_volatility:30_to_50_percent")
    else:
        evidence.append("annualized_volatility:at_or_below_30_percent")
    return {"score": _bounded_score(score), "evidence": evidence,
            "method": "historical_volatility_and_max_drawdown_screen"}


def _valuation_score(metrics, peer_benchmarks):
    if not peer_benchmarks:
        return None
    evidence, comparisons = [], []
    for metric in ("pe", "pb"):
        actual, peer = as_number(metrics.get(metric)), as_number(peer_benchmarks.get(metric))
        if actual is None or peer is None or actual <= 0 or peer <= 0:
            continue
        comparisons.append(1 if actual < peer else 0 if actual == peer else -1)
        evidence.append(metric + (":below_peer_median" if actual < peer else ":at_peer_median" if actual == peer else ":above_peer_median"))
    if not comparisons:
        return None
    return {"score": _bounded_score(50 + (sum(comparisons) / len(comparisons)) * 25),
            "evidence": evidence, "method": "relative_to_user_supplied_peer_medians",
            "peer_benchmarks": {key: peer_benchmarks[key] for key in ("pe", "pb") if key in peer_benchmarks}}


def _combine(dimensions):
    available = [(data["score"], DIMENSION_WEIGHTS[name])
                 for name, data in dimensions.items() if data is not None]
    total_weight = sum(weight for _, weight in available)
    if not available or total_weight <= 0:
        return None
    return round(sum(score * weight for score, weight in available) / total_weight, 2)


def analyze_investment_case(fundamental_record, price_bars, analysis_date,
                            peer_benchmarks=None, max_financial_age_days=550,
                            max_price_age_days=7):
    """Synthesize fundamentals, technicals, risk and optional peer valuation."""
    if not analysis_date:
        raise ValueError("analysis_date is required explicitly (YYYY-MM-DD)")
    try:
        reference_date = date.fromisoformat(analysis_date)
    except (TypeError, ValueError):
        raise ValueError("analysis_date must be YYYY-MM-DD")
    if not isinstance(price_bars, list) or len(price_bars) < 30:
        raise ValueError("at least 30 sourced daily price bars are required")
    symbol = str(fundamental_record.get("symbol", "")).strip().upper()
    if not symbol:
        raise ValueError("fundamental_record.symbol is required")
    dates = [bar.get("date") for bar in price_bars]
    if dates != sorted(dates) or len(set(dates)) != len(dates) or any(not day for day in dates):
        raise ValueError("price bars must have unique chronological dates")
    for day in dates:
        try:
            if date.fromisoformat(day) > reference_date:
                raise ValueError("price bar date cannot be after analysis_date")
        except (TypeError, ValueError) as exc:
            if str(exc) == "price bar date cannot be after analysis_date":
                raise
            raise ValueError("price bar dates must be YYYY-MM-DD")
    for bar in price_bars:
        if str(bar.get("symbol", "")).strip().upper() != symbol:
            raise ValueError("all price bars must match the fundamental symbol")
        if bar.get("currency") != fundamental_record.get("currency"):
            raise ValueError("financial and price currencies must match")
        if bar.get("source") != price_bars[-1].get("source"):
            raise ValueError("price bars must use one consistent source")
    latest_bar = price_bars[-1]
    if latest_bar.get("as_of") is None:
        raise ValueError("latest price bar must include as_of")
    financial_quality = assess_record_quality(fundamental_record, "financial", analysis_date, max_financial_age_days)
    price_quality = assess_record_quality(latest_bar, "prices", analysis_date, max_price_age_days)
    fundamentals = analyze_fundamentals(fundamental_record, analysis_date, max_financial_age_days)
    latest_technical = analyze_price_history(price_bars, "adjusted_close")[-1]
    closes = [as_number(bar.get("adjusted_close")) for bar in price_bars]
    if any(value is None or value <= 0 or not isfinite(value) for value in closes):
        raise ValueError("all adjusted_close values must be finite and positive")
    risk = historical_risk(closes)
    price = closes[-1]
    eps, bvps = as_number(fundamental_record.get("eps")), as_number(fundamental_record.get("book_value_per_share"))
    valuation_metrics = {"pe": price / eps if eps is not None and eps > 0 else None,
                         "pb": price / bvps if bvps is not None and bvps > 0 else None}
    valuation = _valuation_score(valuation_metrics, peer_benchmarks)
    dimensions = {"fundamentals": _fundamental_score(fundamentals),
                  "technical": _technical_score(latest_technical),
                  "risk": _risk_score(risk), "valuation": valuation}
    score = _combine(dimensions)
    blockers = []
    for label, quality in (("financial", financial_quality), ("prices", price_quality)):
        if quality["decision"] not in ("analysis_ready", "conditional"):
            blockers.append(label + "_data_" + quality["decision"])
    if blockers:
        classification, score = "insufficient_data", None
    elif score is None:
        classification = "review_required"
    elif score >= 70:
        classification = "constructive_research_setup"
    elif score >= 45:
        classification = "mixed_or_neutral"
    else:
        classification = "elevated_caution"
    return {
        "symbol": symbol, "analysis_date": analysis_date, "classification": classification,
        "composite_score": score, "score_is_probability": False, "dimensions": dimensions,
        "data_quality": {"financial": financial_quality, "prices": price_quality},
        "fundamentals": fundamentals, "technical": latest_technical, "historical_risk": risk,
        "valuation_metrics": valuation_metrics, "peer_valuation": valuation, "blockers": blockers,
        "facts": {"financial_period": fundamental_record.get("period"),
                  "financial_as_of": fundamental_record.get("as_of"), "price_date": latest_bar.get("date"),
                  "price_as_of": latest_bar.get("as_of"), "price_source": latest_bar.get("source"),
                  "price_currency": latest_bar.get("currency"), "price_basis": "adjusted_close"},
        "assumptions": {"analysis_date": analysis_date, "financial_max_age_days": max_financial_age_days,
                        "price_max_age_days": max_price_age_days,
                        "peer_benchmarks_are_user_supplied": bool(peer_benchmarks),
                        "heuristic_weights": DIMENSION_WEIGHTS},
        "limitations": [
            "Educational research classification only; not a buy/sell instruction or personal recommendation.",
            "Heuristic scores are not probabilities, forecasts, or guarantees.",
            "Fundamental and technical thresholds are not sector-adjusted or validated on EGX historical outcomes.",
            "Peer valuation is omitted unless positive peer median P/E or P/B values are supplied.",
            "The engine does not estimate fair value without an explicit, separately reviewed valuation model.",
            "Historical volatility and drawdown are backward-looking and may understate future risk.",
            "Data-quality scores measure readiness and provenance, not factual correctness.",
        ],
    }
