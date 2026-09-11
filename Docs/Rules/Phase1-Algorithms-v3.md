Phase 1 Gatekeeper — Algorithm Specification

Implementation-ready pseudocode for every check in Phase1-Rules.md. This file is the bridge between the rules doc (human-readable policy) and an application (deterministic code). Every function below maps 1:1 to a section of Phase1-Rules.md — thresholds, exceptions, and edge cases are copied verbatim, not reinterpreted. If the rules file is ever updated, update this file in the same commit.

Status values used throughout: PASS, FAIL, INCONCLUSIVE. Never a numeric score.

Revision 3 (see §13) adds explicit sourcing-confidence plumbing and years-available disclosure, closing three gaps a live run (Cyient DLM, Sep 2026) exposed: a FAIL reached on a partial track record didn't say so in its own finding text; a pledge-trend PASS could be reached from a single data point without flagging that it wasn't the full quarterly series; and "no regulatory action" / "no restatement" findings carried the same confidence whether they came from the named primary registry or a generic web pass. No threshold, exception, or decision rule changed — every number here is still exactly what Phase1-Rules.md §2 and §3 say. Revision 2's provenance/citation plumbing, comparability guards, and versioning are unchanged and retained below.

Revision 4 (see §13) replaces Check 1.4's flat "legal fees > 5x audit fees / >2x YoY surge" thresholds with a revenue-normalized, industry-tiered test, per Phase1-Rules-v2.md §2 Check 1.4 and new §8.4-E. This is a genuine threshold/metric change, unlike Revision 3's sourcing-only changes — see §3 (Check 1) and §2f below, and the Revision 4 entry in §13 for full rationale and traceability.

Revision 5 (see §13) replaces Check 4's flat "contingent liabilities > 15% of net worth" rule with a litigation-vs-routine split (Schedule III sub-categories), and Check 5's flat "CFO/PAT < 0.80, >=3-of-5-years-negative" rule with working-capital-cycle tiering plus a global 0.50 hard floor and an explicit not-applicable path for lending institutions — per Phase1-Rules-v2.md §2 Checks 4 and 5, and new §8.4-F / §8.4-G. Both are genuine threshold/metric changes. See §6 (Check 4), §7 (Check 5), §2g, and the Revision 5 entry in §13.

Revision 6 (see §13) adds a use-of-funds verification override to Check 5 (Phase1-Rules-v2.md §2 Check 5, new §8.4-H), prompted by a live Phase 1 run on GRSE that breached even the Revision 5 hard floor by a wide margin in a way a follow-up forensic trace showed was overwhelmingly explained by working-capital absorption behind genuine revenue growth. Every Check 5 disqualifying trigger except cumulative PAT <= 0 is now routed through verify_use_of_funds() (§2h) before resolving — a verified-benign shortfall becomes a PASS carrying has_mandatory_warning = true (Phase1Result.warning_checks), never a silent PASS and never an automatic FAIL. This is a genuine, narrowly-scoped policy change — see §7 (Check 5), §2h, and the Revision 6 entry in §13.

0. Data model (inputs)
enum CompanyType { PRIVATE_PROMOTER, GOVT_PSU, PROFESSIONALLY_MANAGED }
enum ReportingBasis { CONSOLIDATED, STANDALONE, NOT_APPLICABLE }
enum Confidence { HIGH, MEDIUM, LOW, MANUAL, DERIVED }
// Rev 4 — Rules §8.4-E sector tiers for the legal-fee-anomaly sub-check (Check 1.4).
// TIER5_OTHER is the conservative default when classification is unavailable — never
// silently default to a low-intensity tier, per Rules §8.4-E step 5.
enum IndustrySector {
  TIER1_FINANCIAL_SERVICES, TIER2_PHARMA_HEALTHCARE_IT, TIER3_REGULATED_GOVT_TELECOM_ENERGY,
  TIER4_MANUFACTURING_INDUSTRIALS, TIER5_RETAIL_FMCG_CONSUMER, TIER_OTHER_UNCLASSIFIED
}
// Rev 5 — Rules §8.4-G tiers for Check 5's cash-conversion test. Deliberately a
// separate axis from IndustrySector above: legal-spend intensity (Check 1) and
// working-capital-cycle length (Check 5) classify the same company differently —
// e.g. IT/Technology is TIER2 (elevated legal intensity) but SHORT_CYCLE_ASSET_LIGHT
// (tight cash conversion) — so the two enums must never be conflated or reused for
// each other's lookup.
enum WorkingCapitalCycleTier {
  LONG_CYCLE_PROJECT_ACCOUNTING, MODERATE_CYCLE, SHORT_CYCLE_ASSET_LIGHT,
  LENDING_INSTITUTION_NA, TIER_OTHER_UNCLASSIFIED
}

// Provenance is a first-class input, not an afterthought. Rules §1 requires
// "cite the source and period for each" data point, and CheckResult.citation below
// is required whenever a number is used. A scalar with no provenance cannot be cited,
// so the engine must be handed both.
struct FieldProvenance {
  field_name: string
  source: string                 // e.g. "Screener.in consolidated", "TATAMOTORS_AR_FY24.pdf"
  period: string                 // e.g. "FY24", "Q1FY25", "FY20-FY24" — the period the value covers
  basis: ReportingBasis          // NOT_APPLICABLE for non-financial fields (e.g. audit opinion)
  page: int | null               // PDF page, null for HTML sources
  url: string | null
  confidence: Confidence
  extracted_at: date
}

// New in Revision 3. Distinguishes "this field is populated" from "this field came from
// the primary source the rules require" (Phase1-Rules.md §8.4). A field can be non-null
// and still be sourced from a documented fallback — that is a real, common, and legitimate
// outcome — but the engine must not let it look identical to a primary-source finding.
enum RetrievalTier {
  PRIMARY              // sourced exactly as §8.4 specifies (named registry / full series)
  FALLBACK             // sourced via the documented fallback path, confidence downgraded
  UNAVAILABLE          // neither path worked; field is null, handled by the golden rule as usual
}

struct CompanyInput {
  ticker: string
  as_of_date: date
  company_type: CompanyType          // derived by classify_company_type() below

  // Reporting basis this run is being evaluated on. Rules §8.1 prefers consolidated.
  // Every financial field must agree with this — see assert_comparable() in §2b.
  data_basis: ReportingBasis | null

  // Check 1 — Auditor & Regulator
  auditor_resigned_mid_tenure_last_3y: bool | null
  audit_opinion: enum { CLEAN, QUALIFIED, ADVERSE, DISCLAIMER } | null
  regulatory_action: {
    active_or_past_5y: bool | null
    nature: enum { FRAUD, SIPHONING, MANIPULATION, ACCOUNTING_IRREGULARITY,
                    ROUTINE_PROCEDURAL, NONE } | null
    retrieval_tier: RetrievalTier | null   // new in Rev 3 — was this sourced per §8.4-A?
  }
  legal_fees: number | null            // latest FY, currency units
  audit_fees: number | null            // latest FY, currency units — Rev 4: secondary/
                                        // corroboration only, no longer a required field
                                        // for this check, see §3 fee-anomaly sub-check
  legal_fees_prior_year: number | null // for surge check
  industry_sector: IndustrySector | null   // Rev 4 — NSE/BSE sector tag, mapped via
                                            // sector_flag_threshold() in §2f
  legal_fee_surge_explained: bool | null   // Rev 4 — true only if a disclosed one-off
                                            // cause for a >2x YoY legal-fee increase was
                                            // found (Contingent Liabilities note, Board's
                                            // Report, or news) per Rules §8.4-E step 4

  // Check 2 — Promoter Pledge
  govt_shareholding_pct: number | null       // central+state, direct+indirect
  promoter_holding_pct_of_company: number | null   // promoter shares / total shares outstanding
  pledged_pct_of_promoter_holding: number | null   // latest quarter
  pledged_pct_history_last_4q: number[] | null     // oldest -> newest, same metric
  pledged_pct_history_retrieval_tier: RetrievalTier | null
      // new in Rev 3 — PRIMARY if this is an actual quarterly-filed series per §8.4-B;
      // FALLBACK if inferred from a single latest-quarter figure plus a compliance filing
      // confirming "no new pledge created" (see derive path in §2c note below)
  pledged_pct_of_total_shares: number | null       // for low-base guard; may be derived, see §2c

  // Check 3 — Related Party Transactions
  rpt_sales_plus_purchases: number | null
  revenue: number | null                    // same statement, same FY, same basis as the RPT note.
                                             // Rev 4: also consumed by Check 1's fee-anomaly
                                             // sub-check (§8.4-E) — same comparability requirement.
  unusual_affiliate_dealings: bool | null   // large/unexplained loans/deals w/ unlisted affiliates

  // Check 4 — Contingent Liabilities. Rev 5 — Rules §2 Check 4 / §8.4-E: the flat
  // total-contingent-liabilities ratio is replaced by a litigation-vs-routine split,
  // since Schedule III already requires the sub-category breakdown (see §8.4-F).
  net_worth: number | null                  // total equity / shareholders' funds, same FY & basis
  litigation_claims_exposure: number | null // Rev 5 — claims not acknowledged as debts +
                                             // disputed tax demands + contested claims +
                                             // related-party guarantees outside ordinary course
  routine_guarantee_exposure: number | null // Rev 5 — ordinary-course guarantees/LCs + bills
                                             // discounted; retained for citation, excluded
                                             // from the FAIL ratio entirely (§8.4-F)
  contingent_liabilities: number | null     // Rev 5 — retained only as the lump-total fallback
                                             // when the AR does not disclose a sub-category
                                             // breakdown; see check4's immateriality fast-path
  contingent_liabilities_breakdown_available: bool | null  // Rev 5 — true only if the Schedule
                                             // III sub-categories were actually extracted
                                             // separately, per §8.4-F step 1

  // Check 5 — Cash Conversion (up to 5 fiscal years, oldest -> newest)
  cfo_last_5y: number[] | null   // cash from operations, len <= 5
  pat_last_5y: number[] | null   // profit after tax, len <= 5
  working_capital_cycle_tier: WorkingCapitalCycleTier | null  // Rev 5 — Rules §8.4-G;
      // LENDING_INSTITUTION_NA routes this check to INCONCLUSIVE instead of a ratio
  // Rev 6 — Rules §8.4-H use-of-funds verification fields. Consumed only when a
  // disqualifying trigger actually fires; not required for a company that clears the
  // ratio/negative-years tests outright.
  revenue_last_5y: number[] | null      // same FY alignment/basis as cfo_last_5y/pat_last_5y
  cumulative_working_capital_change_5y: number | null
      // the Cash Flow Statement's own "Changes in working capital" reconciling subtotal
      // (Ind AS 7 indirect method), summed across the same 5 years — a direct AR
      // extraction, never derived by summing individual balance-sheet note movements
  liquid_cushion_first_year: number | null   // cash & equivalents + other bank balances
      // (incl. FDs) + current investments, Balance Sheet, FIRST year of the 5y window
  liquid_cushion_last_year: number | null    // same composition, LAST year of the window
  years_5y_series_gap_checked: bool | null
      // new in Rev 3 — true only if the §8.4-C completeness sub-step (Screener extended
      // view / RHP-DRHP / older AR) was actually attempted before accepting a short series.
      // false or null means the series may be short simply because no one looked further.

  // Check 6 — Executive Stability
  cfo_changes_last_3y: int | null
  restatement_of_past_accounts: bool | null
  restatement_search_retrieval_tier: RetrievalTier | null
      // new in Rev 3 — PRIMARY if sourced per §8.4-D (targeted terms + Emphasis of Matter
      // review); FALLBACK if only a general keyword scan of extracted text was performed
  restatement_esg_only_excluded: bool | null
      // new in Rev 3 — true if a restatement-shaped mention WAS found but confirmed to be
      // an ESG/BRSR data restatement rather than a financial one (§8.4-D disambiguation).
      // Recorded so the finding text can show the distinction was checked, not assumed.

  // Data availability. Nullable on purpose: "we did not establish the listing/reporting
  // history" is NOT the same as "0 years", and must never silently force every
  // window-guarded check to INCONCLUSIVE-by-accident or PASS-by-accident.
  years_of_track_record_available: int | null   // company's actual listed/reporting history

  // field_name -> provenance. A field present here but absent from provenance is
  // usable for evaluation but produces a null citation (see §2b) and is reported as
  // a sourcing gap, never silently.
  provenance: map<string, FieldProvenance>
}

struct CheckResult {
  check_id: int                 // 1-6
  status: PASS | FAIL | INCONCLUSIVE
  finding: string                // human-readable, numbers + thresholds, e.g. "pledge 12% vs 10% limit"
                                  // Rev 3: for Checks 1, 5, 6, MUST include "(N of M years)" whenever
                                  // years_available < years_required — see build_finding_suffix() in §2d
  reason_code: string            // machine-readable, e.g. "PLEDGE_ABOVE_10PCT"
  missing_data: string | null    // populated only when INCONCLUSIVE
  fields_used: string[]          // CompanyInput field names this result actually depended on
  citation: string | null        // source + period, required whenever a number is used
  basis: ReportingBasis          // basis the numbers in this result were computed on
  confidence: Confidence         // new in Rev 3 — rolled up from the retrieval tiers of the
                                  // fields_used; HIGH if all PRIMARY, MEDIUM if any FALLBACK,
                                  // unchanged (MANUAL/DERIVED etc.) if a field already carried
                                  // a more specific tag — see roll_up_confidence() in §2d
  has_mandatory_warning: bool     // new in Rev 6 — true only for a Check 5 PASS reached via
                                  // the §8.4-H use-of-funds override. Defaults false for every
                                  // other check and every ordinary Check 5 PASS. Forces the
                                  // renderer (§10) to produce the dedicated warning paragraph
                                  // from Rules §5d — never a silent PASS.
}

struct Phase1Result {
  result_id: uuid
  ticker: string
  as_of_date: date
  company_type: CompanyType
  data_basis: ReportingBasis | null
  checks: CheckResult[6]
  verdict: REJECT | CLEARED_TO_PHASE_2 | HOLD_INCONCLUSIVE
  failing_checks: int[]           // check_ids where status == FAIL
  inconclusive_checks: int[]      // check_ids where status == INCONCLUSIVE
  low_confidence_checks: int[]    // new in Rev 3 — check_ids where confidence != HIGH,
                                  // regardless of PASS/FAIL — surfaced to the renderer so
                                  // §5's confidence-labelling requirement can't be skipped
  warning_checks: int[]           // new in Rev 6 — check_ids where has_mandatory_warning
                                  // == true (today, only ever [5] or []). Never affects
                                  // verdict — a warning-flagged check already resolved to
                                  // PASS — its only job is to force the renderer's §5d
                                  // dedicated warning paragraph, same pattern as
                                  // low_confidence_checks for confidence disclosure.

  // Versioning. A verdict can legitimately change when a manual review resolves a
  // previously-missing field (HOLD -> REJECT or HOLD -> CLEARED). Anything already
  // published to a user must therefore be identifiable as superseded.
  revision: int                   // 1 for the first evaluation of (ticker, as_of_date)
  supersedes: uuid | null         // prior revision's result_id
  input_digest: string            // hash of CompanyInput + provenance; lets a stored
                                  // report be tested for staleness without re-running
  generated_at: timestamp

  citation_gaps: string[]         // field names used in a verdict but lacking provenance
}

Golden rule for every function below: if a required input field is null (not merely zero/false — a real "we could not find this"), the check returns INCONCLUSIVE, never a guessed PASS or FAIL. Zero and false are valid data points, not missing data; do not conflate "0%" with "unknown."

Corollaries from Revision 2, retained unchanged:

Never compute a ratio across mismatched basis or period. A consolidated RPT figure over a standalone revenue, or an FY24 contingent liability over an FY23 net worth, produces a number that looks confident and is wrong. Mismatch is missing data, so it returns INCONCLUSIVE (§2b).
Never manufacture a FAIL out of an unusable input. If a denominator is zero or a sub-check cannot be computed, that sub-check is INCONCLUSIVE; it does not join the fail list (see the Check 1 fix in §3).

New corollary in Revision 3, derived from Rules §1a and §8.4 — not a new policy threshold:

A field being non-null does not mean it was fully sourced. A FALLBACK-tier field is still usable — the golden rule about nulls is unchanged — but it must never be presented with the same confidence as a PRIMARY-tier field. Confidence is a property of how a non-null value was obtained, tracked separately from whether it is null.
1. Helper: company type classification

Feeds Check 2's auto-pass exceptions. Run this once per company before the checks. (Unchanged from Revision 2.)

function classify_company_type(govt_shareholding_pct, promoter_holding_pct_of_company) -> CompanyType:
    if govt_shareholding_pct is not null and govt_shareholding_pct >= 51:
        return GOVT_PSU
    if promoter_holding_pct_of_company is not null and promoter_holding_pct_of_company == 0:
        return PROFESSIONALLY_MANAGED
    return PRIVATE_PROMOTER

Note: a partially-disinvested former PSU with govt stake < 51% is PRIVATE_PROMOTER for this classifier and gets no auto-pass — per rules §2, Check 2.

Note on acquisition: govt_shareholding_pct being null does not make a company PRIVATE_PROMOTER by evidence — it makes it PRIVATE_PROMOTER by default, which then routes into Check 2's normal path and its own null-checks. That is the correct conservative behaviour (a company is not granted a PSU auto-pass on missing data), but it means the acquisition layer must actually retrieve government shareholding rather than leaving it null. See the field-coverage matrix in the implementation plan §3.

2. Helper: track-record sufficiency guard

Applies to Checks 1, 5, 6 (lookback windows of 3, 5, 3 years respectively). Wrap the core FAIL logic of those checks with this guard.

function apply_track_record_guard(years_required, years_available, disqualifying_event_found) -> Status | null:
    // Returns a forced status, or null meaning "proceed to normal evaluation"

    if years_available is null:
        // We do not know the history length. A real disqualifying event still fails
        // (rules §1: "a short history can still fail"); otherwise we cannot certify
        // that the full window was examined, so we cannot PASS.
        if disqualifying_event_found:
            return FAIL
        return INCONCLUSIVE   // "track record length not established"

    if years_available >= years_required:
        return null   // full window available, evaluate normally
    if disqualifying_event_found:
        return FAIL   // a short history can still fail — never blocked by insufficient data
    return INCONCLUSIVE   // "insufficient track record (only N years available)"

Each check function calls this first and short-circuits if it returns non-null. Rev 3 change: the caller (not this helper) is now responsible for appending the "(N of M years)" suffix to the finding text whenever this guard fires with years_available < years_required — see build_finding_suffix() in §2d. This closes the v1 gap where a FAIL reached through the second branch above carried no indication in its own finding text that the window was short. The guard's return value is unchanged; only what callers do with a non-null FAIL return from it has changed.

2a. Helper: citation composition

CheckResult.citation is required whenever a number is used. It is built from the provenance of exactly the fields the check consumed — never hand-written, never inferred. (Unchanged from Revision 2.)

function compose_citation(input: CompanyInput, field_names: string[]) -> (string | null, string[]):
    // returns (citation, missing_provenance_field_names)

    cited = []
    missing = []
    for f in field_names:
        if input.provenance has key f:
            p = input.provenance[f]
            basis_part = (p.basis == NOT_APPLICABLE) ? "" : " (" + p.basis + ")"
            page_part  = (p.page is null) ? "" : ", p." + p.page
            cited.append(f + ": " + p.source + " " + p.period + basis_part + page_part
                           + " [" + p.confidence + "]")
        else:
            missing.append(f)

    if cited is empty:
        return (null, missing)
    return (join("; ", cited), missing)

A null or partial citation never blocks a verdict — the numbers are still the numbers — but every gap propagates to Phase1Result.citation_gaps, and §10 requires the renderer to surface it as missing sourcing rather than presenting an uncited figure as sourced.

2b. Helper: comparability guard (basis + period)

Applies to every check that divides one reported figure by another: Check 1's legal/audit fee ratio, Check 3, Check 4, Check 5. (Unchanged from Revision 2.)

function assert_comparable(input: CompanyInput, field_names: string[]) -> string | null:
    // returns an explanation string if the fields cannot be validly compared, else null

    provs = [input.provenance[f] for f in field_names if input.provenance has key f]
    if length(provs) < 2:
        return null    // nothing to cross-check; citation_gaps already records the gap

    financial = [p for p in provs if p.basis != NOT_APPLICABLE]

    bases = distinct(p.basis for p in financial)
    if length(bases) > 1:
        return "mixed reporting basis across " + field_names + ": " + bases
               + " — consolidated and standalone figures are not comparable"

    if input.data_basis is not null and length(bases) == 1 and bases[0] != input.data_basis:
        return "figures are " + bases[0] + " but this run is declared "
               + input.data_basis

    periods = distinct(p.period for p in provs)
    if length(periods) > 1:
        return "figures span different periods " + periods
               + " — a ratio across periods is not a valid comparison"

    return null

Callers treat a non-null return as missing data: INCONCLUSIVE, with the returned string as missing_data. Multi-year series (cfo_last_5y, pat_last_5y, pledged_pct_history_last_4q) carry one provenance entry describing the whole span (e.g. period: "FY20-FY24"), so the period check compares spans, not individual years.

2c. Helper: derived pledge base

pledged_pct_of_total_shares is an exact arithmetic identity, not an estimate, so deriving it is not a violation of the golden rule. A directly reported value always wins over a derived one. (Unchanged from Revision 2; see §2e for the new, separate pledge-trend fallback, which is a different field and a genuine sourcing weakening, not an arithmetic derivation.)

function derive_pledged_pct_of_total_shares(input: CompanyInput) -> number | null:
    if input.pledged_pct_of_total_shares is not null:
        return input.pledged_pct_of_total_shares          // reported value wins

    if input.promoter_holding_pct_of_company is null
       or input.pledged_pct_of_promoter_holding is null:
        return null

    // (promoter's % of company) x (pledged % of that holding)
    return input.promoter_holding_pct_of_company
           * input.pledged_pct_of_promoter_holding / 100

When this derives a value, the application must record provenance for it with confidence: DERIVED and a source naming both inputs, so the citation shows the derivation rather than implying a filed figure.

2d. Helper: finding-suffix and confidence roll-up (new in Revision 3)

Two small, mechanical helpers used by every check function below. Neither changes a threshold or a pass/fail outcome — both only change what the finding string says and what confidence value a CheckResult carries.

function build_finding_suffix(years_required: int | null, years_available: int | null) -> string:
    // Returns "" when the full window was available or years_required is not applicable
    // to this check (e.g. Checks 3 and 4 have no lookback window and never call this).
    if years_required is null or years_available is null:
        return ""
    if years_available >= years_required:
        return ""
    return f" (based on {years_available} of the required {years_required} years)"
function roll_up_confidence(input: CompanyInput, fields_used: string[],
                             retrieval_tier_fields: map<string, RetrievalTier | null>) -> Confidence:
    // retrieval_tier_fields maps a subset of fields_used to their RetrievalTier, where
    // applicable (only regulatory_action, pledged_pct_history_last_4q, and
    // restatement_of_past_accounts currently carry a tier — see §0).
    // A field with no tier entry is assumed PRIMARY (i.e. an ordinary Annual-Report or
    // balance-sheet figure with no fallback path defined for it).

    tiers = [retrieval_tier_fields.get(f, PRIMARY) for f in fields_used if f in retrieval_tier_fields]
    if length(tiers) == 0:
        return HIGH
    if any(t == UNAVAILABLE for t in tiers):
        return HIGH   // unreachable in practice — an UNAVAILABLE field is null and the
                       // check would already have returned INCONCLUSIVE before this is called
    if any(t == FALLBACK for t in tiers):
        return MEDIUM
    return HIGH

Every check function that touches regulatory_action, pledged_pct_history_last_4q, or restatement_of_past_accounts calls roll_up_confidence() when building its CheckResult, and appends build_finding_suffix(...) to the finding string wherever the track-record guard (§2) fired on a short window. See Checks 1, 2, 5, and 6 below for the exact call sites.

2f. Helper: sector flag-threshold lookup (new in Revision 4)

Feeds Check 1's fee-anomaly sub-check. Rules §8.4-E table, reproduced here as data rather than re-derived — if the table in the rules file changes, this map changes in the same edit, per §13's change-control rule.

function sector_flag_threshold(sector: IndustrySector) -> number:
    // Returns the flag threshold as a percentage-of-revenue figure (e.g. 1.35 means 1.35%).
    return {
        TIER1_FINANCIAL_SERVICES:           1.35,
        TIER2_PHARMA_HEALTHCARE_IT:         0.75,
        TIER3_REGULATED_GOVT_TELECOM_ENERGY: 0.68,
        TIER4_MANUFACTURING_INDUSTRIALS:    0.45,
        TIER5_RETAIL_FMCG_CONSUMER:         0.30,
        TIER_OTHER_UNCLASSIFIED:            0.75,
    }[sector]

Note on the last row: TIER_OTHER_UNCLASSIFIED intentionally uses the same threshold as Tier 2, not a looser one — Rules §8.4-E step 5 requires that an unclassified sector never default to a low-intensity (permissive) band, since that would under-flag rather than over-flag.

2g. Helper: working-capital-cycle threshold lookup (new in Revision 5)

Feeds Check 5's cash-conversion test. Rules §8.4-G table, reproduced here as data. Returns both the CFO/PAT flag threshold and the negative-CFO-years trigger for a tier, since §8.4-G ties them together.

function working_capital_cycle_thresholds(tier: WorkingCapitalCycleTier) -> {cfo_pat_floor: number, negative_years_trigger: int}:
    return {
        LONG_CYCLE_PROJECT_ACCOUNTING: {cfo_pat_floor: 0.65, negative_years_trigger: 4},
        MODERATE_CYCLE:                {cfo_pat_floor: 0.75, negative_years_trigger: 3},
        SHORT_CYCLE_ASSET_LIGHT:       {cfo_pat_floor: 0.85, negative_years_trigger: 3},
        TIER_OTHER_UNCLASSIFIED:       {cfo_pat_floor: 0.75, negative_years_trigger: 3},
        // LENDING_INSTITUTION_NA deliberately has no entry — check5 must branch to
        // INCONCLUSIVE before calling this function for that tier, never look up a
        // threshold for it. A missing-key lookup here is a caller bug, not a valid case.
    }[tier]

Note on TIER_OTHER_UNCLASSIFIED: uses the Moderate-cycle thresholds, the same "never default to the most lenient tier" principle as §2f — an unclassified non-lending company must not silently receive the Long-cycle tier's looser 0.65/4-years allowance.

The global backstops (cumulative PAT ≤ 0, cumulative CFO/PAT < 0.50) are not part of this lookup — they are checked directly in check5_cash_conversion() before the tier-specific thresholds, and apply regardless of tier or this function's return value. Rev 6 note: cumulative PAT ≤ 0 remains a true unconditional FAIL with no override anywhere in this spec; the 0.50 floor is no longer unconditional — as of Rev 6 it is one of three triggers eligible for the §2h use-of-funds verification override, same as the tier-specific ratio floor and the negative-years trigger. See §2h and check5_cash_conversion() below.

2h. Helper: use-of-funds verification (new in Revision 6)

Feeds Check 5. Rules §8.4-H's three conditions, reproduced as a single pure function — called at most once per check5_cash_conversion() invocation (Rules §8.4-H step 6), regardless of how many of the three disqualifying triggers actually fired.

function verify_use_of_funds(input: CompanyInput, cumulative_pat: number, cumulative_cfo: number) -> {verified: bool, notes: string[]} | null:
    // Returns null — not {verified: false} — if the fields needed to even attempt
    // verification are missing. Callers MUST treat null as "cannot verify," which
    // Rules §8.4-H step 4 requires to leave the disqualifying trigger as FAIL, not
    // silently pass it. This is a deliberate golden-rule application: an unattempted
    // verification is missing data, not a negative result.
    required = [revenue_last_5y, cumulative_working_capital_change_5y,
                liquid_cushion_first_year, liquid_cushion_last_year]
    if any(required) is null:
        return null
    if length(input.revenue_last_5y) < 2 or input.revenue_last_5y[0] <= 0:
        return null   // can't compute a first->last growth ratio

    notes = []

    // (a) Growth is real
    revenue_growth_ratio = last(input.revenue_last_5y) / input.revenue_last_5y[0]
    growth_ok = revenue_growth_ratio >= 1.5
    notes.append(f"(a) revenue grew {revenue_growth_ratio}x over the window "
                 f"(>= 1.5x required): {\"met\" if growth_ok else \"NOT met\"}")

    // (b) The shortfall is a working-capital story
    gap = cumulative_pat - cumulative_cfo
    if gap <= 0:
        return null   // verify_use_of_funds is only meaningful when there IS a
                       // shortfall to explain; callers only invoke this when a
                       // disqualifying trigger already implies gap > 0, but guard here too
    wc_coverage = abs(input.cumulative_working_capital_change_5y) / abs(gap)
    wc_ok = wc_coverage >= 0.60
    notes.append(f"(b) working-capital change covers {wc_coverage*100}% of the "
                 f"PAT-CFO gap (>= 60% required): {\"met\" if wc_ok else \"NOT met\"}")

    // (c) Not hoarding
    cushion_pct_first = input.liquid_cushion_first_year / input.revenue_last_5y[0]
    cushion_pct_last = input.liquid_cushion_last_year / last(input.revenue_last_5y)
    hoarding_ok = cushion_pct_last <= cushion_pct_first * 1.10
    notes.append(f"(c) liquid cushion is {cushion_pct_last*100}% of revenue in the "
                 f"latest year vs {cushion_pct_first*100}% in the first year "
                 f"(must not exceed a 10% rise): {\"met\" if hoarding_ok else \"NOT met\"}")

    return {verified: (growth_ok and wc_ok and hoarding_ok), notes: notes}

Note: all three conditions must hold — this is a logical AND, not a majority vote. A company that passes (a) and (b) but is quietly accumulating cash under (c) does NOT get the override; nor does a company with a flat working-capital shortfall who happens to hold a shrinking cushion under (c) but fails (b) (i.e. the shortfall isn't actually a working-capital story at all). The notes list is always returned alongside the verdict — even a failed verification must show its work, per Rules §8.4-H step 5.

3. Check 1 — Auditor & Regulator Integrity (Section A Q1)
function check1_auditor_regulator(input: CompanyInput) -> CheckResult:

    // Required fields. Rev 4: audit_fees dropped from this list — it is now secondary/
    // corroboration only (see the fee-anomaly sub-check below). revenue and
    // industry_sector added — they are what the primary fee-anomaly test now runs on.
    required = [auditor_resigned_mid_tenure_last_3y, audit_opinion,
                regulatory_action.active_or_past_5y, legal_fees, revenue, industry_sector]
    if any(required) is null:
        return INCONCLUSIVE("Check 1: missing one or more of "
                             "[auditor resignation history, audit opinion, "
                             "regulatory action status, legal fees, revenue, "
                             "industry sector classification]")

    years_available = input.years_of_track_record_available
    guard = apply_track_record_guard(
        years_required = 3,
        years_available = years_available,
        disqualifying_event_found = (
            input.auditor_resigned_mid_tenure_last_3y == true
            or input.audit_opinion != CLEAN
            or input.regulatory_action.nature in {FRAUD, SIPHONING, MANIPULATION, ACCOUNTING_IRREGULARITY}
        )
    )
    suffix = build_finding_suffix(3, years_available)   // Rev 3
    if guard is not null:
        return build_result(1, guard, finding_suffix = suffix)   // Rev 3: suffix always attached

    fail_reasons = []
    inconclusive_notes = []          // NOT the same list as fail_reasons — see below

    if input.auditor_resigned_mid_tenure_last_3y == true:
        fail_reasons.append("AUDITOR_RESIGNED_MID_TENURE")

    if input.audit_opinion != CLEAN:
        fail_reasons.append("AUDIT_OPINION_NOT_CLEAN:" + input.audit_opinion)

    if input.regulatory_action.active_or_past_5y == true
       and input.regulatory_action.nature in {FRAUD, SIPHONING, MANIPULATION, ACCOUNTING_IRREGULARITY}:
        fail_reasons.append("REGULATORY_ACTION:" + input.regulatory_action.nature)
    // Note: ROUTINE_PROCEDURAL nature is explicitly excluded — not a fail trigger.

    // Fee-anomaly sub-check (Rev 4 — Rules §2 Check 1.4 / §8.4-E). Primary test is
    // revenue-normalized and industry-tiered, not a flat multiple of audit fees: audit
    // fees carry a fixed-cost floor and do not scale linearly with revenue, so a flat
    // cross-company ratio systematically over-flags small/mid-caps and under-flags large
    // caps at identical legal intensity. Guarded for comparability first, same as Check 3.
    pass_notes = []           // Rev 4 — non-blocking observations folded into the PASS finding
    fee_mismatch = assert_comparable(input, ["legal_fees", "revenue"])
    if fee_mismatch is not null:
        inconclusive_notes.append("legal-fee-to-revenue check not computable: " + fee_mismatch)
    else if input.revenue <= 0:
        inconclusive_notes.append("revenue is zero/negative; legal-fee-to-revenue check undefined")
    else:
        legal_pct_revenue = (input.legal_fees / input.revenue) * 100
        flag_threshold = sector_flag_threshold(input.industry_sector)   // §2f
        surge = (input.legal_fees_prior_year is not null and input.legal_fees_prior_year > 0
                 and input.legal_fees / input.legal_fees_prior_year > 2
                 and input.legal_fee_surge_explained != true)
        if legal_pct_revenue > flag_threshold:
            fail_reasons.append("LEGAL_PCT_REVENUE_EXCEEDS_SECTOR_BAND:" + legal_pct_revenue
                                 + "%>" + flag_threshold + "% (" + input.industry_sector + ")")
        elif surge:
            fail_reasons.append("LEGAL_FEES_UNEXPLAINED_SURGE_OVER_2X_YOY")
        else:
            // Secondary corroboration only (Rules §8.4-E(c)) — never a standalone fail
            // trigger, because audit_fees is a confounded denominator. Surfaced as an
            // observation on the PASS finding, not as a fail_reason or inconclusive_note.
            secondary_mismatch = assert_comparable(input, ["legal_fees", "audit_fees"])
            if secondary_mismatch is null and input.audit_fees is not null and input.audit_fees > 0:
                ratio = input.legal_fees / input.audit_fees
                if ratio > 5:
                    pass_notes.append("legal/audit fee ratio " + ratio
                        + "x is elevated but legal spend is within the sector's "
                        + "revenue-intensity band, so not treated as a fail trigger")

    (citation, missing_prov) = compose_citation(input,
        ["audit_opinion", "auditor_resigned_mid_tenure_last_3y",
         "regulatory_action", "legal_fees", "revenue", "industry_sector"])

    // Rev 3: confidence roll-up, keyed on the regulatory_action field's retrieval tier
    // per Rules §8.4-A. A fallback-sourced "no action found" is MEDIUM even when it
    // contributes to a clean PASS finding, not just when it would have changed a FAIL.
    confidence = roll_up_confidence(input,
        fields_used = ["audit_opinion", "auditor_resigned_mid_tenure_last_3y",
                        "regulatory_action", "legal_fees", "revenue", "industry_sector"],
        retrieval_tier_fields = {"regulatory_action": input.regulatory_action.retrieval_tier})

    // FAIL dominates: a real disqualifying event still fails even if a sub-check
    // could not be computed. But an uncomputable sub-check on its own is INCONCLUSIVE
    // and must never be reported as a failure.
    if fail_reasons is non-empty:
        return FAIL(1, fail_reasons, finding = format_numbers(fail_reasons) + suffix,
                    citation, confidence)
    if inconclusive_notes is non-empty:
        return INCONCLUSIVE(1, missing_data = join("; ", inconclusive_notes), citation)
    note_suffix = (pass_notes is non-empty) ? " — " + join("; ", pass_notes) : ""
    return PASS(1, "clean opinion, no mid-tenure resignation, no disqualifying "
                   "regulatory action, legal spend within sector revenue-intensity band"
                   + note_suffix + suffix,
                citation, confidence)

Fix retained from Revision 2, restated for Rev 4's new denominator. An uncomputable sub-check (mismatched basis/period, or zero/negative revenue) is an INCONCLUSIVE sub-check, never folded into fail_reasons — a company with a clean opinion and an unparsable revenue figure is not rejected outright. Missing information is a hold, not a fail. (Revision 2's original zero-audit-fee case no longer applies the same way, since audit_fees is no longer required — see the Revision 4 changelog entry in §13 for the corresponding fixture 13 update.)

New in Revision 3. suffix (years-available disclosure) is now attached to every return path, not only the guard's own forced statuses — a normal-window FAIL or PASS gets an empty suffix, so nothing changes in the common case; the short-window case now always shows its shortfall. confidence is now computed and attached to every return path via roll_up_confidence(), keyed on whether the regulatory-action finding was sourced from the primary SEBI-archive query (Rules §8.4-A) or a generic fallback.

New in Revision 4. The fee-anomaly sub-check no longer treats a flat legal ÷ audit fee ratio as a fail trigger on its own — see Rules §8.4-E for why. It now runs primarily on legal_pct_revenue against an industry-tiered band (§2f), with the audit-fee ratio demoted to a pass_notes observation. The YoY surge trigger is now gated on legal_fee_surge_explained, so a disclosed one-off cause (e.g. M&A due diligence, a settlement, capital-raise legal costs) no longer forces a FAIL.

4. Check 2 — Promoter Pledge & Encumbrance (Section A Q2)
function check2_promoter_pledge(input: CompanyInput) -> CheckResult:

    // Auto-pass exceptions first — no data-availability check needed for these paths.
    // Rev 3 note: these auto-pass paths carry confidence: HIGH unconditionally — the
    // classification itself (govt >= 51%, or 0% promoter) does not depend on the pledge
    // trend at all, so the trend's retrieval tier is irrelevant here.
    if input.company_type == GOVT_PSU:
        return PASS(2, "Government PSU (govt shareholding >= 51%) — pledge check N/A",
                    confidence = HIGH)

    if input.company_type == PROFESSIONALLY_MANAGED:
        return PASS(2, "Zero promoter holding — no promoter shares exist to pledge",
                    confidence = HIGH)

    // Normal path requires these fields
    required = [promoter_holding_pct_of_company, pledged_pct_of_promoter_holding,
                pledged_pct_history_last_4q]
    if any(required) is null:
        return INCONCLUSIVE("Check 2: missing promoter holding %, latest pledge %, "
                             "or 4-quarter pledge history")

    trend_rising = detect_rising_trend(input.pledged_pct_history_last_4q)
        // rising trend = each quarter >= previous (allow ties), overall net increase,
        // OR any single-quarter jump > 2 percentage points vs prior quarter

    low_base = input.promoter_holding_pct_of_company < 5

    (citation, missing_prov) = compose_citation(input,
        ["promoter_holding_pct_of_company", "pledged_pct_of_promoter_holding",
         "pledged_pct_history_last_4q"])

    // Rev 3: confidence keyed on how pledged_pct_history_last_4q was actually sourced
    // per Rules §8.4-B — an actual quarterly series (PRIMARY) vs. a single figure plus a
    // "no new pledge" compliance filing standing in for a trend (FALLBACK).
    confidence = roll_up_confidence(input,
        fields_used = ["promoter_holding_pct_of_company", "pledged_pct_of_promoter_holding",
                        "pledged_pct_history_last_4q"],
        retrieval_tier_fields = {"pledged_pct_history_last_4q": input.pledged_pct_history_retrieval_tier})

    // Rev 3: a FALLBACK-tier trend cannot be used to positively assert "stable/declining" —
    // it can only confirm the latest figure and the absence of a *new* pledge. If the
    // absolute threshold already clears the company, say so but cap confidence at MEDIUM
    // and note explicitly that the trend leg is unconfirmed (Rules §5c). This does not
    // change the PASS/FAIL outcome — the absolute-threshold logic is untouched below —
    // it only prevents the trend sub-finding from overstating its own certainty.
    trend_finding_note = ""
    if input.pledged_pct_history_retrieval_tier == FALLBACK:
        trend_finding_note = (" (trend inferred from latest-quarter figure plus a "
                               "no-new-pledge compliance filing, not a confirmed quarterly series)")

    if low_base:
        pledged_of_total = derive_pledged_pct_of_total_shares(input)   // §2c
        if pledged_of_total is null:
            return INCONCLUSIVE("Check 2: promoter base < 5% of company; "
                                 "pledged % of total shares outstanding required but missing")

        fail_a = (input.pledged_pct_of_promoter_holding > 10
                  and pledged_of_total > 0.5)
        fail_b = pledge_material_vs_promoter_liquidity(input)  // qualitative check, defaults false if unknown/undeterminable — do not fabricate

        if fail_a or fail_b:
            return FAIL(2, "pledge material even after low-base adjustment: "
                           f"{input.pledged_pct_of_promoter_holding}% of promoter holding, "
                           f"{pledged_of_total}% of total shares" + trend_finding_note,
                        citation, confidence)
        else:
            return PASS(2, "pledge % elevated due to small promoter base, "
                           "not treated as a red flag" + trend_finding_note,
                        citation, confidence)

    // Standard thresholds
    if input.pledged_pct_of_promoter_holding > 10:
        return FAIL(2, f"pledge {input.pledged_pct_of_promoter_holding}% "
                       "vs 10% limit (absolute threshold)" + trend_finding_note,
                    citation, confidence)

    if trend_rising:
        return FAIL(2, "pledged % rising over last 2-4 quarters "
                       "(or unexplained single-quarter spike > 2pp)" + trend_finding_note,
                    citation, confidence)

    return PASS(2, f"pledge {input.pledged_pct_of_promoter_holding}% "
                   "(<= 10%), stable/declining over last 4 quarters" + trend_finding_note,
                citation, confidence)
function detect_rising_trend(history: number[]) -> bool:
    // history is oldest -> newest, length up to 4
    if length(history) < 2:
        return false   // not enough data to call a trend; caller still has the >10% absolute check
    if history[last] - history[first] > 0 and is_non_decreasing(history):
        return true
    for i in 1..length(history)-1:
        if history[i] - history[i-1] > 2:
            return true
    return false

New in Revision 3. trend_finding_note and the confidence roll-up are the only additions here — every FAIL/PASS branch and threshold is byte-identical to Revision 2. A FALLBACK-tier pledge history still lets the check resolve normally (this is not a new INCONCLUSIVE trigger); it only ensures the resulting finding text and confidence tag tell the renderer, and eventually the investor, that the trend leg rests on weaker evidence than the absolute-threshold leg.

5. Check 3 — Related-Party "Leakage" (Section A Q3)

Unchanged from Revision 2 — this check has no lookback window and no fallback-sourced field, so neither Revision 3 addition applies to it.

function check3_related_party(input: CompanyInput) -> CheckResult:

    required = [rpt_sales_plus_purchases, revenue, unusual_affiliate_dealings]
    if any(required) is null:
        return INCONCLUSIVE("Check 3: missing RPT sales+purchases, revenue, "
                             "or affiliate-dealings assessment")

    mismatch = assert_comparable(input, ["rpt_sales_plus_purchases", "revenue"])
    if mismatch is not null:
        return INCONCLUSIVE("Check 3: " + mismatch)

    if input.revenue <= 0:
        return INCONCLUSIVE("Check 3: revenue is zero/negative, RPT % undefined")

    rpt_pct = (input.rpt_sales_plus_purchases / input.revenue) * 100

    (citation, missing_prov) = compose_citation(input,
        ["rpt_sales_plus_purchases", "revenue", "unusual_affiliate_dealings"])

    if rpt_pct > 5:
        return FAIL(3, f"RPT {rpt_pct}% of revenue vs 5% limit", citation, confidence = HIGH)

    if input.unusual_affiliate_dealings == true:
        return FAIL(3, "large/unexplained loans or deals with promoter-owned unlisted affiliates",
                    citation, confidence = HIGH)

    return PASS(3, f"RPT {rpt_pct}% of revenue (<= 5%), no suspicious affiliate transactions",
                citation, confidence = HIGH)
6. Check 4 — Contingent Liabilities (Section A Q4)

Rev 5 (Rules §2 Check 4 / §8.4-F): the flat total-contingent-liabilities-over-net-worth
ratio is replaced by a litigation-vs-routine split, since Schedule III already requires
the sub-category breakdown and a blended total makes the ratio meaningless for banks,
NBFCs, and EPC/infrastructure contractors (routine guarantee/LC/forex business dwarfs
any genuine litigation exposure for those sectors). net_worth <= 0 remains an
unconditional FAIL, unchanged from Revision 2/3.

function check4_contingent_liabilities(input: CompanyInput) -> CheckResult:

    if input.net_worth is null:
        return INCONCLUSIVE("Check 4: missing net worth figure")

    if input.net_worth <= 0:
        (nw_citation, _) = compose_citation(input, ["net_worth"])
        return FAIL(4, f"net worth {input.net_worth} <= 0 (broken balance sheet)",
                    nw_citation, confidence = HIGH)

    // Rev 5 — §8.4-F step 4: an AR disclosing only a single lump total, with no Schedule
    // III sub-category breakdown, gets an immateriality fast-path rather than an
    // automatic hold, so a clearly-immaterial company is not needlessly blocked.
    if input.contingent_liabilities_breakdown_available != true:
        if input.contingent_liabilities is null:
            return INCONCLUSIVE("Check 4: no contingent liabilities figure "
                                 "(lump total or sub-category breakdown) available")
        mismatch = assert_comparable(input, ["contingent_liabilities", "net_worth"])
        if mismatch is not null:
            return INCONCLUSIVE("Check 4: " + mismatch)

        lump_pct = (input.contingent_liabilities / input.net_worth) * 100
        (lump_citation, _) = compose_citation(input, ["contingent_liabilities", "net_worth"])
        if lump_pct <= 5:
            return PASS(4, f"contingent liabilities {lump_pct}% of net worth (<= 5%, "
                           "immaterial — no Schedule III sub-category breakdown was "
                           "disclosed, but the total is small enough that a litigation/"
                           "routine split cannot change the verdict)",
                        lump_citation, confidence = MEDIUM)
        return INCONCLUSIVE(f"Check 4: contingent liabilities disclosed as a single total "
                             f"({lump_pct}% of net worth) with no Schedule III sub-category "
                             "breakdown — litigation/routine split not available (§8.4-F)")

    // Primary path: the litigation/routine breakdown was extracted per §8.4-F.
    if input.litigation_claims_exposure is null:
        return INCONCLUSIVE("Check 4: breakdown flagged available but "
                             "litigation_claims_exposure missing")

    mismatch = assert_comparable(input, ["litigation_claims_exposure", "net_worth"])
    if mismatch is not null:
        return INCONCLUSIVE("Check 4: " + mismatch)

    (citation, missing_prov) = compose_citation(input,
        ["litigation_claims_exposure", "routine_guarantee_exposure", "net_worth"])

    ratio_pct = (input.litigation_claims_exposure / input.net_worth) * 100

    if ratio_pct > 20:
        return FAIL(4, f"litigation & claims exposure {ratio_pct}% of net worth vs 20% "
                       "limit (routine guarantees/LCs/bills discounted excluded, §8.4-F)",
                    citation, confidence = HIGH)

    return PASS(4, f"litigation & claims exposure {ratio_pct}% of net worth (<= 20%); "
                   "routine business-linked exposure excluded from this ratio per §8.4-F",
                citation, confidence = HIGH)
7. Check 5 — Show Me the Cash (Section A Q5)

Rev 5 (Rules §2 Check 5 / §8.4-G): the flat 0.80 CFO/PAT threshold and flat
≥3-of-5-years-negative trigger are replaced by working-capital-cycle tiering (§2g),
a global 0.50 hard floor, and an explicit "not applicable" path for lending
institutions, whose CFO is dominated by loan-book/deposit movement rather than
P&L-linked working capital.

Rev 6 (Rules §2 Check 5 / §8.4-H): every disqualifying trigger below except
cumulative PAT ≤ 0 now routes through verify_use_of_funds() (§2h) before resolving
to FAIL. A verified-benign shortfall becomes a PASS carrying has_mandatory_warning
= true, never a silent PASS and never an automatic FAIL either.

PASS() below accepts an optional has_mandatory_warning argument (informal pseudocode
convention, same as every other named constructor in this spec) — omitted or false
everywhere except the one Rev 6 return path that sets it true.

function check5_cash_conversion(input: CompanyInput) -> CheckResult:

    if input.working_capital_cycle_tier is null:
        return INCONCLUSIVE("Check 5: missing working-capital-cycle classification (Rules §8.4-G)")

    if input.working_capital_cycle_tier == LENDING_INSTITUTION_NA:
        return INCONCLUSIVE("Check 5: not applicable — CFO/PAT is not a meaningful metric "
                             "for lending institutions (banks/NBFCs/insurers); their operating "
                             "cash flow is dominated by loan-book/deposit movement, not "
                             "P&L-linked working capital (Rules §8.4-G). Asset-quality trend "
                             "(GNPA/NNPA) is a domain-appropriate substitute, out of this "
                             "spec's scope.")

    if input.cfo_last_5y is null or input.pat_last_5y is null:
        return INCONCLUSIVE("Check 5: missing 5-year CFO and/or PAT series")

    n = length(input.cfo_last_5y)
    if n != length(input.pat_last_5y):
        return INCONCLUSIVE("Check 5: CFO and PAT series have mismatched year counts")

    mismatch = assert_comparable(input, ["cfo_last_5y", "pat_last_5y"])
    if mismatch is not null:
        return INCONCLUSIVE("Check 5: " + mismatch)

    thresholds = working_capital_cycle_thresholds(input.working_capital_cycle_tier)   // §2g

    negative_cfo_years = count(y in input.cfo_last_5y where y < 0)
    cumulative_cfo = sum(input.cfo_last_5y)
    cumulative_pat = sum(input.pat_last_5y)
    cfo_pat_ratio = (cumulative_pat > 0) ? (cumulative_cfo / cumulative_pat) : null

    // Rev 6: cumulative_pat <= 0 is the one trigger with no verification path — Rules
    // §2 Check 5's "never overridden" backstop.
    pat_negative_or_zero = (cumulative_pat <= 0)

    // The three triggers eligible for the §8.4-H override. Every tier's floor
    // (0.65/0.75/0.85) already sits above 0.50, so hard_floor_breach and
    // tier_floor_breach are not mutually exclusive — both are tracked separately so
    // the FAIL/warning message can correctly name whichever actually fired.
    negative_years_breach = (negative_cfo_years >= thresholds.negative_years_trigger)
    hard_floor_breach = (cfo_pat_ratio is not null and cfo_pat_ratio < 0.50)
    tier_floor_breach = (cfo_pat_ratio is not null and cfo_pat_ratio < thresholds.cfo_pat_floor)
    any_verifiable_trigger = negative_years_breach or hard_floor_breach or tier_floor_breach

    // Rev 6: attempt verification at most once (§8.4-H step 6), only if a verifiable
    // trigger fired and there is an actual shortfall to explain. A PAT<=0 company is
    // never routed here — that path is unconditional regardless of verification.
    verification = null
    if any_verifiable_trigger and not pat_negative_or_zero:
        verification = verify_use_of_funds(input, cumulative_pat, cumulative_cfo)   // §2h
    verified_ok = (verification is not null and verification.verified == true)

    // Post-verification disqualifying signal — what the track-record guard and the
    // normal-window branch both consume below. A verified-benign shortfall is not
    // disqualifying; an unverified or unverifiable one still is, exactly as pre-Rev-6.
    disqualifying_event = pat_negative_or_zero or (any_verifiable_trigger and not verified_ok)

    guard = apply_track_record_guard(
        years_required = 5,
        years_available = n,   // use actual series length, not the company-wide field, since this check's window is specifically 5 FYs of CFO/PAT data
        disqualifying_event_found = disqualifying_event
    )
    suffix = build_finding_suffix(5, n)   // Rev 3 — empty string if n >= 5

    // Rev 3: if the guard is about to fire on a short series, confirm the §8.4-C
    // completeness sub-step was actually attempted before accepting it silently.
    // This does not block or change the guard's outcome — it only enriches the
    // finding text so a reader can tell "we looked and 5 years genuinely aren't
    // available" from "no one tried to find the 5th year".
    if guard is not null and n < 5:
        gap_note = (input.years_5y_series_gap_checked == true)
            ? ""
            : " — 5-year completeness sub-step (Rules §8.4-C) not recorded as attempted"
        return build_result(5, guard, finding_suffix = suffix + gap_note)
    elif guard is not null:
        return build_result(5, guard, finding_suffix = suffix)

    (citation, missing_prov) = compose_citation(input,
        ["cfo_last_5y", "pat_last_5y", "working_capital_cycle_tier"])

    if pat_negative_or_zero:
        return FAIL(5, f"cumulative 5-yr PAT {cumulative_pat} <= 0" + suffix, citation, confidence = HIGH)

    if any_verifiable_trigger:
        trigger_desc = []
        if negative_years_breach:
            trigger_desc.append(f"{negative_cfo_years} of last 5 years had negative CFO "
                                 f"(>= {thresholds.negative_years_trigger} triggers this sector's tier)")
        if hard_floor_breach:
            trigger_desc.append(f"CFO/PAT ratio {cfo_pat_ratio} < 0.50 global hard floor")
        elif tier_floor_breach:
            trigger_desc.append(f"CFO/PAT ratio {cfo_pat_ratio} < {thresholds.cfo_pat_floor} "
                                 "sector tier threshold")
        trigger_text = join("; ", trigger_desc)

        if verified_ok:
            (uof_citation, _) = compose_citation(input,
                ["cfo_last_5y", "pat_last_5y", "working_capital_cycle_tier",
                 "revenue_last_5y", "cumulative_working_capital_change_5y",
                 "liquid_cushion_first_year", "liquid_cushion_last_year"])
            return PASS(5, "WARNING — " + trigger_text + ", but verified as business-"
                           "expansion-linked per Rules §8.4-H: " + join("; ", verification.notes) + suffix,
                        uof_citation, confidence = HIGH, has_mandatory_warning = true)

        // Not verified — verification is either null (data missing) or ran and failed.
        if verification is null:
            return FAIL(5, trigger_text + " — use-of-funds verification (§8.4-H) could not be "
                           "attempted: revenue_last_5y / cumulative_working_capital_change_5y / "
                           "liquid_cushion figures not available" + suffix,
                        citation, confidence = HIGH)
        return FAIL(5, trigger_text + " — use-of-funds verification (§8.4-H) attempted and did "
                       "not clear: " + join("; ", verification.notes) + suffix,
                    citation, confidence = HIGH)

    return PASS(5, f"CFO/PAT ratio {cfo_pat_ratio} (>= {thresholds.cfo_pat_floor} tier threshold), "
                   f"{negative_cfo_years} negative-CFO years "
                   f"(< {thresholds.negative_years_trigger} trigger)" + suffix,
                citation, confidence = HIGH)

New in Revision 3. suffix is now attached to every return path exactly as in Check 1 — this is the specific fix for the v1 gap where a FAIL reached via the guard's "a short history can still fail" branch gave no indication in its own finding text that only 4 of 5 years were used. gap_note additionally distinguishes "5 years genuinely weren't obtainable after actually looking" from "the pipeline stopped at whatever the uploaded source documents happened to contain" — the latter is a process gap the renderer and the analyst should be able to see and close on a re-run, per Rules §8.4-C. confidence here stays HIGH throughout: Check 5's fields have no RetrievalTier (there is no fallback source for CFO/PAT the way there is for a pledge trend or a regulatory search — either the audited cash flow statement has the figure or it doesn't), so the years-available suffix is the correct and sufficient disclosure mechanism for this check, not a confidence downgrade.

New in Revision 6. The three verifiable triggers are now tracked as independent booleans rather than folded straight into disqualifying_event, specifically so the FAIL/warning finding text can name exactly which one(s) fired — this matters more now than pre-Rev-6 because a reader deciding whether an override "should" have applied needs to know what was actually being excused. verify_use_of_funds() runs at most once per call (Rules §8.4-H step 6): if multiple triggers fire together (e.g. both a ratio breach and the negative-years count, as in the GRSE case that prompted this revision), one verification result governs the finding for all of them, since they are different symptoms of the same underlying cash-timing question, not independent claims each requiring its own evidence. has_mandatory_warning is the only place in this entire spec where a check's own CheckResult carries a flag with no equivalent in Revisions 1-5 — Phase1Result.warning_checks (§0) surfaces it to the renderer exactly as low_confidence_checks already does for confidence, so a warning can never silently disappear between the engine and the investor-facing text.

New in Revision 5. The lending-institution short-circuit runs before the 5-year-series check — a bank's INCONCLUSIVE "not applicable" verdict does not depend on whether its CFO/PAT data happens to be available; the check is inapplicable either way. thresholds is looked up once per call from working_capital_cycle_tier (§2g) and threaded through every subsequent comparison, replacing the old hardcoded 3 / 0.80 literals. Both fee/ratio floors (global 0.50, tier-specific) are evaluated as part of the same disqualifying_event expression the track-record guard consumes, so a short-history FAIL still correctly fires on either floor exactly as it did pre-Rev-5 for the flat threshold.

8. Check 6 — Executive Stability (Section A Q6)
function check6_executive_stability(input: CompanyInput) -> CheckResult:

    required = [cfo_changes_last_3y, restatement_of_past_accounts]
    if any(required) is null:
        return INCONCLUSIVE("Check 6: missing CFO change count or restatement history")

    disqualifying_event = (input.cfo_changes_last_3y > 1) or (input.restatement_of_past_accounts == true)

    years_available = input.years_of_track_record_available
    guard = apply_track_record_guard(
        years_required = 3,
        years_available = years_available,
        disqualifying_event_found = disqualifying_event
    )
    suffix = build_finding_suffix(3, years_available)   // Rev 3
    if guard is not null:
        return build_result(6, guard, finding_suffix = suffix)

    (citation, missing_prov) = compose_citation(input,
        ["cfo_changes_last_3y", "restatement_of_past_accounts"])

    // Rev 3: confidence keyed on how the restatement finding was sourced per Rules §8.4-D.
    confidence = roll_up_confidence(input,
        fields_used = ["cfo_changes_last_3y", "restatement_of_past_accounts"],
        retrieval_tier_fields = {"restatement_of_past_accounts": input.restatement_search_retrieval_tier})

    // Rev 3: if a restatement-shaped mention was found and excluded as ESG/BRSR-only
    // (Rules §8.4-D disambiguation), say so in the finding even on a PASS, so the
    // distinction is visibly a checked fact, not an assumed one.
    esg_note = ""
    if input.restatement_esg_only_excluded == true:
        esg_note = (" (an ESG/BRSR data restatement was found and confirmed unrelated to "
                    "the financial statements — does not count toward this check)")

    if input.cfo_changes_last_3y > 1:
        return FAIL(6, f"{input.cfo_changes_last_3y} CFO changes in last 3 years (> 1 triggers fail)" + suffix,
                    citation, confidence)

    if input.restatement_of_past_accounts == true:
        return FAIL(6, "retroactive restatement of past accounts" + suffix, citation, confidence)

    return PASS(6, f"{input.cfo_changes_last_3y} CFO change(s) (<= 1), no restatement" + suffix + esg_note,
                citation, confidence)

New in Revision 3. suffix, confidence, and esg_note are additive only — the > 1 and restatement thresholds are untouched. confidence reflects whether "no restatement found" came from the targeted search + Emphasis-of-Matter review (Rules §8.4-D, PRIMARY → HIGH) or a general keyword scan alone (FALLBACK → MEDIUM).

9. Master orchestrator — the gate
function run_phase1(input: CompanyInput, prior: Phase1Result | null) -> Phase1Result:

    input.company_type = classify_company_type(
        input.govt_shareholding_pct, input.promoter_holding_pct_of_company)

    // Evaluate ALL six checks — never short-circuit the evaluation itself.
    // Short-circuiting only applies to how much further analysis happens AFTER
    // the verdict (i.e. stop before Phase 2), not to which Phase 1 checks run.
    results = [
        check1_auditor_regulator(input),
        check2_promoter_pledge(input),
        check3_related_party(input),
        check4_contingent_liabilities(input),
        check5_cash_conversion(input),
        check6_executive_stability(input),
    ]

    failing = [r.check_id for r in results if r.status == FAIL]
    inconclusive = [r.check_id for r in results if r.status == INCONCLUSIVE]
    low_confidence = [r.check_id for r in results if r.confidence != HIGH]   // Rev 3
    warning = [r.check_id for r in results if r.has_mandatory_warning == true]   // Rev 6

    if failing is non-empty:
        verdict = REJECT
    elif inconclusive is non-empty:
        verdict = HOLD_INCONCLUSIVE
    else:
        verdict = CLEARED_TO_PHASE_2

    // Any field that a PASS or FAIL actually leaned on, but for which we have no
    // provenance, is a sourcing gap. Rules §7 requires every number to be cited.
    citation_gaps = distinct(flatten(
        [f for f in r.fields_used if input.provenance has no key f]
        for r in results if r.status != INCONCLUSIVE))

    return Phase1Result {
        result_id: new_uuid(),
        ticker: input.ticker,
        as_of_date: input.as_of_date,
        company_type: input.company_type,
        data_basis: input.data_basis,
        checks: results,
        verdict: verdict,
        failing_checks: failing,
        inconclusive_checks: inconclusive,
        low_confidence_checks: low_confidence,   // Rev 3
        warning_checks: warning,   // Rev 6
        revision: (prior is null) ? 1 : prior.revision + 1,
        supersedes: (prior is null) ? null : prior.result_id,
        input_digest: hash(input),
        generated_at: now(),
        citation_gaps: citation_gaps,
    }

Decision table (must match Phase1-Rules.md §3 exactly — unchanged in Revision 3):

Any FAIL?	Any INCONCLUSIVE (given no FAIL)?	Verdict
Yes	—	REJECT
No	Yes	HOLD_INCONCLUSIVE
No	No	CLEARED_TO_PHASE_2

FAIL always dominates INCONCLUSIVE — a stock is never "held" when it has already failed something; it is rejected outright. low_confidence_checks never participates in this table — a low-confidence finding is still a finding, and does not on its own turn a PASS into a HOLD or a FAIL. Its only job is to force the renderer (§10) to disclose it. Rev 6: warning_checks behaves the same way — a check only lands in warning_checks after already resolving to PASS via the §8.4-H override, so it cannot turn a CLEARED_TO_PHASE_2 into anything else; its only job, like low_confidence_checks, is to force the renderer to disclose it (§10).

Re-evaluation and supersession. Unchanged from Revision 2: a HOLD_INCONCLUSIVE is a temporary state by design; run_phase1() is re-run when a missing field is supplied, with revision = prior + 1 and supersedes = prior.result_id. Rev 3 addition: the same applies when a FALLBACK-tier field is later upgraded to PRIMARY (e.g. the 4-quarter pledge series becomes available after initially only a single figure could be sourced) — this is not a null-to-non-null resolution, so it would not have triggered re-evaluation under Revision 2's rule alone; confidence upgrades are now an explicit re-run trigger too.

10. Rendering layer (kept separate from the decision engine)

The functions above produce Phase1Result, a purely internal/analyst-facing object (maps to Phase1-Rules.md §4's table). Do not let the decision engine format investor-facing prose. A separate rendering function must:

Take Phase1Result as input (never re-derive numbers — display exactly what the engine computed).
Apply user.md's wrapping rules (§5 of Phase1-Rules.md): plain-English lead, term explanations on first use, numbers translated to relatable facts, the Pass/Fail translation table, a "so what does this mean for you" line per section, and the verbatim SEBI disclaimer from user.md §9. Verbatim means byte-for-byte from a locked template constant — the disclaimer text is never regenerated, paraphrased, shortened, or made editable in the UI.
Never fabricate a number, source, or explanation not present in the underlying CheckResult objects — if citation is null, the renderer must surface that as missing sourcing rather than inventing one.
Render citation_gaps explicitly. If a verdict-bearing check has no citation, the report must say so ("figure used but source not recorded") in both the analyst and investor views. An uncited number presented as sourced is the single worst failure mode this system can have.
Stamp revision, generated_at, as_of_date and data_basis on every rendered artefact, web and PDF alike, so a printed report can always be matched back to the evaluation that produced it.
State the reporting basis in plain language on the investor view ("figures are on a consolidated basis") — rules §8.1 prefers consolidated, and a reader comparing this report to a standalone filing needs to know which they are holding.
(New in Revision 3.) For every check_id in low_confidence_checks, render the plain-language confidence disclosure required by Rules §5 — not the word "confidence" or a raw MEDIUM/LOW tag, but a sentence naming what wasn't directly confirmed (see Rules §5c for the exact worked pattern). This is mandatory, not optional: a Phase1Result with a non-empty low_confidence_checks list and no corresponding disclosure in the rendered output is an incomplete render, on the same footing as a missing citation under point 4 above.
(New in Revision 3.) Any finding string containing the "(based on N of M years)" suffix from build_finding_suffix() must have that suffix carried into the investor-facing text in plain language (Rules §1a) — e.g. "over the four years we had reports for" — not dropped during the plain-English rewrite.
(New in Revision 6.) For every check_id in warning_checks, render the dedicated warning paragraph required by Rules §5d — its own clearly-labelled section, not a footnote or a clause folded into the "all six passed" summary. Must state the ratio/trigger that was breached, in plain language what that would normally mean, and the specific verified explanation (real revenue growth, the shortfall traced to working capital, no sign of hoarding) — see Rules §5d for the exact worked pattern. This is mandatory on the same footing as the low_confidence_checks disclosure above: a Phase1Result with a non-empty warning_checks list and no corresponding dedicated paragraph in the rendered output is an incomplete render.

Keeping this as two layers (engine → renderer) means the engine can be unit-tested against numeric fixtures independent of prose, and the prose layer can change without touching pass/fail logic.

11. Test fixtures to validate an implementation

Before wiring this into an app, run these fixtures through run_phase1() and confirm the verdicts match, since they exercise every branch. Fixtures 1–11 validate the check logic (Revision 1); 12–18 validate the data-integrity guards added in Revision 2; 19–23 (new) validate the confidence and years-available disclosure added in Revision 3.

#	Fixture	Expected verdict	Exercises
1	All 6 fields fully populated, all within safe thresholds	CLEARED_TO_PHASE_2	happy path
2	Audit opinion = QUALIFIED, everything else clean	REJECT (Check 1)	single-fail short-circuit reporting
3	Pledge 34%, rising trend	REJECT (Check 2)	§5a worked example
4	Govt shareholding 55%, promoter pledge fields all null	CLEARED_TO_PHASE_2 if others pass	Check 2 auto-pass bypasses its own null-check
5	Promoter holding 1% of company, pledge 30% of promoter holding, 0.3% of total shares	PASS on Check 2 w/ low-base note	low-base guard
6	Company listed 2 years, no disqualifying events, Check 1/6	INCONCLUSIVE on 1 & 6, others normal	insufficient track record → HOLD
7	Company listed 1 year but had a qualified audit opinion that year	REJECT (Check 1)	short history still fails on a real event
8	SHORT_CYCLE_ASSET_LIGHT company, CFO/PAT ratio 0.79 cumulative (< 0.85 tier floor), 2 negative-CFO years (< 3 trigger), no use-of-funds fields populated	REJECT (Check 5, ratio trigger only) — finding notes verification could not be attempted	independent OR triggers; Rev 5 — tier-qualified from the original v1 fixture so the 0.79 figure still fails under the new tiering (it would now PASS for a Moderate- or Long-cycle company — see fixture 32); Rev 6 — confirms a trigger with no use-of-funds data stays FAIL via verify_use_of_funds() returning null, not a free pass
9	Missing net_worth entirely	HOLD_INCONCLUSIVE overall (assuming no other fails)	missing-data guard, never estimate
10	Net worth = -500 (negative)	REJECT (Check 4)	broken balance sheet
11	Tier1 (Financial Services) company, legal fees 1.6% of revenue (> 1.35% flag threshold), opinion clean, no other issues	REJECT (Check 1, fee-anomaly sub-trigger)	Check 1's 4th sub-condition in isolation, Rev 4 revenue-normalized version
12	years_of_track_record_available = null, everything else clean and populated	HOLD_INCONCLUSIVE (Checks 1 & 6)	unknown history must not read as 0 years, nor as a sufficient window
13	audit_fees = 0, revenue/industry_sector/legal_fees all populated and within sector band, opinion clean, no other issues	CLEARED_TO_PHASE_2 (assuming others pass) — Rev 4: audit_fees is no longer required, so a zero/missing audit_fees alone no longer forces INCONCLUSIVE	regression guard, updated for Rev 4 — an uncomputable *secondary* observation must never block a PASS reached on the primary revenue-normalized test
14	RPT note tagged CONSOLIDATED, revenue tagged STANDALONE	HOLD_INCONCLUSIVE (Check 3)	basis-mismatch guard
15	contingent_liabilities period FY24, net_worth period FY23	HOLD_INCONCLUSIVE (Check 4)	period-mismatch guard
16	Promoter holding 3%, pledge 40%, pledged_pct_of_total_shares not reported	REJECT (Check 2) — derived 1.2% of total shares > 0.5%	§2c derivation + low-base FAIL path
17	Pledge 34% with no provenance entry for pledged_pct_of_promoter_holding	REJECT (Check 2), citation null, citation_gaps non-empty	citation plumbing — verdict stands, sourcing gap is visible
18	Fixture 9 re-run after net_worth is supplied by manual review	revision = 2, supersedes = fixture 9's result_id, verdict recomputed	result versioning after review resolution
19	Check 5 with only 4 years of CFO/PAT, cumulative ratio −0.12	REJECT (Check 5), finding text contains "(based on 4 of the required 5 years)"	§2d build_finding_suffix() on a FAIL reached via the guard's short-history branch
20	Check 2 pledge 0%, pledged_pct_history_retrieval_tier = FALLBACK	PASS (Check 2), confidence = MEDIUM, finding contains the trend-inferred note	§8.4-B fallback disclosure, PASS case
21	Check 1 regulatory_action.nature = NONE, retrieval_tier = FALLBACK (SEBI portal unreachable)	PASS (Check 1) if other sub-checks clear, confidence = MEDIUM	§8.4-A fallback disclosure on a PASS-contributing negative finding
22	Check 6 restatement search finds an ESG/BRSR water-withdrawal restatement only, restatement_esg_only_excluded = true, restatement_of_past_accounts = false	PASS (Check 6), finding contains the ESG-exclusion note	§8.4-D disambiguation is visible, not just assumed
23	Check 5 with only 3 years of CFO/PAT, no disqualifying event in those 3, years_5y_series_gap_checked = false	HOLD_INCONCLUSIVE (Check 5), finding/missing_data notes the §8.4-C completeness sub-step was not recorded as attempted	distinguishes "genuinely unavailable" from "no one looked further"
24	Tier4 (Manufacturing) company, legal fees 0.35% of revenue (within 0.2%–0.3% sourced band, below the 0.45% flag threshold), legal/audit ratio 7x, opinion clean, no other issues	CLEARED_TO_PHASE_2 (Check 1 PASS), finding contains the secondary-ratio pass_note ("legal/audit fee ratio 7x is elevated but... not treated as a fail trigger")	Rev 4 — a high legal/audit ratio alone, with revenue-intensity inside the sector band, must PASS, not FAIL; validates the old v3 fixture 11 scenario now resolves the opposite way once revenue-normalized
25	Tier4 company, legal fees jump 2.4x YoY, a disclosed litigation settlement is found in the Contingent Liabilities note, legal_fee_surge_explained = true	CLEARED_TO_PHASE_2 (Check 1 PASS), assuming legal_pct_revenue itself is within band	Rev 4 surge-gate — a >2x YoY increase with a disclosed, checked-for explanation must not fail on that basis alone
26	Tier4 company, legal fees jump 2.4x YoY, no disclosed cause found, legal_fee_surge_explained = false	REJECT (Check 1, LEGAL_FEES_UNEXPLAINED_SURGE_OVER_2X_YOY)	Rev 4 surge-gate — an unexplained surge still fails exactly as it did pre-Rev 4
27	Bank, litigation_claims_exposure = 2% of net worth, routine_guarantee_exposure = 850% of net worth (ordinary LC/guarantee/forex business), breakdown_available = true	CLEARED_TO_PHASE_2 (Check 4 PASS)	Rev 5 — the primary motivating case: under the pre-Rev-5 flat 15%-of-total rule this bank would have been an automatic REJECT purely from routine business; the split correctly excludes it
28	EPC contractor, litigation_claims_exposure = 25% of net worth (disputed tax demand + contested claim), routine_guarantee_exposure = 300% of net worth (performance/bid bonds), breakdown_available = true	REJECT (Check 4, "litigation & claims exposure 25% of net worth vs 20% limit")	Rev 5 — a genuine litigation exposure still fails even for a sector with high routine guarantee volume; the split doesn't make Check 4 toothless, it makes it accurate
29	contingent_liabilities (lump total) = 3% of net worth, breakdown_available = false	CLEARED_TO_PHASE_2 (Check 4 PASS, confidence MEDIUM)	Rev 5 — §8.4-F immateriality fast-path; a small undisclosed-breakdown total should not block a verdict
30	contingent_liabilities (lump total) = 40% of net worth, breakdown_available = false	HOLD_INCONCLUSIVE (Check 4)	Rev 5 — same fast-path, opposite outcome; a large undisclosed-breakdown total is genuinely unresolved, not assumed either way
31	Missing net_worth entirely (Rev 5 re-check of fixture 9's scenario)	HOLD_INCONCLUSIVE overall (assuming no other fails)	confirms fixture 9's missing-data guard still holds after the Rev 5 rewrite
32	MODERATE_CYCLE company, CFO/PAT ratio 0.79 cumulative (>= 0.75 tier floor), 1 negative-CFO year (< 3 trigger)	CLEARED_TO_PHASE_2 (Check 5 PASS)	Rev 5 — the same 0.79 ratio that fails fixture 8's Short-cycle company correctly passes here; proves the tiering, not just a global loosening
33	LONG_CYCLE_PROJECT_ACCOUNTING (EPC) company, CFO/PAT ratio 0.68 cumulative (>= 0.65 tier floor), 3 negative-CFO years (< 4 trigger)	CLEARED_TO_PHASE_2 (Check 5 PASS)	Rev 5 — a ratio and negative-year count that would fail every other tier is legitimate for this tier, per the sourced ~0.7x EPC benchmark
34	Any working_capital_cycle_tier, CFO/PAT ratio 0.45 cumulative	REJECT (Check 5), finding text cites the global 0.50 hard floor, not the tier threshold	Rev 5 — confirms the hard-floor message routing fires ahead of the tier-specific message even though both would fail here
35	Bank (LENDING_INSTITUTION_NA), full clean 5-year CFO/PAT series available	HOLD_INCONCLUSIVE (Check 5), finding states "not applicable... lending institutions"	Rev 5 — the not-applicable path fires regardless of data availability; a bank is never routed through the ratio logic
36	working_capital_cycle_tier = null, cfo_last_5y/pat_last_5y otherwise clean and populated	HOLD_INCONCLUSIVE (Check 5)	Rev 5 — missing classification guard; null tier is never silently treated as any specific tier
37	LONG_CYCLE company, CFO/PAT 0.055 (breaches both the 0.50 hard floor and the 0.65 tier floor), 3 of 5 years negative CFO (below the tier's own 4-year trigger, so this alone would not fire), revenue_last_5y grows 4x over the window (>= 1.5x), cumulative_working_capital_change_5y covers 85% of the cumulative PAT-CFO gap (>= 60%), liquid cushion 22% of revenue in year 1 vs 19% in year 5 (flat-or-declining, passes the 10% tolerance)	CLEARED_TO_PHASE_2 (Check 5 PASS), has_mandatory_warning = true, warning_checks = [5], finding states both breached triggers and all three verified conditions	Rev 6 — the canonical case this revision was built for (the GRSE Sep-2026 live run); confirms one verify_use_of_funds() call correctly governs two simultaneously-fired triggers
38	Same trigger scenario as fixture 37, but liquid cushion is 18% of revenue in year 1 vs 31% in year 5 (rising well past the 10% tolerance)	REJECT (Check 5), finding states condition (c) NOT met	Rev 6 — growth and working-capital coverage alone are not enough; evidence of the cash actually piling up blocks the override even when (a) and (b) both hold
39	Same trigger scenario as fixture 37, but revenue_last_5y is flat across the window (growth ratio 1.05x, < 1.5x)	REJECT (Check 5), finding states condition (a) NOT met	Rev 6 — a working-capital-heavy shortfall without genuine revenue growth is not a credible "expansion" story; guards against dressing up receivable/inventory deterioration as growth
40	Same trigger scenario as fixture 37, but cumulative_working_capital_change_5y covers only 25% of the cumulative PAT-CFO gap (< 60%)	REJECT (Check 5), finding states condition (b) NOT met	Rev 6 — the shortfall isn't actually a working-capital story here (e.g. driven by unusual provisions or finance costs instead); the override requires the CFO Statement's own reconciling line to do most of the explaining, not just a plausible-sounding narrative
41	Same trigger scenario as fixture 37 (all three conditions verified), but only 4 of the required 5 years of CFO/PAT data are available	HOLD_INCONCLUSIVE (Check 5), finding contains "(based on 4 of the required 5 years)"	Rev 6 — proves the composition with the Rev 3 track-record guard: a verified-benign shortfall is "not disqualifying," so a short window correctly falls through to INCONCLUSIVE ("cannot pass prematurely") rather than either FAIL or a premature PASS-with-warning
12. What this spec deliberately does not decide

These are acquisition or product concerns, resolved in the implementation plan, and are listed here only so an implementer does not mistake their absence for an omission:

Where each field comes from. The engine is source-agnostic by design. The field-by-field source contract lives in the implementation plan §3.
What confidence level is good enough to populate a field. The engine trusts every non-null input it is given; the extraction layer is responsible for deciding what it is willing to assert (implementation plan §5.3). Revision 3 note: this still holds for whether to populate a field at all; RetrievalTier only governs how a populated field's confidence is disclosed downstream, which is a rendering concern, not an extraction-trust concern.
When to re-run. Staleness, review SLAs, and re-scrape cadence are product decisions (implementation plan §7.4, §12), now extended in Revision 3 to also cover fallback-to-primary confidence upgrades (see §9).
13. Change-control note

This file is derived entirely from Phase1-Rules.md. If a threshold, exception, or decision rule changes there, mirror the exact change here in the same edit — do not let the two drift. If an application is later generated from this spec, treat Phase1-Rules.md as the source of truth for policy and this file as the source of truth for implementation shape; neither should introduce a rule the other doesn't have.

Revision history

Revision 6 — a genuine, narrowly-scoped policy change to Check 5 only, adding an evidence-gated override rather than loosening any existing threshold. Prompted by a live Phase 1 run on GRSE (Sep 2026) that breached the Revision 5 hard floor (ratio 0.055 vs. a 0.50 floor) in a way a follow-up forensic trace of the Cash Flow Statement showed was overwhelmingly explained by working-capital absorption behind genuine revenue growth (revenue nearly quadrupled over the same window), not cash going missing — rejecting outright on the ratio alone, without ever asking where the shortfall went, was treating a symptom as the disease. Every item below traces to Phase1-Rules-v2.md §2 Check 5 and new §8.4-H:

Change	Traces to
CompanyInput: revenue_last_5y, cumulative_working_capital_change_5y, liquid_cushion_first_year, liquid_cushion_last_year added	Rules §8.4-H's three verification conditions — a direct AR/Screener extraction, not synthesized from other fields
CheckResult.has_mandatory_warning; Phase1Result.warning_checks	Rules §5's new use-of-funds warning disclosure requirement and §8.4-H's "disclosed PASS, never silent" rule — same architectural pattern as Revision 3's confidence/low_confidence_checks pair
verify_use_of_funds() (§2h)	Rules §8.4-H's three conditions (real growth, working-capital-covered shortfall, no hoarding), reproduced as a pure function returning null (not false) when it cannot be attempted, per the golden rule
Check 5 rewritten: cumulative_pat <= 0 remains the sole unconditional trigger; the other three triggers (tier floor, 0.50 hard floor, negative-years count) now route through verify_use_of_funds() before resolving to FAIL; a verified-benign shortfall returns PASS with has_mandatory_warning = true and a finding string naming both the breached trigger(s) and the verification notes	Rules §2 Check 5, §8.4-H steps 4-6
run_phase1() populates Phase1Result.warning_checks; decision table note extended to state warning_checks never affects verdict, same footing as low_confidence_checks	Rules §5's disclosure requirement; the check only ever reaches warning_checks after already resolving to PASS
New §10 renderer requirement: dedicated warning paragraph for every check_id in warning_checks, per Rules §5d's worked pattern	Rules §5, new §5d worked example
Fixture 8 annotated (confirms a trigger with no use-of-funds data stays FAIL, not a free pass); Fixtures 37-41 added (verified PASS-with-warning on the GRSE pattern; each of the three conditions failing individually; composition with the short-track-record guard)	Coverage for each item above

Revision 5 — a genuine threshold/metric change to Check 4 and Check 5 only. Both replaced a single flat, industry-agnostic threshold with an industry/business-model-aware test, for the same underlying reason as Revision 4: a flat number applied identically to every sector breaks badly for the sectors whose business model differs most from the "typical" company the flat number was implicitly calibrated against (banks/NBFCs/EPC contractors for Check 4's routine guarantee volume; long-project-cycle and lending sectors for Check 5's cash-conversion timing). Every item below traces to Phase1-Rules-v2.md §2 Checks 4/5 and new §8.4-F / §8.4-G:

Change	Traces to
CompanyInput: litigation_claims_exposure, routine_guarantee_exposure, contingent_liabilities_breakdown_available added; contingent_liabilities retained as lump-total fallback only	Rules §2 Check 4 / §8.4-F — Schedule III already requires the sub-category breakdown; a blended total is not comparable across sectors
CompanyInput: WorkingCapitalCycleTier enum, working_capital_cycle_tier added	Rules §2 Check 5 / §8.4-G — a separate classification axis from IndustrySector (§2f), since legal intensity and working-capital-cycle length classify the same company differently (e.g. IT is elevated-legal but short-cycle/asset-light)
working_capital_cycle_thresholds() (§2g)	Rules §8.4-G's tier table, reproduced as data
Check 4 rewritten: net_worth <= 0 unchanged; primary test now litigation_claims_exposure vs. a single 20%-of-net-worth threshold; routine_guarantee_exposure excluded from the ratio entirely; lump-total immateriality fast-path (<=5% of net worth) and INCONCLUSIVE fallback for undisclosed breakdowns above that	Rules §2 Check 4, §8.4-F steps 1-4
Check 5 rewritten: lending-institution short-circuit to INCONCLUSIVE before the data-availability check; tier-specific cfo_pat_floor and negative_years_trigger replace the flat 0.80 / 3-of-5 literals; explicit global 0.50 hard-floor check retained as a distinctly-labelled backstop alongside the tier floor	Rules §2 Check 5, §8.4-G
Fixture 8 tier-qualified (SHORT_CYCLE_ASSET_LIGHT); Fixtures 27-36 added (BFSI routine-exclusion PASS, genuine-litigation FAIL, lump-total fast-path PASS/INCONCLUSIVE, moderate-cycle PASS proving the same ratio that fails fixture 8 passes here, long-cycle EPC tolerance, hard-floor message routing, lending not-applicable, missing-tier guard)	Coverage for each item above

Revision 4 — a genuine threshold/metric change to Check 1.4 only. The prior "legal fees > 5x audit fees, or > 2x YoY surge" rule was a flat, industry-agnostic multiple with no published benchmark behind the specific ratio, and audit fees are a poor denominator on their own (fixed-cost floor, so the ratio is size-confounded — see Phase1-Rules-v2.md §8.4-E for full sourcing and rationale, including the caveat that the industry bands are global/directional, not India-calibrated). Every item below traces to Phase1-Rules-v2.md §2 Check 1.4 and new §8.4-E:

Change	Traces to
IndustrySector enum; industry_sector and legal_fee_surge_explained added to CompanyInput	Rules §8.4-E — the primary test needs a sector classification; the surge test needs a place to record whether a disclosed cause was found
sector_flag_threshold() (§2f)	Rules §8.4-E's industry-tiered band table, reproduced as data
Check 1's required-fields list: audit_fees removed, revenue and industry_sector added	Rules §2 Check 1.4 — audit_fees is now secondary/non-binding; the primary test runs on legal_pct_revenue
Check 1's fee-anomaly sub-check rewritten: primary test is legal_pct_revenue vs. sector_flag_threshold(); surge test gated on legal_fee_surge_explained; legal/audit ratio demoted to a pass_notes observation	Rules §2 Check 1.4(a)(b)(c)
Fixture 11 rewritten (sector-band trigger, not a flat ratio); Fixture 13 updated (audit_fees=0 no longer forces INCONCLUSIVE); Fixtures 24–26 added (ratio-inside-band PASS, explained-surge PASS, unexplained-surge FAIL)	Coverage for each item above

Revision 3 — sourcing-transparency changes only; no policy threshold, exception, or decision rule was altered, and each item below traces to a gap identified during the Cyient DLM live run (Sep 2026) and the corresponding Phase1-Rules.md v2 requirement:

Change	Traces to
RetrievalTier enum; regulatory_action.retrieval_tier, pledged_pct_history_retrieval_tier, restatement_search_retrieval_tier, restatement_esg_only_excluded, years_5y_series_gap_checked on CompanyInput	Rules §8.4-A/B/C/D — each sub-check now names its primary source and its fallback explicitly
CheckResult.confidence; Phase1Result.low_confidence_checks	Rules §4's new Confidence column and §9's Guardrail 9 ("confidence is not optional")
build_finding_suffix() (§2d), applied to Checks 1, 5, 6	Rules §1a — a short-window FAIL/INCONCLUSIVE must say so in its own finding text, not only in analyst notes
roll_up_confidence() (§2d), applied to Checks 1, 2, 6	Rules §4's Confidence column + §5's confidence-labelling requirement
Check 2's trend_finding_note	Rules §8.4-B — a fallback-sourced pledge trend must be visibly distinguished from an actual quarterly series
Check 5's gap_note referencing years_5y_series_gap_checked	Rules §8.4-C — distinguishes "5 years genuinely unavailable after looking" from "pipeline didn't try"
Check 6's esg_note referencing restatement_esg_only_excluded	Rules §8.4-D disambiguation — an ESG/BRSR restatement must be shown as checked-and-excluded, not silently absent
Renderer requirements 7–8 in §10	Rules §5's confidence-labelling and §1a's years-available disclosure, made mandatory for the render step, mirroring how Revision 2 made citation_gaps mandatory
Phase1Result re-run trigger extended to confidence upgrades (§9)	Rules v2 intent — a fallback-sourced finding that later gets a primary source should refresh the report, not just a null-to-non-null resolution
Fixtures 19–23 added	Coverage for each item above

Revision 2 (retained for history) — implementation-shape changes only; no policy threshold, exception, or decision rule was altered:

Change	Traces to
FieldProvenance on CompanyInput, compose_citation() (§2a), citation_gaps	Rules §1 "cite the source and period for each"; §7 definition of done; this file's own CheckResult.citation requirement, which previously had no way of being satisfied
Comparability guard on basis and period (§2b), applied to Checks 1, 3, 4, 5	Rules §8.1 (consolidated preferred) + §0 golden rule — an incomparable ratio is not data
data_basis on CompanyInput and Phase1Result	Rules §8.1
years_of_track_record_available made nullable, with null handled in §2	Rules §1 track-record paragraph + golden rule; previously an unset value silently read as 0 years
Check 1: zero/uncomputable audit fee moved out of fail_reasons into an INCONCLUSIVE path	Rules §1 "do not guess... mark that check INCONCLUSIVE"; the prior code returned FAIL on missing data, which contradicted policy
derive_pledged_pct_of_total_shares() (§2c)	Rules §2 Check 2 low-base exception; exact arithmetic, flagged DERIVED
revision / supersedes / input_digest / generated_at on Phase1Result	Rules §3 (a HOLD is temporary) + §6 guardrails — a superseded verdict must not circulate as current
Renderer requirements 4–6 in §10	Rules §5 and user.md §9 (verbatim disclaimer)
Fixture 5 corrected: promoter 1% / pledge 30% / 0.3% of total	The original values (3% × 40%) are arithmetically 1.2% of total shares, not 0.3%, and would have failed rather than passed once §2c derivation exists. The corrected numbers preserve the fixture's original intent — a low-base PASS
Fixtures 12–18 added	Coverage for each guard above