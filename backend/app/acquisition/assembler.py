"""
Assembler for Phase 1 Gatekeeper.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §6.
Turns AdapterResult[] into a CompanyInput + provenance map, enforcing
the §3 field coverage matrix, basis comparability, confidence floors,
and discrepancy flagging.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from backend.app.models.coverage import FIELD_COVERAGE_MATRIX
from backend.app.models.enums import (
    Confidence,
    ExtractionMethod,
    ReportingBasis,
)
from backend.app.models.schemas import (
    CompanyInput,
    FieldProvenance,
    RegulatoryActionInput,
    ReviewQueueItem,
)
from .types import AdapterResult, CompanyIdentity, ExtractedField

# Priority ordering for owner resolution (§6.3)
OWNER_PRIORITY = {
    "MANUAL": 100,
    "WorkbookUploadAdapter": 90,
    "AnnualReportAdapter": 80,
    "PDF tier 1 (D)": 80,
    "PDF tier 2 (D)": 75,
    "PDF tier 2/3 (D)": 70,
    "Screener (C)": 50,
    "ScreenerExportAdapter": 50,
    "ScreenerAdapter": 45,
    "Engine": 30,
}

CONFIDENCE_RANK = {
    Confidence.MANUAL: 5,
    Confidence.HIGH: 4,
    Confidence.MEDIUM: 3,
    Confidence.LOW: 2,
    Confidence.DERIVED: 1,
}


def satisfies_floor(conf: Confidence, floor_str: str) -> bool:
    """
    MANUAL always passes.
    Otherwise compares against floor enum rank.
    Phase1-PhaseC-Scraper-Implementation-Plan.md §5A.3
    """
    if conf == Confidence.MANUAL:
        return True
    floor_conf = Confidence(floor_str)
    return CONFIDENCE_RANK[conf] >= CONFIDENCE_RANK[floor_conf]


def assemble(
    identity: CompanyIdentity,
    as_of_date: str,
    basis: ReportingBasis,
    results: List[AdapterResult],
    manual_overrides: Optional[Dict[str, Any]] = None,
    uploader: Optional[str] = None,
) -> Tuple[CompanyInput, List[ReviewQueueItem]]:
    """
    Assembles extracted adapter results into CompanyInput with full provenance.
    Multi-document period-aware assembly per implementpdf.md Stage 4.
    """
    manual_overrides = manual_overrides or {}
    review_items: List[ReviewQueueItem] = []
    field_candidates: Dict[str, List[Tuple[ExtractedField, str]]] = {}

    # Derive fiscal year from as_of_date for period matching
    import re
    run_fy = "FY24"
    if as_of_date:
        m = re.search(r"20(\d{2})", as_of_date)
        if m:
            run_fy = f"FY{m.group(1)}"
    prior_fy = f"FY{int(run_fy[2:]) - 1}" if run_fy.startswith("FY") and run_fy[2:].isdigit() else "Prior FY"

    # Flatten extracted fields from all adapter results
    for res in results:
        for f in res.fields:
            if f.field_name not in field_candidates:
                field_candidates[f.field_name] = []
            field_candidates[f.field_name].append((f, res.adapter))

    populated_values: Dict[str, Any] = {}
    provenance_map: Dict[str, FieldProvenance] = {}

    # Stage 4.4: Cross-document comparative check for restatement detection
    # If two documents report the same (field, period) e.g. FY23 reported in AR23 vs AR24 comparative
    for field_name, candidates in field_candidates.items():
        if field_name in {"revenue", "net_worth", "legal_fees"} and len(candidates) >= 2:
            by_period: Dict[str, List[Tuple[ExtractedField, str]]] = {}
            for ef, adp in candidates:
                if ef.period and isinstance(ef.value, (int, float)):
                    by_period.setdefault(ef.period, []).append((ef, adp))
            for p, p_candidates in by_period.items():
                if len(p_candidates) >= 2:
                    v1 = float(p_candidates[0][0].value)
                    v2 = float(p_candidates[1][0].value)
                    # If material divergence (> 2%) between reported numbers for the same period across documents
                    if abs(v1 - v2) > max(1.0, 0.02 * max(abs(v1), abs(v2))):
                        populated_values["restatement_of_past_accounts"] = True
                        provenance_map["restatement_of_past_accounts"] = FieldProvenance(
                            field_name="restatement_of_past_accounts",
                            source=f"{p_candidates[0][0].source} vs {p_candidates[1][0].source}",
                            period=p,
                            basis=basis,
                            confidence=Confidence.HIGH,
                            extraction_method=ExtractionMethod.DERIVED,
                            raw_snippet=f"Material divergence in {field_name} for {p}: {v1} vs {v2}",
                            extracted_at=datetime.now(timezone.utc).isoformat(),
                            document_id=p_candidates[0][0].document_id,
                        )

    for field_name, candidates in field_candidates.items():
        meta = FIELD_COVERAGE_MATRIX.get(field_name)
        if not meta:
            continue

        target_period = prior_fy if field_name == "legal_fees_prior_year" else run_fy

        def candidate_sort_key(item: Tuple[ExtractedField, str]):
            ef, adapter_name = item
            # Exact period match gets highest score
            period_score = 2 if ef.period == target_period else (1 if not ef.period or ef.period == "NOT_APPLICABLE" else 0)
            return (
                period_score,
                OWNER_PRIORITY.get(adapter_name, 10),
                CONFIDENCE_RANK.get(ef.confidence, 0),
            )

        # Sort candidates by period alignment, then owner priority, then confidence
        candidates.sort(key=candidate_sort_key, reverse=True)

        chosen_field: Optional[ExtractedField] = None
        chosen_adapter: Optional[str] = None

        # Check for discrepancy if multiple adapters supply numeric fields (e.g. pledge %)
        if len(candidates) >= 2 and isinstance(candidates[0][0].value, (int, float)) and isinstance(candidates[1][0].value, (int, float)):
            val1 = float(candidates[0][0].value)
            val2 = float(candidates[1][0].value)
            if abs(val1 - val2) > 1.0:  # > 1 percentage point gap
                review_items.append(
                    ReviewQueueItem(
                        id=str(uuid.uuid4()),
                        company_id=identity.ticker,
                        ticker=identity.ticker,
                        check_id=meta.get("check") or 0,
                        field_name=field_name,
                        best_guess_value=val1,
                        period=candidates[0][0].period,
                        basis=candidates[0][0].basis,
                        raw_snippet=f"{candidates[0][1]}: {val1} vs {candidates[1][1]}: {val2}",
                        reason=f"Discrepancy > 1pp between sources: {candidates[0][1]}={val1} vs {candidates[1][1]}={val2}",
                    )
                )

        for ef, adapter_name in candidates:
            # 1. Basis filter rule (§6.1)
            if (
                meta.get("basis_required", False)
                and ef.basis != ReportingBasis.NOT_APPLICABLE
                and ef.basis != basis
            ):
                review_items.append(
                    ReviewQueueItem(
                        id=str(uuid.uuid4()),
                        company_id=identity.ticker,
                        ticker=identity.ticker,
                        check_id=meta.get("check") or 0,
                        field_name=field_name,
                        best_guess_value=ef.value,
                        period=ef.period,
                        basis=ef.basis,
                        raw_snippet=ef.raw_snippet,
                        reason=f"Mismatched basis: field is {ef.basis.value} but declared run basis is {basis.value}",
                    )
                )
                continue  # drop candidate

            # 2. Confidence floor check (§6.2)
            floor_str = meta.get("confidence_floor", "HIGH")
            if not satisfies_floor(ef.confidence, floor_str):
                review_items.append(
                    ReviewQueueItem(
                        id=str(uuid.uuid4()),
                        company_id=identity.ticker,
                        ticker=identity.ticker,
                        check_id=meta.get("check") or 0,
                        field_name=field_name,
                        best_guess_value=ef.value,
                        period=ef.period,
                        basis=ef.basis,
                        raw_snippet=ef.raw_snippet,
                        reason=f"Confidence {ef.confidence.value} below required floor {floor_str}",
                    )
                )
                continue  # below floor, stays null

            # 3. Near-threshold escalation for MEDIUM numeric values (§5.3)
            if ef.confidence == Confidence.MEDIUM and isinstance(ef.value, (int, float)):
                review_items.append(
                    ReviewQueueItem(
                        id=str(uuid.uuid4()),
                        company_id=identity.ticker,
                        ticker=identity.ticker,
                        check_id=meta.get("check") or 0,
                        field_name=field_name,
                        best_guess_value=ef.value,
                        period=ef.period,
                        basis=ef.basis,
                        raw_snippet=ef.raw_snippet,
                        reason=f"Near-threshold escalation for MEDIUM confidence figure: {ef.value}",
                    )
                )

            chosen_field = ef
            chosen_adapter = adapter_name
            break  # highest priority valid candidate selected

        if chosen_field:
            populated_values[field_name] = chosen_field.value
            provenance_map[field_name] = FieldProvenance(
                field_name=field_name,
                source=chosen_field.source,
                period=chosen_field.period,
                basis=chosen_field.basis,
                page=chosen_field.page,
                confidence=chosen_field.confidence,
                extraction_method=chosen_field.extraction_method,
                raw_snippet=chosen_field.raw_snippet,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                document_id=chosen_field.document_id,
            )

    # 6. Manual overrides win (§6.6)

    for f_name, val in manual_overrides.items():
        if val is not None and f_name in FIELD_COVERAGE_MATRIX:
            populated_values[f_name] = val
            meta = FIELD_COVERAGE_MATRIX[f_name]
            field_period = prior_fy if f_name == "legal_fees_prior_year" else run_fy
            provenance_map[f_name] = FieldProvenance(
                field_name=f_name,
                source=f"Manual Override by {uploader or 'analyst'}",
                period=field_period,
                basis=basis if meta.get("basis_required", False) else ReportingBasis.NOT_APPLICABLE,
                confidence=Confidence.MANUAL,
                extraction_method=ExtractionMethod.MANUAL,
                extracted_at=datetime.now(timezone.utc).isoformat(),
            )

    # Construct CompanyInput model
    regulatory_action = populated_values.get("regulatory_action")
    if not isinstance(regulatory_action, RegulatoryActionInput):
        regulatory_action = RegulatoryActionInput()

    company_input = CompanyInput(
        ticker=identity.ticker,
        as_of_date=as_of_date,
        data_basis=basis,
        auditor_resigned_mid_tenure_last_3y=populated_values.get("auditor_resigned_mid_tenure_last_3y"),
        audit_opinion=populated_values.get("audit_opinion"),
        regulatory_action=regulatory_action,
        legal_fees=populated_values.get("legal_fees"),
        audit_fees=populated_values.get("audit_fees"),
        legal_fees_prior_year=populated_values.get("legal_fees_prior_year"),
        industry_sector=populated_values.get("industry_sector"),
        legal_fee_surge_explained=populated_values.get("legal_fee_surge_explained"),
        govt_shareholding_pct=populated_values.get("govt_shareholding_pct"),
        promoter_holding_pct_of_company=populated_values.get("promoter_holding_pct_of_company"),
        pledged_pct_of_promoter_holding=populated_values.get("pledged_pct_of_promoter_holding"),
        pledged_pct_history_last_4q=populated_values.get("pledged_pct_history_last_4q"),
        pledged_pct_history_retrieval_tier=populated_values.get("pledged_pct_history_retrieval_tier"),
        pledged_pct_of_total_shares=populated_values.get("pledged_pct_of_total_shares"),
        rpt_sales_plus_purchases=populated_values.get("rpt_sales_plus_purchases"),
        revenue=populated_values.get("revenue"),
        unusual_affiliate_dealings=populated_values.get("unusual_affiliate_dealings"),
        net_worth=populated_values.get("net_worth"),
        litigation_claims_exposure=populated_values.get("litigation_claims_exposure"),
        routine_guarantee_exposure=populated_values.get("routine_guarantee_exposure"),
        contingent_liabilities=populated_values.get("contingent_liabilities"),
        contingent_liabilities_breakdown_available=populated_values.get("contingent_liabilities_breakdown_available"),
        cfo_last_5y=populated_values.get("cfo_last_5y"),
        pat_last_5y=populated_values.get("pat_last_5y"),
        working_capital_cycle_tier=populated_values.get("working_capital_cycle_tier"),
        revenue_last_5y=populated_values.get("revenue_last_5y"),
        cumulative_working_capital_change_5y=populated_values.get("cumulative_working_capital_change_5y"),
        liquid_cushion_first_year=populated_values.get("liquid_cushion_first_year"),
        liquid_cushion_last_year=populated_values.get("liquid_cushion_last_year"),
        years_5y_series_gap_checked=populated_values.get("years_5y_series_gap_checked"),
        cfo_changes_last_3y=populated_values.get("cfo_changes_last_3y"),
        restatement_of_past_accounts=populated_values.get("restatement_of_past_accounts"),
        restatement_search_retrieval_tier=populated_values.get("restatement_search_retrieval_tier"),
        restatement_esg_only_excluded=populated_values.get("restatement_esg_only_excluded"),
        years_of_track_record_available=populated_values.get("years_of_track_record_available"),
        provenance=provenance_map,
    )

    return company_input, review_items
