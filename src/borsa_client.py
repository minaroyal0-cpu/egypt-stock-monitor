"""Free Borsa demo quote client.

The public demo is shared and rate-limited. Quote snapshots are stored separately
from daily OHLC bars and are never fed into historical indicators/backtests.
"""
import json
import math
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://demo.borsa.ashh.me"
SOURCE = "Borsa demo (third-party aggregator)"
ALLOWED_SYMBOL = __import__("re").compile(r"^[A-Z0-9]{2,12}$")


class BorsaError(RuntimeError):
    pass


def _parse_timestamp(value):
    if not isinstance(value, str) or not value.strip():
        raise BorsaError("missing_quote_timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BorsaError("invalid_quote_timestamp") from exc
    if parsed.tzinfo is None:
        raise BorsaError("quote_timestamp_missing_timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def normalize_quote(payload, requested_symbol):
    if not isinstance(payload, dict):
        raise BorsaError("quote_payload_must_be_object")
    symbol = str(payload.get("symbol", "")).strip().upper()
    expected = requested_symbol.strip().upper()
    if not ALLOWED_SYMBOL.fullmatch(expected) or symbol != expected:
        raise BorsaError("quote_symbol_mismatch")
    try:
        price = float(payload["price"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BorsaError("quote_price_missing_or_invalid") from exc
    if not math.isfinite(price) or price <= 0:
        raise BorsaError("quote_price_must_be_positive_and_finite")
    currency = str(payload.get("currency", "")).strip().upper()
    if currency != "EGP":
        raise BorsaError("quote_currency_not_egp_or_missing")
    timestamp = _parse_timestamp(payload.get("timestamp"))
    provider = payload.get("attribution") or {}
    if not isinstance(provider, dict):
        provider = {}
    return {
        "symbol": symbol,
        "price": price,
        "currency": currency,
        "timestamp": timestamp,
        "source": SOURCE,
        "provider": str(provider.get("provider") or payload.get("source") or "unknown"),
        "provider_url": str(provider.get("url") or ""),
        "api_symbol": str(payload.get("api_symbol") or ""),
        "change": _optional_number(payload.get("change")),
        "change_percent": _optional_number(payload.get("change_percent")),
        "volume": _optional_number(payload.get("volume")),
        "high": _optional_number(payload.get("high")),
        "low": _optional_number(payload.get("low")),
        "data_status": "third_party",
        "feed_type": "demo_quote",
        "historical_ohlcv_eligible": False,
    }


def _optional_number(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def fetch_quote(symbol, timeout=12, opener=None):
    symbol = str(symbol).strip().upper()
    if not ALLOWED_SYMBOL.fullmatch(symbol):
        raise ValueError("invalid_symbol")
    request = Request(
        BASE_URL + "/demo/quote/" + symbol,
        headers={"Accept": "application/json", "User-Agent": "EGX-Impact-Intelligence/0.1"},
        method="GET",
    )
    try:
        with (opener or urlopen)(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise BorsaError("borsa_http_status:" + str(status))
            content_type = response.headers.get("Content-Type", "")
            if "json" not in content_type.lower():
                raise BorsaError("borsa_non_json_response")
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 429:
            raise BorsaError("borsa_demo_daily_limit_reached") from exc
        raise BorsaError("borsa_http_status:" + str(exc.code)) from exc
    except URLError as exc:
        raise BorsaError("borsa_network_error:" + str(exc.reason)) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BorsaError("borsa_invalid_json") from exc
    return normalize_quote(payload, symbol)
