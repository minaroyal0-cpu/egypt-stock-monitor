"""Markdown report formatter with explicit source and uncertainty labels."""
def build_report(company, fundamentals=None, valuation=None, technical=None, provenance=None, risks=None):
    sections = [f"# Equity research snapshot: {company}",
                "> Educational research output, not a buy/sell instruction.",
                "## Data quality and provenance"]
    provenance = provenance or {}
    sections += [f"- Status: {provenance.get('data_status', 'unknown')}",
                 f"- Source: {provenance.get('source', 'not supplied')}",
                 f"- Source URL: {provenance.get('source_url', 'not supplied')}",
                 f"- Period: {provenance.get('period', 'not supplied')}",
                 f"- As of: {provenance.get('as_of', 'not supplied')}"]
    for title, data in (("Fundamentals", fundamentals), ("Valuation", valuation), ("Technical indicators", technical)):
        sections.append("## " + title)
        if not data:
            sections.append("Not calculated: required data was not supplied.")
        else:
            sections.extend(f"- {key}: {value}" for key, value in data.items())
    sections.append("## Key risks")
    sections.extend("- " + str(item) for item in (risks or ["No risk review supplied; this is not evidence of low risk."]))
    sections.append("## Limitations\nMissing inputs are not treated as zero. Estimates depend on stated assumptions; verify figures against official disclosures.")
    return "\n".join(sections) + "\n"
