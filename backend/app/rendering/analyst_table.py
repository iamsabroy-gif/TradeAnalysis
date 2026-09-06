"""
Analyst working table renderer for Phase 1 Gatekeeper.
Maps to Phase1-Rules.md §4 internal working table.
"""

from typing import Any, Dict, List
from backend.app.models.schemas import CompanyInput, Phase1Result

CHECK_TECHNICAL_TITLES = {
    1: "Auditor & Regulator Integrity",
    2: "Promoter Pledge & Encumbrance",
    3: "Related-Party 'Leakage'",
    4: "Contingent Liabilities",
    5: "Cash Conversion (5-yr CFO / PAT)",
    6: "Executive Stability (CFO Changes & Restatements)",
}

CHECK_THRESHOLDS = {
    1: "Clean audit opinion; No mid-tenure resignation (3y); No adverse reg order (5y); Legal fees <= 5x audit fees & <= 2x YoY growth",
    2: "Pledged shares <= 10% of promoter holding; Non-rising trend (<= 2pp jump); Low-base guard (total pledged <= 0.5%)",
    3: "RPT sales+purchases <= 5% of revenue; No suspicious unlisted affiliate loans",
    4: "Contingent liabilities <= 15% of net worth; Net worth > 0",
    5: "Cumulative 5y CFO / PAT >= 0.80; Negative CFO years <= 2; Cumulative PAT > 0",
    6: "CFO changes <= 1 in trailing 3 years; No retroactive restatements of accounts",
}


def render_analyst_report(
    result: Phase1Result, input_data: CompanyInput
) -> Dict[str, Any]:
    """
    Renders the raw internal working table and provenance inspector for analysts.
    """
    rows: List[Dict[str, Any]] = []
    for c in result.checks:
        rows.append(
            {
                "check_id": c.check_id,
                "name": CHECK_TECHNICAL_TITLES.get(c.check_id, f"Check {c.check_id}"),
                "status": c.status.value,
                "reason_code": c.reason_code,
                "finding": c.finding,
                "threshold": CHECK_THRESHOLDS.get(c.check_id, "N/A"),
                "missing_data": c.missing_data,
                "citation": c.citation or "MISSING_CITATION",
                "basis": c.basis.value,
                "fields_used": c.fields_used,
            }
        )

    # Provenance items list
    prov_items = []
    for f_name, p in sorted(input_data.provenance.items()):
        prov_items.append(
            {
                "field_name": f_name,
                "source": p.source,
                "period": p.period,
                "basis": p.basis.value,
                "page": p.page,
                "confidence": p.confidence.value,
                "extracted_at": p.extracted_at,
            }
        )

    return {
        "result_id": result.result_id,
        "ticker": result.ticker,
        "as_of_date": result.as_of_date,
        "revision": result.revision,
        "supersedes": result.supersedes,
        "verdict": result.verdict.value,
        "company_type": result.company_type.value,
        "data_basis": result.data_basis.value if result.data_basis else None,
        "input_digest": result.input_digest,
        "generated_at": result.generated_at,
        "failing_checks": result.failing_checks,
        "inconclusive_checks": result.inconclusive_checks,
        "citation_gaps": result.citation_gaps,
        "rows": rows,
        "provenance_items": prov_items,
    }
