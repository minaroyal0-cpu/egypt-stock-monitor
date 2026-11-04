"""Registry of EGX data sources and their verified access capabilities.

This module intentionally does not fetch market data. A public Swagger page or
website is not proof that automated reuse is licensed or that an API credential
is available. Live adapters must be enabled only after access terms are confirmed.
"""
from dataclasses import asdict, dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Source:
    source_id: str
    name: str
    category: str
    website: str
    capabilities: tuple
    access_status: str
    automation_status: str
    notes: str


SOURCES = (
    Source(
        "egx",
        "Egyptian Exchange",
        "exchange",
        "https://beta.egx.com.eg/en",
        ("issuer_disclosures", "market_notices", "listed_company_information"),
        "public_reference",
        "not_connected",
        "Primary exchange reference. Automated extraction and redistribution terms "
        "must be confirmed before enabling a collector.",
    ),
    Source(
        "fra",
        "Financial Regulatory Authority",
        "regulator",
        "https://fra.gov.eg/en/press-releases/",
        ("regulatory_announcements", "regulatory_information"),
        "public_reference",
        "not_connected",
        "Use original FRA publications where relevant; no automated collector is enabled.",
    ),
    Source(
        "egid",
        "Egyptian Exchange Information Technology (EGID)",
        "market_data_provider",
        "https://www.egidegypt.com/",
        ("delayed_market_feed", "market_watch", "historical_market_data", "news_feed"),
        "documented_api_access_unverified",
        "not_connected",
        "A public API documentation page is visible at "
        "https://ticker.egidegypt.com/index.html. Commercial terms, credentials, "
        "permitted use, rate limits, and redistribution rights have not been verified. "
        "Do not call the feed until those conditions are confirmed.",
    ),
)


def list_sources():
    """Return source metadata as JSON-serializable dictionaries."""
    return [
        {**asdict(source), "capabilities": list(source.capabilities)}
        for source in SOURCES
    ]


def get_source(source_id):
    for source in SOURCES:
        if source.source_id == source_id:
            return {**asdict(source), "capabilities": list(source.capabilities)}
    raise KeyError("unknown_source:" + str(source_id))


def classify_source_url(url):
    """Classify a URL against registered source domains; never verifies a filing."""
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme != "https" or not parsed.hostname:
        return {"registered": False, "source_id": None, "reason": "https_url_required"}
    host = parsed.hostname.lower().rstrip(".")
    for source in SOURCES:
        registered_host = urlparse(source.website).hostname.lower()
        if host == registered_host or host.endswith("." + registered_host):
            return {
                "registered": True,
                "source_id": source.source_id,
                "reason": "registered_domain_only",
                "verified_document": False,
            }
    return {
        "registered": False,
        "source_id": None,
        "reason": "domain_not_in_registry",
        "verified_document": False,
    }


def readiness_report():
    """Report what can be used now without implying any live data connection."""
    return {
        "live_data_connected": False,
        "automatic_disclosure_ingestion": False,
        "sources": list_sources(),
        "next_requirements": [
            "Confirm written access and usage terms with the relevant source or vendor.",
            "Obtain credentials through an authorized account if required.",
            "Confirm permitted delay, history depth, rate limits, storage, and redistribution.",
            "Implement and test a source-specific adapter only after those checks.",
            "Record source URL, publication time, retrieval time, currency, and data status.",
        ],
    }
