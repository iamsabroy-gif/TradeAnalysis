chunkrule-v3.md — Annual Report Chunking & Extraction Rules (Note-Unit & Statement Revision)

Defines how any Indian listed company's annual report (arbitrary length, arbitrary formatting) is broken down and mapped into the CompanyInput schema used by Phase1-Algorithms-v3.md. This revision optimizes the original v3 spec to include a Statement Tier for aggregates and a Summation Tier for party-wise disclosures.

Read this before building or running any extraction step.

Golden rule: if a data point cannot be found and classified with confidence, its field stays null. Never guess a value to fill a gap. A missed section becomes INCONCLUSIVE downstream. A value read from the wrong row, or in an undeclared unit, is worse than null. Prefer null.

Revision history

v3 — introduced Note-Unit chunking and the header-vs-sub-label test to fix the "Payment to Auditors" total-row leakage error.

v4 (Optimized) — this revision. Live runs against party-wise RPT tables (Oswal, Minda) showed that declining these reports (the v3 "correct failure mode") created too many INCONCLUSIVE results. v4 introduces a "Summation Tier" to aggregate party-wise rows and a "Statement Tier" to source core aggregates (Revenue, Net Worth) directly from the audited Balance Sheet and P&L.

0. Why chunk this way

Two annual reports are never formatted the same way. We avoid token-budgeted chunks because they split notes mid-table. The atomic unit of an annual report's notes block is **the note**. Never split one; never merge two.

1. Step 1 — Structural split (mechanical, format-agnostic) — for BASIS TAGGING only

Goal: turn one large PDF into a bounded, ordered list of coarse sections, and tag each with its reporting basis (STANDALONE / CONSOLIDATED / NOT_APPLICABLE). Prefer PDF bookmarks/TOC metadata. Preserve page numbers on every chunk.

Output of Step 1: an ordered list of coarse chunks, each with {text, page_range, heading_path, basis, source_confidence}.

1a. Technique — locate with OCR, confirm with vision (mixed text/scanned reports)

NOT YET IMPLEMENTED. Current pipeline skips SCANNED_IMAGE_Lonly reports. Future state: OCR for location $\rightarrow$ Vision for authoritative value extraction.

2. Step 2 — Canonical target schema

Category | What it's looking for (meaning, not wording) | Keyword anchors | Source
audit_opinion | The auditor's formal opinion paragraph | masthead + confirmer, see §3a | AR
auditor_resigned_mid_tenure_last_3y | Auditor resignation during tenure | "resignation of statutory auditor", CARO clause 3(xviii) | AR
audit_fees | Statutory audit fee as reported in notes | "payment to auditors", "auditor's remuneration", "remuneration to auditors", "auditor remuneration", "statutory audit" | AR
legal_fees / legal_fees_prior_year | Legal & professional charges, current and prior column | "legal and professional", "legal fees", "legal charges" | AR
industry_sector | NSE/BSE sector classification | — | NOT in the AR
working_capital_cycle_tier | NSE/BSE sector classification mapped to cycle tier | — | NOT in the AR
legal_fee_surge_explained | Whether a disclosed one-off cause explains a >2x YoY jump in legal_fees | "legal and professional" note + "contingent liabilit" | AR (Contingent Liabilities note)
related_party_transactions (rpt_sales_plus_purchases) | Related party sales + purchases (summed if party-wise) | "related party transactions", "related party disclosures", "Ind AS 24", "AS 18" | AR
contingent_liabilities | Disclosed contingent claims, guarantees, disputed demands — lump total | "contingent liabilit", "claims against the company not acknowledged", "guarantees" | AR
litigation_claims_exposure | Sum of the Schedule III sub-categories representing genuine contested/disputed risk | "claims against the company not acknowledged", "disputed", "demand raised", "contested" | AR — same note, sub-category rows only
routine_guarantee_exposure | Sum of the Schedule III sub-categories that scale with ordinary trade-finance/business volume | "bank guarantee", "letter of credit", "bills discounted" | AR — same note, other sub-category rows
contingent_liabilities_breakdown_available | True only if litigation_claims_exposure and routine_guarantee_exposure were both extracted as separate sums | — | Derived from whether the note itemizes sub-categories
revenue | Revenue from operations | "revenue from operations", "total income" | AR (Statement Tier)
net_worth | Total equity attributable to owners (exclude NCI) | "total equity", "shareholders' funds", "net worth" | AR (Statement Tier)
cash_flow_operations | Net cash from operating activities, multi-year | "cash flow from operating", "net cash", "operating activities" | AR (multi-report, see §7a) 
profit_after_tax | PAT, matching the cash-flow periods | "profit for the year", "profit after tax" | AR (multi-report, see §7a)
revenue_last_5y | Revenue from operations, multi-year | — | AR (multi-report, see §7a) / Screener.in 5-yr view
cumulative_working_capital_change_5y | Cash Flow Statement's "Changes in working capital" subtotal | "changes in working capital", "adjustments for changes in operating assets and liabilities" | AR Cash Flow Statement (multi-report, see §7a)
liquid_cushion_first_year / liquid_cushion_last_year | Cash & cash equivalents + Other bank balances + Current investments | — | AR Balance Sheet
restatement_of_past_accounts | Prior-period restatement (NOT routine Ind AS regrouping) | "restatement", "prior period errors", "correction of prior period" | AR
kmp_changes / cfo_changes_last_3y | CFO/KMP appointments and resignations | "key managerial personnel", "chief financial officer", "resign" | AR
regulatory_action | SEBI/RBI/SFIO/ED/CBI proceedings, penalties, show-cause | "SEBI", "SFIO", "Enforcement Directorate", "show cause", "penalty", "adjudication order" | AR (secretarial audit report + board's report)
unusual_affiliate_dealings | Loans/advances to promoter entities, circular flows | "unsecured loans given", "advances given", RPT note | AR
years_of_track_record_available | Listed/reporting history | "Nth Annual Report" on the cover | AR
company_type / govt_shareholding_pct | PSU vs professionally-managed vs promoter-led | shareholding pattern table, "promoter" | AR shareholding table; Screener for pledge
promoter_shareholding (pledge %) | Pledge/encumbrance %, trailing quarters | — | NOT in the AR — Screener.in / BSE Reg 31 only

3. Step 3 — Extraction Tiers (PRIMARY)

For each category, the pipeline executes tiers in order of specificity.

3.0 Statement Tier (High-Level Aggregates)
For fields like `revenue` and `net_worth`, search the primary audited statements (P&L, Balance Sheet). Locate the statement via anchors, identify the target row (e.g., "Revenue from operations"), and read the current year column. This bypasses the notes entirely for core figures.

3a. Locating the auditor's report specifically
Require two signals (masthead + confirmer) within the first ~1,500 characters of a page. Classify in order: ADVERSE → DISCLAIMER → QUALIFIED → CLEAN.

3b. Note-Unit Chunking
Flatten the notes region to a stream of (page, line). Segment into note units by matching `^(\d{1,3})(\.(\d{1,3}))?\s*[:.]?\s+<Title>$`. Select the longest non-decreasing run of keys to avoid false positives. Bound notes at LINE offsets. Collapse repeated headers.

3c. Row and Column Selection (The "v4" Logic)
An anchor hit yields a note.
1. Header-vs-Sub-label Test: If the anchor is the note's header, a `Total` row is the value. If it is a sub-label, reject the `Total` and read only the labeled row.
2. Summation Tier:
    - Party-wise RPT: If no Total row exists but multiple rows match party-wise patterns, sum them to derive the total.
    - Contingent Breakdown: Sum rows matching "disputed/contested" for `litigation_claims_exposure` and "guarantees/LCs" for `routine_guarantee_exposure`.
3. Bound the table: Stop at the first footnote marker, sub-section heading, or prose paragraph.
4. Read Columns: First numeric column is current year, second is prior year.

3d. Units
Capture the declaration (e.g., "All amounts are in Lakhs"). Carry it forward from the last declaration seen at or before the page. Normalize to Lakh before storing.

4. Step 4 — Embedding/LLM classification (FALLBACK)
Run only for categories §3 could not place. Do not force a classification of irrelevant content.

5. Step 5 — Basis tagging (consolidated vs standalone)
Detect structurally from "Report on the audit of the (standalone|consolidated) financial statements" headings. Prefer consolidated per Phase1-Rules-v2.md §8.1.

6. Step 6 — Resolve multiple matches per category
Prefer audited notes over narrative. Prefer consolidated over standalone.

7. Step 7 — Populate CompanyInput with provenance
Record: source, period, basis, page, note_key, row label, unit, anchor type (header/sub-label), confidence, method.

8. Step 8 — Validate before handing off to the rule engine
Verify basis, period, and unit consistency across ratio operands. No silent zero-filling.

9. Step 9 — Cache the classification map, keyed on content hash.

10. Handling format outliers

Situation | How it's handled
Integer note numbering ("37 OTHER EXPENSES") | §3b.1 — (37,0)
Decimal note numbering ("2.33 Other expenses") | §3b.1 — (2,33)
Sectioned numbering with colon ("39.2 : Contingent Liabilities") | §3b.1 — (39,2)
Note header reprinted on continuation pages | §3b.4 — collapse equal consecutive keys
Several notes on one page | §3b.3 — line-level bounds, never page ranges
Unit declared on some pages only | §3d.2 — carry the last declaration forward
Target is a sub-label inside a larger note | §3c.1 — reject the parent's Total
Party-wise RPT table with no per-group total | §3c.2 — Handled via Summation Tier (sum individual party rows)
Whole report scanned/image-only | §1a, NOT YET IMPLEMENTED — INCONCLUSIVE
Non-standard section naming ("Report of the Statutory Auditors") | §4 fallback

11. Validation before trusting this on a new company

Measured results, three FY2025-26 reports:

Field | Dynamic (lakh) | Oswal Pumps (million) | Minda Corp (million)
audit_fees | 3.07 ✓ | 4.74 ✓ | 21 ✓
legal_fees | 21.46 ✓ | 43.52 ✓ | 436 ✓
contingent_liabilities | 0.0 ✓ | 50.55 ✓ | 1,052 ✓
rpt_sales_plus_purchases | 256.56 ✓ | 1,240.12 ✓ | 8,450.11 ✓
unit resolved | lakh ✓ | million ✓ | million ✓
note units segmented | 61 | 53 | 45

10/10 on fields with a known truth. v4 fixed the RPT "declined" issue seen in v3 by implementing party-wise summing.

12. Definition of done for this chunking layer

- Report split into page-tagged structural chunks with basis tagging (§1, §5)
- Notes block segmented into note units by numbering, line-bounded (§3b)
- Every relevant category located via keyword anchor (§3) or fallback (§4)
- Row read decided by header-vs-sub-label test and Summation Tier (§3c)
- Current and prior columns distinguished; dashes read as nil (§3c.4)
- Unit resolved, carried forward, and normalized (§3d)
- Multiple-match categories resolved by preference order (§6)
- CompanyInput populated with full provenance including row label and anchor type (§7)
- Basis, period and unit consistency validated (§8)
- Classification map cached (§9)
- No field silently defaulted — every null represents a genuine "not found"

Summary of the v3 → v4 change

v3 solved the "Payment to Auditors" total-row leakage by introducing Note-Unit chunking and the sub-label test. v4 extends this by adding a Statement Tier for high-level aggregates (Revenue/Net Worth) and a Summation Tier for party-wise disclosures (RPT, Contingent Liabilities), moving the pipeline from "declining" complex tables to "resolving" them via aggregation.
