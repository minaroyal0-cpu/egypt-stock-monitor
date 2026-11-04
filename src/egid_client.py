"""Minimal EGID delayed-feed client.

Only use with credentials and permissions supplied by EGID. This client reads
raw JSON from a small allowlist of documented delayed-feed routes; it does not
place orders, scrape web pages, or assume data redistribution rights.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://ticker.egidegypt.com"
ALLOWED_PATHS = {
    "/api/DelayedFeed/getEGXMarketWatch",
    "/api/DelayedFeed/getMarketSummary",
    "/api/DelayedFeed/getMarketStatus",
}


class EGIDError(RuntimeError):
    pass


def fetch_delayed_feed(path, params=None, token=None, timeout=15, opener=None):
    """Fetch a documented EGID delayed-feed route using a vendor-issued token.

    Token must be provided explicitly or through EGID_BEARER_TOKEN. No token
    acquisition flow is guessed because the published docs list GetToken but
    do not expose enough verified request details in this repository.
    """
    if path not in ALLOWED_PATHS:
        raise ValueError("unsupported_egid_endpoint")
    token = token or os.getenv("EGID_BEARER_TOKEN")
    if not token:
        raise EGIDError("missing_EGID_BEARER_TOKEN")
    query = urlencode(params or {}, doseq=True)
    url = BASE_URL + path + (("?" + query) if query else "")
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer " + token,
            "User-Agent": "EGX-Impact-Intelligence/0.1",
        },
        method="GET",
    )
    open_url = opener or urlopen
    try:
        with open_url(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise EGIDError("egid_http_status:" + str(status))
            content_type = response.headers.get("Content-Type", "")
            if "json" not in content_type.lower():
                raise EGIDError("egid_non_json_response")
            raw = response.read()
    except HTTPError as exc:
        raise EGIDError("egid_http_status:" + str(exc.code)) from exc
    except URLError as exc:
        raise EGIDError("egid_network_error:" + str(exc.reason)) from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EGIDError("egid_invalid_json") from exc
    return {
        "source": "EGID",
        "source_url": url,
        "data_status": "third_party",
        "feed_type": "delayed",
        "retrieved_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "raw": payload,
        "normalization_status": "not_normalized",
        "note": "Confirm vendor terms and field semantics before database ingestion.",
    }
