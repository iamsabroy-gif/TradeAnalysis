# Phase 1 Gatekeeper — Algorithm Specification

*Implementation-ready pseudocode for every check in `Phase1-Rules.md`. This file is the
bridge between the rules doc (human-readable policy) and an application (deterministic
code). Every function below maps 1:1 to a section of `Phase1-Rules.md` — thresholds,
exceptions, and edge cases are copied verbatim, not reinterpreted. If the rules file is
ever updated, update this file in the same commit.*

Status values used throughout: `PASS`, `FAIL`, `INCONCLUSIVE`. Never a numeric score.

**Revision 2 (see §13)** adds provenance/citation plumbing, reporting-basis and period
consistency guards, result versioning, and two bug fixes. **No threshold, exception, or
decision rule changed** — every number here is still exactly what `Phase1-Rules.md` §2
and §3 say.

---

## 0. Data model (inputs)

```
enum CompanyType { PRIVATE_PROMOTER, GOVT_PSU, PROFESSIONALLY_MANAGED }
enum ReportingBasis { CONSOLIDATED, STANDALONE, NOT_APPLICABLE }
enum Confidence { HIGH, MEDIUM, LOW, MANUAL, DERIVED }

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
  }
  legal_fees: number | null            // latest FY, currency units
  audit_fees: number | null            // latest FY, currency units
  legal_fees_prior_year: number | null // for surge check

  // Check 2 — Promoter Pledge
  govt_shareholding_pct: number | null       // central+state, direct+indirect
  promoter_holding_pct_of_company: number | null   // promoter shares / total shares outstanding
  pledged_pct_of_promoter_holding: number | null   // latest quarter
  pledged_pct_history_last_4q: number[] | null     // oldest -> newest, same metric
  pledged_pct_of_total_shares: number | null       // for low-base guard; may be derived, see §2c

  // Check 3 — Related Party Transactions
  rpt_sales_plus_purchases: number | null
  revenue: number | null                    // same statement, same FY, same basis as the RPT note
  unusual_affiliate_dealings: bool | null   // large/unexplained loans/deals w/ unlisted affiliates

  // Check 4 — Contingent Liabilities
  contingent_liabilities: number | null
  net_worth: number | null                  // total equity / shareholders' funds, same FY & basis

  // Check 5 — Cash Conversion (5 fiscal years, oldest -> newest)
  cfo_last_5y: number[] | null   // cash from operations, len <= 5
  pat_last_5y: number[] | null   // profit after tax, len <= 5

  // Check 6 — Executive Stability
  cfo_changes_last_3y: int | null
  restatement_of_past_accounts: bool | null

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
  reason_code: string            // machine-readable, e.g. "PLEDGE_ABOVE_10PCT"
  missing_data: string | null    // populated only when INCONCLUSIVE
  fields_used: string[]          // CompanyInput field names this result actually depended on
  citation: string | null        // source + period, required whenever a number is used
  basis: ReportingBasis          // basis the numbers in this result were computed on
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
```

**Golden rule for every function below:** if a required input field is `null` (not
merely zero/false — a real "we could not find this"), the check returns `INCONCLUSIVE`,
never a guessed `PASS` or `FAIL`. Zero and false are valid data points, not missing data;
do not conflate "0%" with "unknown."

**Two corollaries added in revision 2, both derived from that same rule plus rules §1's
"cite the source and period for each" — neither is a new policy threshold:**

- **Never compute a ratio across mismatched basis or period.** A consolidated RPT figure
  over a standalone revenue, or an FY24 contingent liability over an FY23 net worth,
  produces a number that looks confident and is wrong. Mismatch is missing data, so it
  returns `INCONCLUSIVE` (§2b).
- **Never manufacture a FAIL out of an unusable input.** If a denominator is zero or a
  sub-check cannot be computed, that sub-check is `INCONCLUSIVE`; it does not join the
  fail list (see the Check 1 fix in §3).

---

## 1. Helper: company type classification

Feeds Check 2's auto-pass exceptions. Run this once per company before the checks.

```
function classify_company_type(govt_shareholding_pct, promoter_holding_pct_of_company) -> CompanyType:
    if govt_shareholding_pct is not null and govt_shareholding_pct >= 51:
        return GOVT_PSU
    if promoter_holding_pct_of_company is not null and promoter_holding_pct_of_company == 0:
        return PROFESSIONALLY_MANAGED
    return PRIVATE_PROMOTER
```

Note: a partially-disinvested former PSU with govt stake < 51% is `PRIVATE_PROMOTER` for
this classifier and gets no auto-pass — per rules §2, Check 2.

Note on acquisition: `govt_shareholding_pct` being null does not make a company
`PRIVATE_PROMOTER` *by evidence* — it makes it `PRIVATE_PROMOTER` *by default*, which
then routes into Check 2's normal path and its own null-checks. That is the correct
conservative behaviour (a company is not granted a PSU auto-pass on missing data), but
it means the acquisition layer must actually retrieve government shareholding rather
than leaving it null. See the field-coverage matrix in the implementation plan §3.

---

## 2. Helper: track-record sufficiency guard

Applies to Checks 1, 5, 6 (lookback windows of 3, 5, 3 years respectively). Wrap the
core FAIL logic of those checks with this guard.

```
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
```

Each check function calls this first and short-circuits if it returns non-null.

---

## 2a. Helper: citation composition

`CheckResult.citation` is required whenever a number is used. It is built from the
provenance of exactly the fields the check consumed — never hand-written, never inferred.

```
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
```

A null or partial citation never blocks a verdict — the numbers are still the numbers —
but every gap propagates to `Phase1Result.citation_gaps`, and §10 requires the renderer
to surface it as missing sourcing rather than presenting an uncited figure as sourced.

---

## 2b. Helper: comparability guard (basis + period)

Applies to every check that divides one reported figure by another: Check 1's
legal/audit fee ratio, Check 3, Check 4, Check 5.

```
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
```

Callers treat a non-null return as missing data: `INCONCLUSIVE`, with the returned string
as `missing_data`. Multi-year series (`cfo_last_5y`, `pat_last_5y`,
`pledged_pct_history_last_4q`) carry one provenance entry describing the whole span
(e.g. `period: "FY20-FY24"`), so the period check compares spans, not individual years.

---

## 2c. Helper: derived pledge base

`pledged_pct_of_total_shares` is an exact arithmetic identity, not an estimate, so
deriving it is not a violation of the golden rule. A directly reported value always wins
over a derived one.

```
function derive_pledged_pct_of_total_shares(input: CompanyInput) -> number | null:
    if input.pledged_pct_of_total_shares is not null:
        return input.pledged_pct_of_total_shares          // reported value wins

    if input.promoter_holding_pct_of_company is null
       or input.pledged_pct_of_promoter_holding is null:
        return null

    // (promoter's % of company) x (pledged % of that holding)
    return input.promoter_holding_pct_of_company
           * input.pledged_pct_of_promoter_holding / 100
```

When this derives a value, the application must record provenance for it with
`confidence: DERIVED` and a source naming both inputs, so the citation shows the
derivation rather than implying a filed figure.

---

## 3. Check 1 — Auditor & Regulator Integrity (Section A Q1)

```
function check1_auditor_regulator(input: CompanyInput) -> CheckResult:

    // Required fields
    required = [auditor_resigned_mid_tenure_last_3y, audit_opinion,
                regulatory_action.active_or_past_5y, legal_fees, audit_fees]
    if any(required) is null:
        return INCONCLUSIVE("Check 1: missing one or more of "
                             "[auditor resignation history, audit opinion, "
                             "regulatory action status, legal/audit fee figures]")

    guard = apply_track_record_guard(
        years_required = 3,
        years_available = input.years_of_track_record_available,
        disqualifying_event_found = (
            input.auditor_resigned_mid_tenure_last_3y == true
            or input.audit_opinion != CLEAN
            or input.regulatory_action.nature in {FRAUD, SIPHONING, MANIPULATION, ACCOUNTING_IRREGULARITY}
        )
    )
    if guard is not null:
        return build_result(1, guard)

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

    // Fee-ratio sub-check. Guarded for comparability first: a legal fee from the
    // consolidated statements over an audit fee from the standalone ones is meaningless.
    fee_mismatch = assert_comparable(input, ["legal_fees", "audit_fees"])
    if fee_mismatch is not null:
        inconclusive_notes.append("legal/audit fee ratio not computable: " + fee_mismatch)
    else if input.audit_fees > 0:
        ratio = input.legal_fees / input.audit_fees
        surge = (input.legal_fees_prior_year is not null and input.legal_fees_prior_year > 0
                 and input.legal_fees / input.legal_fees_prior_year > 2)
        if ratio > 5:
            fail_reasons.append("LEGAL_FEES_EXCEED_5X_AUDIT_FEES:" + ratio)
        elif surge:
            fail_reasons.append("LEGAL_FEES_SURGE_OVER_2X_YOY")
    else:
        // audit_fees is present but zero — the ratio is undefined, not a red flag.
        inconclusive_notes.append("audit_fees is zero; legal/audit ratio undefined")

    (citation, missing_prov) = compose_citation(input,
        ["audit_opinion", "auditor_resigned_mid_tenure_last_3y",
         "regulatory_action", "legal_fees", "audit_fees"])

    // FAIL dominates: a real disqualifying event still fails even if a sub-check
    // could not be computed. But an uncomputable sub-check on its own is INCONCLUSIVE
    // and must never be reported as a failure.
    if fail_reasons is non-empty:
        return FAIL(1, fail_reasons, finding = format_numbers(fail_reasons), citation)
    if inconclusive_notes is non-empty:
        return INCONCLUSIVE(1, missing_data = join("; ", inconclusive_notes), citation)
    return PASS(1, "clean opinion, no mid-tenure resignation, no disqualifying "
                   "regulatory action, legal/audit fee ratio normal", citation)
```

> **Fix in revision 2.** The previous version appended the zero-audit-fee note into
> `fail_reasons` and then returned `FAIL` whenever that list was non-empty — so a company
> with a clean opinion and a zero/unparsed audit fee was rejected outright. Zero audit
> fees is missing information, and rules §1 is explicit that missing information is a
> hold, not a fail.

---

## 4. Check 2 — Promoter Pledge & Encumbrance (Section A Q2)

```
function check2_promoter_pledge(input: CompanyInput) -> CheckResult:

    // Auto-pass exceptions first — no data-availability check needed for these paths
    if input.company_type == GOVT_PSU:
        return PASS(2, "Government PSU (govt shareholding >= 51%) — pledge check N/A")

    if input.company_type == PROFESSIONALLY_MANAGED:
        return PASS(2, "Zero promoter holding — no promoter shares exist to pledge")

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
                           f"{pledged_of_total}% of total shares", citation)
        else:
            return PASS(2, "pledge % elevated due to small promoter base, "
                           "not treated as a red flag", citation)

    // Standard thresholds
    if input.pledged_pct_of_promoter_holding > 10:
        return FAIL(2, f"pledge {input.pledged_pct_of_promoter_holding}% "
                       "vs 10% limit (absolute threshold)", citation)

    if trend_rising:
        return FAIL(2, "pledged % rising over last 2-4 quarters "
                       "(or unexplained single-quarter spike > 2pp)", citation)

    return PASS(2, f"pledge {input.pledged_pct_of_promoter_holding}% "
                   "(<= 10%), stable/declining over last 4 quarters", citation)
```

```
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
```

---

## 5. Check 3 — Related-Party "Leakage" (Section A Q3)

```
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
        return FAIL(3, f"RPT {rpt_pct}% of revenue vs 5% limit", citation)

    if input.unusual_affiliate_dealings == true:
        return FAIL(3, "large/unexplained loans or deals with promoter-owned unlisted affiliates", citation)

    return PASS(3, f"RPT {rpt_pct}% of revenue (<= 5%), no suspicious affiliate transactions", citation)
```

---

## 6. Check 4 — Contingent Liabilities (Section A Q4)

```
function check4_contingent_liabilities(input: CompanyInput) -> CheckResult:

    required = [contingent_liabilities, net_worth]
    if any(required) is null:
        return INCONCLUSIVE("Check 4: missing contingent liabilities or net worth figure")

    mismatch = assert_comparable(input, ["contingent_liabilities", "net_worth"])
    if mismatch is not null:
        return INCONCLUSIVE("Check 4: " + mismatch)

    (citation, missing_prov) = compose_citation(input,
        ["contingent_liabilities", "net_worth"])

    if input.net_worth <= 0:
        return FAIL(4, f"net worth {input.net_worth} <= 0 (broken balance sheet)", citation)

    ratio_pct = (input.contingent_liabilities / input.net_worth) * 100

    if ratio_pct > 15:
        return FAIL(4, f"contingent liabilities {ratio_pct}% of net worth vs 15% limit", citation)

    return PASS(4, f"contingent liabilities {ratio_pct}% of net worth (<= 15%)", citation)
```

---

## 7. Check 5 — Show Me the Cash (Section A Q5)

```
function check5_cash_conversion(input: CompanyInput) -> CheckResult:

    if input.cfo_last_5y is null or input.pat_last_5y is null:
        return INCONCLUSIVE("Check 5: missing 5-year CFO and/or PAT series")

    n = length(input.cfo_last_5y)
    if n != length(input.pat_last_5y):
        return INCONCLUSIVE("Check 5: CFO and PAT series have mismatched year counts")

    mismatch = assert_comparable(input, ["cfo_last_5y", "pat_last_5y"])
    if mismatch is not null:
        return INCONCLUSIVE("Check 5: " + mismatch)

    negative_cfo_years = count(y in input.cfo_last_5y where y < 0)
    cumulative_cfo = sum(input.cfo_last_5y)
    cumulative_pat = sum(input.pat_last_5y)

    disqualifying_event = (negative_cfo_years >= 3) or (cumulative_pat <= 0) or (
        cumulative_pat > 0 and (cumulative_cfo / cumulative_pat) < 0.80
    )

    guard = apply_track_record_guard(
        years_required = 5,
        years_available = n,   // use actual series length, not the company-wide field, since this check's window is specifically 5 FYs of CFO/PAT data
        disqualifying_event_found = disqualifying_event
    )
    if guard is not null:
        return build_result(5, guard)

    (citation, missing_prov) = compose_citation(input, ["cfo_last_5y", "pat_last_5y"])

    if negative_cfo_years >= 3:
        return FAIL(5, f"{negative_cfo_years} of last 5 years had negative CFO (>= 3 triggers fail)", citation)

    if cumulative_pat <= 0:
        return FAIL(5, f"cumulative 5-yr PAT {cumulative_pat} <= 0", citation)

    cfo_pat_ratio = cumulative_cfo / cumulative_pat
    if cfo_pat_ratio < 0.80:
        return FAIL(5, f"cumulative CFO/PAT ratio {cfo_pat_ratio} < 0.80", citation)

    return PASS(5, f"CFO/PAT ratio {cfo_pat_ratio} (>= 0.80), "
                   f"{negative_cfo_years} negative-CFO years (<= 2)", citation)
```

---

## 8. Check 6 — Executive Stability (Section A Q6)

```
function check6_executive_stability(input: CompanyInput) -> CheckResult:

    required = [cfo_changes_last_3y, restatement_of_past_accounts]
    if any(required) is null:
        return INCONCLUSIVE("Check 6: missing CFO change count or restatement history")

    disqualifying_event = (input.cfo_changes_last_3y > 1) or (input.restatement_of_past_accounts == true)

    guard = apply_track_record_guard(
        years_required = 3,
        years_available = input.years_of_track_record_available,
        disqualifying_event_found = disqualifying_event
    )
    if guard is not null:
        return build_result(6, guard)

    (citation, missing_prov) = compose_citation(input,
        ["cfo_changes_last_3y", "restatement_of_past_accounts"])

    if input.cfo_changes_last_3y > 1:
        return FAIL(6, f"{input.cfo_changes_last_3y} CFO changes in last 3 years (> 1 triggers fail)", citation)

    if input.restatement_of_past_accounts == true:
        return FAIL(6, "retroactive restatement of past accounts", citation)

    return PASS(6, f"{input.cfo_changes_last_3y} CFO change(s) (<= 1), no restatement", citation)
```

---

## 9. Master orchestrator — the gate

```
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
        revision: (prior is null) ? 1 : prior.revision + 1,
        supersedes: (prior is null) ? null : prior.result_id,
        input_digest: hash(input),
        generated_at: now(),
        citation_gaps: citation_gaps,
    }
```

**Decision table (must match `Phase1-Rules.md` §3 exactly):**

| Any FAIL? | Any INCONCLUSIVE (given no FAIL)? | Verdict |
| :-: | :-: | :-- |
| Yes | — | `REJECT` |
| No | Yes | `HOLD_INCONCLUSIVE` |
| No | No | `CLEARED_TO_PHASE_2` |

FAIL always dominates INCONCLUSIVE — a stock is never "held" when it has already failed
something; it is rejected outright.

**Re-evaluation and supersession.** A `HOLD_INCONCLUSIVE` is a temporary state by design:
when a missing field is later supplied (a manual review resolution, a re-scrape, a newly
published Annual Report), `run_phase1()` is re-run with the prior result passed in, and
the new result carries `revision = prior + 1` and `supersedes = prior.result_id`. The
verdict may legitimately move in any direction. Any artefact already handed to a user
from the prior revision — a web page, an exported PDF — is stale from that moment and
must be treated as such by the application (implementation plan §7.4).

---

## 10. Rendering layer (kept separate from the decision engine)

The functions above produce `Phase1Result`, a purely internal/analyst-facing object
(maps to `Phase1-Rules.md` §4's table). **Do not let the decision engine format
investor-facing prose.** A separate rendering function must:

1. Take `Phase1Result` as input (never re-derive numbers — display exactly what the
   engine computed).
2. Apply `user.md`'s wrapping rules (§5 of `Phase1-Rules.md`): plain-English lead,
   term explanations on first use, numbers translated to relatable facts, the
   Pass/Fail translation table, a "so what does this mean for you" line per section,
   and the verbatim SEBI disclaimer from `user.md` §9. *Verbatim* means byte-for-byte
   from a locked template constant — the disclaimer text is never regenerated,
   paraphrased, shortened, or made editable in the UI.
3. Never fabricate a number, source, or explanation not present in the underlying
   `CheckResult` objects — if `citation` is null, the renderer must surface that as
   missing sourcing rather than inventing one.
4. Render `citation_gaps` explicitly. If a verdict-bearing check has no citation, the
   report must say so ("figure used but source not recorded") in both the analyst and
   investor views. An uncited number presented as sourced is the single worst failure
   mode this system can have.
5. Stamp `revision`, `generated_at`, `as_of_date` and `data_basis` on every rendered
   artefact, web and PDF alike, so a printed report can always be matched back to the
   evaluation that produced it.
6. State the reporting basis in plain language on the investor view ("figures are on a
   consolidated basis") — rules §8.1 prefers consolidated, and a reader comparing this
   report to a standalone filing needs to know which they are holding.

Keeping this as two layers (engine → renderer) means the engine can be unit-tested
against numeric fixtures independent of prose, and the prose layer can change without
touching pass/fail logic.

---

## 11. Test fixtures to validate an implementation

Before wiring this into an app, run these fixtures through `run_phase1()` and confirm
the verdicts match, since they exercise every branch. Fixtures 1–11 validate the check
logic; 12–18 validate the data-integrity guards added in revision 2.

| # | Fixture | Expected verdict | Exercises |
| :-: | :-- | :-- | :-- |
| 1 | All 6 fields fully populated, all within safe thresholds | `CLEARED_TO_PHASE_2` | happy path |
| 2 | Audit opinion = `QUALIFIED`, everything else clean | `REJECT` (Check 1) | single-fail short-circuit reporting |
| 3 | Pledge 34%, rising trend | `REJECT` (Check 2) | §5a worked example |
| 4 | Govt shareholding 55%, promoter pledge fields all null | `CLEARED_TO_PHASE_2` if others pass | Check 2 auto-pass bypasses its own null-check |
| 5 | Promoter holding 1% of company, pledge 30% of promoter holding, 0.3% of total shares | `PASS` on Check 2 w/ low-base note | low-base guard |
| 6 | Company listed 2 years, no disqualifying events, Check 1/6 | `INCONCLUSIVE` on 1 & 6, others normal | insufficient track record → HOLD |
| 7 | Company listed 1 year but had a qualified audit opinion that year | `REJECT` (Check 1) | short history still fails on a real event |
| 8 | CFO/PAT ratio 0.79 cumulative, 2 negative-CFO years | `REJECT` (Check 5, ratio trigger only) | independent OR triggers |
| 9 | Missing `net_worth` entirely | `HOLD_INCONCLUSIVE` overall (assuming no other fails) | missing-data guard, never estimate |
| 10 | Net worth = -500 (negative) | `REJECT` (Check 4) | broken balance sheet |
| 11 | Legal fees 6x audit fees, opinion clean, no other issues | `REJECT` (Check 1, fee-ratio sub-trigger) | Check 1's 4th sub-condition in isolation |
| 12 | `years_of_track_record_available` = null, everything else clean and populated | `HOLD_INCONCLUSIVE` (Checks 1 & 6) | unknown history must not read as 0 years, nor as a sufficient window |
| 13 | `audit_fees` = 0, opinion clean, no other issues | `HOLD_INCONCLUSIVE` (Check 1) | **regression guard** — an uncomputable sub-check must never produce a FAIL |
| 14 | RPT note tagged `CONSOLIDATED`, revenue tagged `STANDALONE` | `HOLD_INCONCLUSIVE` (Check 3) | basis-mismatch guard |
| 15 | `contingent_liabilities` period FY24, `net_worth` period FY23 | `HOLD_INCONCLUSIVE` (Check 4) | period-mismatch guard |
| 16 | Promoter holding 3%, pledge 40%, `pledged_pct_of_total_shares` not reported | `REJECT` (Check 2) — derived 1.2% of total shares > 0.5% | §2c derivation + low-base FAIL path |
| 17 | Pledge 34% with no provenance entry for `pledged_pct_of_promoter_holding` | `REJECT` (Check 2), `citation` null, `citation_gaps` non-empty | citation plumbing — verdict stands, sourcing gap is visible |
| 18 | Fixture 9 re-run after `net_worth` is supplied by manual review | `revision` = 2, `supersedes` = fixture 9's `result_id`, verdict recomputed | result versioning after review resolution |

---

## 12. What this spec deliberately does not decide

These are acquisition or product concerns, resolved in the implementation plan, and are
listed here only so an implementer does not mistake their absence for an omission:

- **Where each field comes from.** The engine is source-agnostic by design. The
  field-by-field source contract lives in the implementation plan §3.
- **What confidence level is good enough to populate a field.** The engine trusts every
  non-null input it is given; the extraction layer is responsible for deciding what it
  is willing to assert (implementation plan §5.3).
- **When to re-run.** Staleness, review SLAs, and re-scrape cadence are product
  decisions (implementation plan §7.4, §12).

---

## 13. Change-control note

This file is derived entirely from `Phase1-Rules.md`. If a threshold, exception, or
decision rule changes there, mirror the exact change here in the same edit — do not let
the two drift. If an application is later generated from this spec, treat
`Phase1-Rules.md` as the source of truth for *policy* and this file as the source of
truth for *implementation shape*; neither should introduce a rule the other doesn't have.

### Revision history

**Revision 2** — implementation-shape changes only; **no policy threshold, exception, or
decision rule was altered**, and each item below traces to an existing requirement in
`Phase1-Rules.md`:

| Change | Traces to |
| :-- | :-- |
| `FieldProvenance` on `CompanyInput`, `compose_citation()` (§2a), `citation_gaps` | Rules §1 "cite the source and period for each"; §7 definition of done; this file's own `CheckResult.citation` requirement, which previously had no way of being satisfied |
| Comparability guard on basis and period (§2b), applied to Checks 1, 3, 4, 5 | Rules §8.1 (consolidated preferred) + §0 golden rule — an incomparable ratio is not data |
| `data_basis` on `CompanyInput` and `Phase1Result` | Rules §8.1 |
| `years_of_track_record_available` made nullable, with null handled in §2 | Rules §1 track-record paragraph + golden rule; previously an unset value silently read as 0 years |
| Check 1: zero/uncomputable audit fee moved out of `fail_reasons` into an INCONCLUSIVE path | Rules §1 "do not guess... mark that check INCONCLUSIVE"; the prior code returned FAIL on missing data, which contradicted policy |
| `derive_pledged_pct_of_total_shares()` (§2c) | Rules §2 Check 2 low-base exception; exact arithmetic, flagged `DERIVED` |
| `revision` / `supersedes` / `input_digest` / `generated_at` on `Phase1Result` | Rules §3 (a HOLD is temporary) + §6 guardrails — a superseded verdict must not circulate as current |
| Renderer requirements 4–6 in §10 | Rules §5 and `user.md` §9 (verbatim disclaimer) |
| Fixture 5 corrected: promoter 1% / pledge 30% / 0.3% of total | The original values (3% × 40%) are arithmetically 1.2% of total shares, not 0.3%, and would have failed rather than passed once §2c derivation exists. The corrected numbers preserve the fixture's original intent — a low-base PASS |
| Fixtures 12–18 added | Coverage for each guard above |
