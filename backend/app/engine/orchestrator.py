"""
Master Orchestrator for Phase 1 Gatekeeper.
Strictly maps to Phase1-Algorithms.md §9.
Pure function — zero network or disk I/O.
"""

from datetime import datetime
import hashlib
from typing import List, Optional
import uuid

from backend.app.models.enums import CheckStatus, Verdict
from backend.app.models.schemas import CheckResult, CompanyInput, Phase1Result
from .checks import (
    check1_auditor_regulator,
    check2_promoter_pledge,
    check3_related_party,
    check4_contingent_liabilities,
    check5_cash_conversion,
    check6_executive_stability,
)
from .helpers import classify_company_type


def run_phase1(
    input_data: CompanyInput,
    prior: Optional[Phase1Result] = None,
) -> Phase1Result:
    """
    Evaluates all six checks against CompanyInput and produces a versioned Phase1Result.
    FAIL dominates INCONCLUSIVE.
    """
    # 1. Derive company type
    input_data.company_type = classify_company_type(
        govt_shareholding_pct=input_data.govt_shareholding_pct,
        promoter_holding_pct_of_company=input_data.promoter_holding_pct_of_company,
    )

    # 2. Evaluate ALL six checks — never short-circuit the evaluation itself
    results: List[CheckResult] = [
        check1_auditor_regulator(input_data),
        check2_promoter_pledge(input_data),
        check3_related_party(input_data),
        check4_contingent_liabilities(input_data),
        check5_cash_conversion(input_data),
        check6_executive_stability(input_data),
    ]

    failing = [r.check_id for r in results if r.status == CheckStatus.FAIL]
    inconclusive = [r.check_id for r in results if r.status == CheckStatus.INCONCLUSIVE]

    # 3. Decision table (Phase1-Rules.md §3 / Phase1-Algorithms.md §9)
    if failing:
        verdict = Verdict.REJECT
    elif inconclusive:
        verdict = Verdict.HOLD_INCONCLUSIVE
    else:
        verdict = Verdict.CLEARED_TO_PHASE_2

    # 4. Citation gaps: any field a PASS or FAIL relied on, but has no provenance entry
    citation_gaps_set = set()
    for r in results:
        if r.status != CheckStatus.INCONCLUSIVE:
            for f in r.fields_used:
                # Disregard synthetic or derived fields that don't need direct external provenance
                if f not in input_data.provenance and f != "pledged_pct_of_total_shares":
                    citation_gaps_set.add(f)
    citation_gaps = sorted(list(citation_gaps_set))

    # 5. Result versioning & input digest
    raw_digest = input_data.model_dump_json(exclude={"company_type"}).encode("utf-8")
    input_digest = hashlib.sha256(raw_digest).hexdigest()[:16]

    revision = 1 if prior is None else prior.revision + 1
    supersedes = None if prior is None else prior.result_id

    return Phase1Result(
        result_id=str(uuid.uuid4()),
        ticker=input_data.ticker,
        as_of_date=str(input_data.as_of_date),
        company_type=input_data.company_type,
        data_basis=input_data.data_basis,
        checks=results,
        verdict=verdict,
        failing_checks=failing,
        inconclusive_checks=inconclusive,
        revision=revision,
        supersedes=supersedes,
        input_digest=input_digest,
        generated_at=datetime.utcnow().isoformat() + "Z",
        citation_gaps=citation_gaps,
    )
