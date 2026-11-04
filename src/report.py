"""Markdown report formatter with explicit source, quality, risk and uncertainty labels."""
def build_report(company, fundamentals=None, valuation=None, technical=None, provenance=None, risks=None, historical_risk=None, data_quality=None):
    sections = [f"# Equity research snapshot: {company}",
                "> Educational research output, not a buy/sell instruction.",
                "## Data quality and provenance"]
    provenance = provenance or {}
    sections += [f"- Status: {provenance.get('data_status', 'unknown')}",
                 f"- Source: {provenance.get('source', 'not supplied')}",
                 f"- Source URL: {provenance.get('source_url', 'not supplied')}",
                 f"- Period: {provenance.get('period', 'not supplied')}",
                 f"- As of: {provenance.get('as_of', 'not supplied')}"]
    quality = data_quality or (fundamentals or {}).get("data_quality") or {}
    if quality:
        sections.append(f"- Data readiness: {quality.get('score', 'not scored')}/100")
        sections.append(f"- Quality decision: {quality.get('decision', 'unknown')}")
        sections.append("- Eligible for analysis: " + str(quality.get("eligible_for_analysis", False)))
        sections.append("- Score is a probability: no")
        for reason in quality.get("reasons", []):
            sections.append("- Quality evidence: " + str(reason))
        for warning in quality.get("warnings", []):
            sections.append("- QUALITY WARNING: " + str(warning))
        if quality.get("decision") not in ("analysis_ready", "conditional"):
            sections.append("**CAUTION: Fundamental ratios below are calculated from supplied inputs, but data quality does not permit treating them as analysis-ready.**")
    else:
        sections.append("- QUALITY WARNING: no data-quality assessment supplied.")
    for title, data in (("Fundamentals", fundamentals), ("Valuation", valuation), ("Technical indicators", technical)):
        sections.append("## " + title)
        if not data:
            sections.append("Not calculated: required data was not supplied.")
        else:
            sections.extend(f"- {key}: {value}" for key, value in data.items() if key != "data_quality")
    sections.append("## Historical risk diagnostics")
    if not historical_risk:
        sections.append("Not calculated: sufficient sourced price history was not supplied.")
    else:
        sections.extend(f"- {key}: {value}" for key, value in historical_risk.items())
    sections.append("## Key risks")
    sections.extend("- " + str(item) for item in (risks or ["No risk review supplied; this is not evidence of low risk."]))
    sections.append("## Limitations\nMissing inputs are not treated as zero. Estimates depend on stated assumptions; historical risk is not a forecast. Verify figures against official disclosures.")
    return "\n".join(sections) + "\n"
