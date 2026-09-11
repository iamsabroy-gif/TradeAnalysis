Phase 1 Gatekeeper Rules (v2)

Operating instructions for running the "Trust Check" governance screen on a stock and returning the verdict. Read this file top to bottom before analysing. It defines the data to gather, the exact pass/fail logic, the decision rule, and how the result must be written up for the investor. This is a red-flag elimination filter, not a buy signal — the only outputs are REJECT, CLEARED TO PHASE 2, or HOLD — INCONCLUSIVE.

Source checklist: this screen operationalises Section A — Red Flags & Governance, Q1–Q6 of this project's own Stock - Analysis - Question - Set.md. Every check below maps 1:1 to one of those six questions. Debt and leverage (Section F of the question set) is deliberately not part of this filter — that belongs to Phase 2 (Core Health). Keep that boundary.

Communication rules: every investor-facing verdict produced from this file must be written through user.md — plain English first, jargon explained the moment it appears, numbers translated into relatable facts, the Pass/Fail translation table, a "so what does this mean for you" line per section, and the fixed disclaimer from user.md §9. §5 of this file shows exactly how that wrapping works.

Revision history

v2 — this revision. Closes three specific sourcing gaps identified during the Cyient DLM live run: (1) Check 5 was allowed to pass/fail silently on fewer than 5 years of data without the shortfall being visible downstream; (2) Check 2's pledge trend was routinely inferred from a single latest-quarter figure plus a "no new pledge" compliance filing, rather than actually retrieved as a quarterly series; (3) Checks 1 and 6's negative findings ("no regulatory action found", "no restatement found") were being sourced from generic web search rather than the specific regulatory registry / disclosure the finding depends on. No pass/fail threshold changed. Every change below is a sourcing and disclosure requirement, not a new policy line. Specific additions:

§1: Inputs table now names, per check, the specific query/registry required — not just "a preferred source" — and marks which fields must never be silently derived.
§1a (new): explicit rule that a short track record must be disclosed, not just silently evaluated, whenever fewer than the required years of data were available — applies even when the check still resolves to PASS/FAIL rather than INCONCLUSIVE.
§2, Check 2: pledge trend must come from an actual quarterly series; a single point-in-time figure plus a "no new pledge" filing is a weaker, explicitly flagged substitute, not a full substitute.
§2, Check 1 & Check 6: regulatory-action and restatement sub-checks must be sourced from the named registry/search terms in §8.4, not a generic web pass.
§8.4 (new): "Targeted retrieval per check — closing v1 gaps", with the exact registries and search strings each of the four items above requires.
§9 (renumbered from §7): definition-of-done now includes a confidence-sourcing checklist.

Update (Sep 2026, filename unchanged to preserve existing §8.4-A/B/C/D cross-references from Phase1-Algorithms-v3.md and chunkrule-v3.md): Check 1.4's "Legal vs. Audit fee anomaly" sub-condition is redefined. The flat "> 5x audit fees" / "> 2x YoY surge" thresholds were hardcoded and industry-agnostic; no published benchmark exists for a legal-fee-to-audit-fee ratio, and audit fees are a poor denominator on their own (fixed-cost floor confounds company size with legal intensity — see §8.4-E). The sub-check is now a revenue-normalized, industry-tiered test (legal & professional charges ÷ revenue vs. a sector band, per new §8.4-E), with the audit-fee ratio retained only as a non-binding secondary observation, and the YoY surge test gated on whether a disclosed one-off cause exists. This is a threshold-and-metric change, unlike v2's sourcing-only changes above — see §8.4-E for full rationale, sourcing, and the industry band table.

Update 2 (Sep 2026, same filename-stability reason as above): Check 4 and Check 5 are similarly redefined, for the same underlying reason — a single flat threshold applied identically across every industry is not sound practice for either check. Check 4's flat "> 15% of net worth" on *total* contingent liabilities is replaced by a litigation-vs-routine split (Schedule III already requires the sub-category breakdown) with a single conservative threshold applied only to the litigation/claims portion — the old rule would have rejected nearly the entire banking, NBFC, and EPC/infrastructure sectors purely from routine guarantee/LC/forex business, which is not the check's intent (see §8.4-F). Check 5's flat "0.80 CFO/PAT, ≥3-of-5-years-negative" rule is replaced by working-capital-cycle tiering (long-cycle/project-accounting sectors like EPC and real estate legitimately run lower and more volatile, asset-light sectors should be held to a tighter bar), a hard global floor of 0.50 that no tier can loosen, and an explicit "not applicable" treatment for banks/NBFCs/insurers, whose CFO is dominated by loan-book movement rather than P&L-linked working capital (see §8.4-G). Both are genuine threshold/metric changes — see §8.4-F and §8.4-G for full rationale, sourcing, and the tier tables.

Update 3 (Sep 2026, same filename-stability reason as above): Check 5 gains a use-of-funds verification override (new §8.4-H), prompted by a live Phase 1 run on GRSE that failed the CFO/PAT hard floor by a wide margin (ratio 0.055) in a way a follow-up forensic trace showed was overwhelmingly explained by working-capital absorption behind genuine revenue growth, not cash going missing. Every Check 5 disqualifying trigger except cumulative PAT ≤ 0 (negative-years count, the sector-tier ratio floor, and the former unconditional 0.50 hard floor) is now a candidate for reclassification from FAIL to a disclosed PASS-with-warning — but only when three sourced, objective conditions are all independently verified (real revenue growth, the shortfall traced to the Cash Flow Statement's own working-capital line, and no evidence of the cash instead piling up as an idle, growing cushion). An unverifiable or unverified shortfall stays FAIL exactly as before — this is an affirmative, evidence-gated upgrade path, never a default or a narrative-based exception, and it applies to Check 5 only (see the Guardrail 1 note in §6 for why this is not a general "growth story" carve-out). See §8.4-H for the exact formulas, thresholds, and sourcing steps, and §5d for the required investor-facing disclosure pattern.
0. Core principle

Phase 1's job is capital preservation, not opportunity-finding. It answers one question: is this company honest and stable enough to be worth studying? Six checks stand at the door — the same six questions as Section A of the question set. If a stock fails even one check, it is REJECTED — stop immediately. Do not build a valuation, do not look at the price chart, do not weigh the growth story against a red flag. The moment one check fails, the analysis is over and the verdict is REJECT.

Treat this as strictly pass/fail per check, never a score out of six.

1. Inputs (what to gather before deciding)

For the stock under review, collect these data points. Cite the source and period for each. The "Section A Q#" column shows which question set item each check answers. The "Retrieval requirement" column is new in v2 — it names the specific query or registry each field needs, not just a preferred source, per §8.4.

#	Section A Q#	Check	Data to pull	Preferred source	Retrieval requirement (v2)
1	Q1	Auditor & regulator	Auditor resignation (last 3 yrs)? Audit opinion type? Active/5-yr fraud probe (SEBI/ED/CBI/SFIO)? Legal vs. audit fee anomaly (now revenue-normalized, industry-tiered — see §2 Check 1.4 and §8.4-E)? Also pull: Revenue (same FY/basis as legal fees) and the company's industry-sector classification (Screener.in / NSE-BSE sector tag).	Annual Report → Independent Auditors' Report → "Opinion", Notes → "Auditor remuneration" & "Legal charges" & "Revenue from operations"; Screener.in company header for sector classification; Google name + auditor resigns, + SEBI	Regulatory-action sub-check MUST be run against §8.4-A (named registry + query string), not a generic web search alone. Legal-fee-anomaly sub-check MUST be run against §8.4-E's industry-tiered revenue bands, not a flat multiple of audit fees — see rationale there.
2	Q2	Promoter pledge	Promoter pledge % (latest); pledge trend over last ~4 quarters; is it a govt PSU or zero-promoter (professionally managed)?	Screener.in → Shareholding Pattern	Trend MUST be the actual trailing-4-quarter series per §8.4-B; a single latest figure plus a "no new pledge" filing is a flagged fallback only, per §1a
3	Q3	Related-party leakage	RPT (sales + purchases) as % of revenue; any unusual affiliate loans/deals	Annual Report → notes → "Related Party Transactions"	—
4	Q4	Contingent liabilities	Net worth (total equity); the Contingent Liabilities note broken into its Schedule III sub-categories (see §8.4-F) — do not pull a single lump total, the split is required	Annual Report → "Contingent Liabilities" note (full sub-category breakdown), Balance Sheet	Litigation & claims exposure MUST be computed from the Schedule III sub-categories per §8.4-F, not a single blended total — see rationale there for why a blended total breaks this check for banks/NBFCs and EPC/infra contractors
5	Q5	Cash conversion	5-yr cumulative CFO (cash from operations); 5-yr cumulative PAT (profit after tax); count of years (of 5) with negative CFO; the company's working-capital-cycle tier (see §8.4-G)	Cash Flow statement vs P&L, 5 years (Screener.in or Annual Reports)	If fewer than 5 years of source documents are available, actively attempt to close the gap per §8.4-C (Screener 5-yr view, RHP/DRHP pre-listing financials, or an older Annual Report) before falling back to a partial window; §1a governs disclosure either way. CFO/PAT threshold and the negative-CFO-year count MUST be read against the sector's working-capital-cycle tier per §8.4-G, not a flat 0.80/≥3-of-5 rule applied to every industry — see rationale there.
6	Q6	Executive stability	Number of CFO changes (last 3 yrs); any restatement of past accounts	Board's Report (KMP changes); Google name CFO resigns	Restatement sub-check MUST be run against §8.4-D (specific search terms + Auditor's Report Emphasis-of-Matter check), not a generic word search of the report text alone

If a required data point is unavailable or unverifiable, do not guess. Mark that check INCONCLUSIVE — data not available, and treat it as a hold (see §3): the stock cannot be CLEARED while any check is inconclusive, but do not fabricate a Fail either. State exactly what is missing and where it would normally be found.

Track record shorter than the lookback window: If the company has been listed or reporting for less than the required window (3 years for Checks 1 & 6, 5 years for Check 5), do not FAIL or PASS on partial data. Evaluate over whatever full years are actually available and mark the check INCONCLUSIVE — insufficient track record (only N years available) rather than PASS or FAIL. Exception: if even one available year shows a disqualifying event (e.g. a qualified audit opinion, a CFO exit tied to a restatement), that still triggers an immediate FAIL — a short history can still fail, it just cannot "pass" prematurely.

1a. Disclosure requirement for a short track record (new in v2)

The exception above — "a short history can still fail" — was, in v1, silent about the shortfall once it produced a FAIL: the finding text said only "cumulative CFO/PAT ratio X < 0.80", with no indication that X was computed over 4 years instead of the required 5. That is a real gap: a reader has no way to tell a fully-evidenced FAIL from a FAIL reached on 80% of the required window.

From v2 onward, every finding produced under the short-track-record exception — whether it resolves to FAIL or to INCONCLUSIVE — must state the years actually used against the years required, in the finding text itself (e.g. "cumulative CFO/PAT ratio −0.12 < 0.80 (based on 4 of the required 5 years — FY22 not available from source documents)"). This applies to Checks 1, 5, and 6, the three checks with a lookback window. See Phase1-Algorithms.md §2 and §7 (Check 5) for the corresponding implementation change.

This is a disclosure rule, not a threshold change: a disqualifying event found in a partial window still fails exactly as it did in v1. The only change is that the shortfall is now always visible in the output, never only in the analyst's working notes.

2. Pass / Fail logic (exact thresholds — unchanged from v1)

Apply each rule literally. "Safe" = Pass; any listed danger condition = Fail.

Check 1 — Auditor & Regulator Integrity (Section A Q1)

FAIL if any of the following apply:
Auditor resignation: Statutory auditor resigned mid-tenure within the last 3 years.
Audit opinion: Most recent audit report contains a "qualified", "adverse", or "disclaimer of opinion".
Regulatory / Criminal action: Active or past 5-year investigation, charge-sheet, probe, or material sanction/debarment by SEBI, RBI, SFIO, ED, CBI, or EOW involving fraud, siphoning, market manipulation, or accounting irregularities (excludes routine, immaterial secretarial/procedural fines). v2: this sub-check must be run per §8.4-A. A "no action found" result sourced only from a generic web search is a lower-confidence substitute and must be labelled as such (see §5, confidence labelling).
Legal vs. Audit fee anomaly (redefined — see §8.4-E): a flat "> 5x audit fees" multiple, applied identically across every industry and company size, is not sound — audit fees do not scale linearly with revenue (a fixed-cost floor means small/mid-caps carry a structurally higher audit-fee-to-revenue ratio than large caps at identical legal intensity, per Indian audit-fee research showing only a "modest" fee-to-turnover correlation), and no published benchmark exists for a "legal fee ÷ audit fee" ratio specifically — it is not a recognized forensic or audit metric. What is independently benchmarked, by industry, is legal & professional spend as a % of revenue (Acritas "Patterns in Legal Spend" report; ACC Law Department Management Benchmarking Report for the overall average). This sub-check is rebuilt around that metric:
  (a) Revenue-intensity test (primary): Legal & professional charges ÷ Revenue exceeds the company's sector flag-threshold in the §8.4-E table.
  (b) Unexplained surge test: Legal & professional charges show an unexplained > 2x year-on-year increase, AND no disclosed one-off cause (e.g. an M&A due-diligence exercise, a disclosed litigation settlement, legal costs tied to a capital raise) is found in the Contingent Liabilities note, Board's Report, or news — check for such a cause before treating the surge as a fail trigger; a disclosed, non-concerning cause means this sub-condition does not fire.
  (c) Legal ÷ Audit fee ratio (secondary, non-binding): may be noted alongside (a) when informative, but is never used alone to FAIL, for the denominator reason above. A ratio above 5x that sits inside the sector's revenue-intensity band is recorded as an observation, not a red flag.
FAIL this sub-condition if (a) or (b) is true. PASS only if all conditions are clear (clean opinion, no mid-tenure resignation, no fraud-related probes/sanctions, and legal spend within its sector's revenue-intensity band with no unexplained surge).

Check 2 — Promoter Pledge & Encumbrance (Section A Q2)

Auto-PASS Exceptions:
Government-owned PSUs: Defined as government (central + state, direct or indirect) shareholding ≥ 51% per the latest shareholding pattern (e.g. GRSE, HAL, BEL, NTPC) — government does not pledge; this check is N/A. A partially-disinvested former PSU below this 51% threshold does not qualify for the auto-pass and must be evaluated under the normal thresholds below like any other company.
Professionally managed companies: Zero (0%) promoter holding (e.g. ITC, L&T, ICICI Bank) — no promoter shares exist to pledge.
FAIL if either of the following applies:
Absolute threshold: Latest pledged/encumbered shares > 10% of total promoter holding.
Rising trend: Pledged % has shown an upward trend over the last 2–4 quarters (or an unexplained single-quarter spike of > 2%), signaling promoter liquidity stress. v2: this trend must be evaluated from the actual trailing-4-quarter series per §8.4-B. If only a single latest-quarter figure plus a "no new pledge" compliance filing could be sourced, the trend leg of this check is downgraded to a flagged low-confidence PASS-lean rather than a fully-evidenced PASS — see §5.
PASS only if: Pledged shares are ≤ 10% of promoter holding AND stable or declining over the last 4 quarters (ideal is 0%).
Low-base guard: If promoter holding is below 5% of total company shares outstanding, do not apply the >10%-of-promoter-holding threshold in isolation — a tiny promoter base can make a small pledge look alarming in percentage terms. Also compute pledged shares as % of total company shares outstanding. FAIL only if either (a) pledged shares exceed 10% of promoter holding and pledged shares exceed 0.5% of total company shares, or (b) the absolute value of pledged shares is material relative to the promoter's other disclosed liquidity. Otherwise mark PASS with a note: "pledge % elevated due to small promoter base, not treated as a red flag."

Check 3 — Related-Party "Leakage" (Section A Q3)

FAIL if: RPT (sales + purchases) > 5% of revenue (excluding ordinary, heavily regulated dealings), OR there are large/unexplained loans or deals with promoter-owned unlisted affiliates.
PASS if RPT ≤ 5% and no suspicious affiliate transactions.

Check 4 — Contingent Liabilities (Section A Q4)

A flat "> 15% of net worth" applied to the *total* disclosed contingent liabilities figure is not sound (see §8.4-F): routine, business-linked exposures — bank guarantees, letters of credit, bills discounted, forex/derivative notional — dominate the total for banks, NBFCs, insurers, and EPC/infrastructure/capital-goods contractors as an ordinary feature of how those businesses operate, not as a sign of concealed risk. A large private Indian bank's *total* disclosed contingent liabilities have run to several times its net worth in ordinary years purely from routine guarantee/LC/forex business — a flat 15%-of-net-worth rule would REJECT nearly the entire banking and EPC/infra sectors on that basis alone, which is not the check's intent. The check is therefore rebuilt around the sub-category the Companies Act's Schedule III already requires every company to disclose separately:

FAIL if **either**:
  1. Net worth ≤ 0 (broken balance sheet) — unchanged, applies to every company regardless of sector.
  2. **Litigation & claims exposure** — the sum of the Schedule III sub-categories that actually represent contested/disputed risk to the company ("claims against the company not acknowledged as debts," disputed tax demands, contested claims for non-execution of orders, and any guarantee given specifically on behalf of a promoter/related-party entity outside the ordinary course of business — cross-reference Check 3's RPT data for the last item) — exceeds **20% of net worth** (§8.4-F).
  Routine, business-linked exposure (bank guarantees/letters of credit issued in the ordinary course, bills discounted) is **excluded from this numerator entirely** — it is not merely re-thresholded, because its scale is a function of business/transaction volume, not risk, and is not comparable across a bank, an EPC contractor, and an FMCG company.
PASS if net worth > 0 and litigation & claims exposure ≤ 20% of net worth.
Formula: Litigation & Claims Exposure ÷ Net Worth × 100 (see §8.4-F for the exact sub-category composition and the fallback for reports that don't disclose the Schedule III breakdown).

Check 5 — Show Me the Cash (Section A Q5)

A flat 0.80 CFO/PAT threshold and a flat "≥3 of 5 years negative" trigger, applied identically to every industry, is not sound (see §8.4-G): a business with a long working-capital/project-accounting cycle (EPC, construction, infrastructure, real-estate development) legitimately shows PAT arriving as cash later than an asset-light services business (IT, FMCG, pharma) does, and can show more low or negative-CFO years in the ordinary course of executing multi-year projects without that indicating earnings manipulation. Lending institutions (banks, NBFCs, insurers) are excluded from this metric altogether — their operating cash flow statement is dominated by the movement in the loan/advances book and deposits, which is their core business, not "working capital" in the sense this ratio assumes; forcing a CFO/PAT threshold onto a bank produces a number that is not meaningful in either direction.

**Global backstop that is never overridden:** Cumulative PAT ≤ 0 → FAIL, unconditionally. A company that lost money overall is a fail regardless of sector, regardless of what it did with whatever cash it had — there is no "used it for expansion" story that rescues a company that didn't actually turn a profit. This is the one Check 5 trigger with no verification override.

**Every other disqualifying trigger below is now a candidate for the use-of-funds verification override (new — see §8.4-H), not an automatic FAIL.** A live Phase 1 run on GRSE (Sep 2026) surfaced the case this section is written for: a defence shipbuilder failed the 0.50 hard floor by a wide margin (ratio 0.055), and a follow-up forensic trace of the Cash Flow Statement showed the shortfall was overwhelmingly explained by working-capital absorption funding a genuinely growing order book (revenue nearly quadrupled over the same window) plus an accounting-classification effect (customer advances parked in bank deposits, which Ind AS 7 books as investing rather than operating cash flow) — with no evidence of the cash instead piling up unproductively. Treating that as a hard, unappealable REJECT would have been wrong. But the fix is not to loosen the thresholds — it is to require the shortfall to be **verified**, with objective, sourced criteria, before a low ratio is downgraded from a red flag to a disclosed-but-accepted finding. An unverified shortfall still fails exactly as before.

The disqualifying triggers eligible for verification:
  1. Cumulative CFO ÷ PAT **< 0.50** (the former unconditional hard floor — now the strongest candidate for override, since GRSE's own case sat here).
  2. Cumulative CFO ÷ PAT below the company's sector tier threshold (0.65 long-cycle/project-accounting, 0.75 moderate-cycle, 0.85 short-cycle/asset-light, 0.75 default if unclassified — §8.4-G).
  3. Negative operating cash flow in ≥4 of the last 5 years (long-cycle/project-accounting sectors) or ≥3 of the last 5 years (every other sector) — §8.4-G.

**Use-of-funds verification (§8.4-H):** when any of the three triggers above fires, do not resolve the check yet. Attempt to verify whether the shortfall is explained by genuine business expansion, using three objective conditions (all three required, exact formulas and sourcing in §8.4-H):
  (a) **Growth is real** — cumulative revenue over the 5-year window grew by at least 50% (latest year ≥ 1.5x earliest year), not just working capital.
  (b) **The shortfall is a working-capital story, not an unexplained gap** — the Cash Flow Statement's own "changes in working capital" reconciling line accounts for at least 60% of the magnitude of the cumulative PAT-minus-CFO gap.
  (c) **Not hoarding** — the liquid cushion (cash + bank deposits/FDs + current investments) as a percentage of revenue in the latest year is flat or lower than in the earliest year of the window (allowing a small 10%-of-ratio tolerance for normal noise), i.e. the company is not accumulating a growing pile of unproductive cash alongside the low ratio.

  - **If all three conditions are met and sourced:** the check resolves to **PASS**, but the finding **must carry a mandatory, explicit warning note** — this is a disclosed caveat, not a silent pass. State the ratio, which trigger(s) it breached, and the verified explanation, in both the internal table and the investor-facing write-up (§8.4-H, §5 below).
  - **If the verification data needed for (a)/(b)/(c) is not available:** the check stays **FAIL** — an unverifiable "maybe it's just growth" is not a benefit of the doubt this screen extends; verification is an affirmative, evidence-based upgrade, never a default.
  - **If the data is available but any of the three conditions is not met:** the check stays **FAIL**, and the finding should say which condition(s) failed — this is now positive evidence against the benign explanation, not merely an absence of evidence.
PASS (without a warning note) if none of the three disqualifying triggers fires in the first place.
v2: if evaluated on fewer than 5 years (see §1a), the finding text must state "(based on N of 5 years)" regardless of whether the result is FAIL, PASS-with-warning, or INCONCLUSIVE.

Check 6 — Executive Stability (Section A Q6)

FAIL if: > 1 CFO change in the last 3 years, OR any retroactive restatement of past accounts. v2: the restatement sub-check must be run per §8.4-D — a specific search for "restatement" / "prior period error" / "Ind AS 8" plus a check of the Auditor's Report for an Emphasis of Matter paragraph, not a general keyword scan of the report text (which can miss a restatement disclosed only in a note or auditor's paragraph the scan didn't target, and can also be confused by unrelated ESG/BRSR data restatements — see §8.4-D for the disambiguation rule).
PASS if CFO changes ≤ 1 and no restatement.
3. Decision rule (the gate — unchanged from v1)
Evaluate all six checks (PSUs and zero-promoter companies auto-pass Check 2).
If any check = FAIL → verdict is REJECT. Report the failing check(s) and stop. Do not proceed to any further analysis.
If any check = INCONCLUSIVE (and none failed) → verdict is HOLD — INCONCLUSIVE. List what data is missing to close it.
If all six checks = PASS → verdict is CLEARED TO PHASE 2. State explicitly that this means only "honest enough to study," not "buy." A CLEARED verdict is a passed background check, nothing more.

Order of reporting: it is fine to short-circuit — once a Fail is found, the stock is rejected regardless of the other checks — but for a full record, still report the status of every check that was actually assessed.

4. Internal working table (analyst view — precise, technical)

This is the raw evidence table. It stays exact and numeric — the plain-English wrapping happens in §5, on top of this table, never instead of it.

# Phase 1 — <Company Name> (<TICKER>)
**As of:** <date data pulled>   **Type:** <Private promoter / Govt PSU / Professionally managed (0% promoter)>

## VERDICT: <REJECT | CLEARED TO PHASE 2 | HOLD — INCONCLUSIVE>
<one line: e.g. "Failed Check 2 (promoter pledge 34%, rising) — stop here.">

| # | Check | Finding (with number) | Source | Confidence | Pass/Fail |
| :-: | :-- | :-- | :-- | :-- | :-: |
| 1 | Auditor & regulator | | | | |
| 2 | Promoter pledge | | | | |
| 3 | Related-party txns | | | | |
| 4 | Contingent liabilities | | | | |
| 5 | Cash conversion | | | | |
| 6 | CFO stability | | | | |

## Why the verdict
- <for each FAIL: the number, the threshold it breached, and the plain-language risk>
- <for a CLEARED verdict: confirm all six passed and restate the thresholds cleared>

## What the data does NOT let us conclude
- <any check marked inconclusive, and exactly which document would close it>

## Sourcing confidence notes (new in v2)
- <any finding sourced from a fallback path in §8.4 rather than the named primary
  registry/series — named explicitly, even when it didn't change the verdict>

Formatting rules for this internal table:

Every quantitative finding must be sourced (document + period, e.g. "FY24 AR, Note 34" or "Screener, as of DD-MMM-YYYY"). No unsourced numbers.
Show the actual number against the threshold for each check ("pledge 12% vs 10% limit"), not just "Fail".
Separate what the data shows from what it implies.
Never soften a Fail into a "watch item." A breached threshold is a Fail and a REJECT — the single, narrow exception is Check 5's use-of-funds verification (§8.4-H): a cash-conversion trigger that clears all three sourced, objective conditions there becomes a disclosed PASS-with-warning, never a silent one. Every other check's Fail is final, and even Check 5's exception requires evidence, not a narrative — see the Guardrail 1 note in §6.
v2: the new Confidence column records, per check, whether the finding came from the primary source named in §8.4 (HIGH), a documented fallback (MEDIUM), or a generic search with no targeted registry available (LOW). A LOW confidence tag never blocks a verdict — the data is still the best available — but it must be visible, and it must be carried into the investor-facing write-up per §5.
5. Investor-facing output (must run through user.md)

The internal table in §4 is the analyst's working evidence. It is never shown to the investor on its own. Every time this screen is actually run against a real stock, the final response must be re-expressed through user.md's rules before it is sent:

Open with a one-to-two sentence plain-English verdict in storytelling form — the investor should know the answer before any numbers appear.
Explain every technical term (promoter pledge, contingent liabilities, CFO, PAT, etc.) in plain language the moment it is first used — analogy first, label second (user.md §2, §10).
Translate every number into a relatable fact, not a bare figure.
Use the exact Pass/Fail translation table from user.md §4:
CLEARED TO PHASE 2 → "Passed the honesty check — safe to look deeper"
REJECT (Phase 1) → "Failed the honesty check — stop here, do not invest"
Close every section with a "so what does this mean for me" line.
Keep paragraphs short (3–4 lines) for mobile reading.
End with the disclaimer, verbatim, from user.md §9.
Never imply a guaranteed return anywhere in the write-up (this screen makes no return forecast at all).
CLEARED TO PHASE 2 means "safe enough to study further" — it is never a buy signal. Say this explicitly every time a CLEARED verdict is delivered, per user.md's own translation table.
v2 — confidence labelling: where §4's internal table carries a MEDIUM or LOW confidence tag on a finding, the investor-facing section for that check must say so in plain language — not with the word "confidence" or "LOW", but by naming what wasn't directly confirmed. For example: "We could confirm the promoter hasn't pledged any shares right now, and that a recent filing says no new pledge was created — but we weren't able to pull the quarter-by-quarter trend, so we can't independently confirm the pledge has been at zero the whole time, only that it is now." This is not a hedge on the verdict — it is telling the investor exactly how solid the underlying evidence is, per chunkrule.md's "located, not confirmed" principle applied at the check level, not just the page level.
v2 — partial track record: per §1a, any Check 1, 5, or 6 finding based on fewer years than required must say so in the investor-facing text too, in plain language (e.g. "over the four years we had reports for" rather than silently saying "over five years").
New — use-of-funds warning disclosure: when Check 5 resolves via the §8.4-H override (PASS-with-warning), the investor-facing text must devote its own clearly-labelled paragraph to it — not a footnote, not a one-line aside folded into the "all six passed" summary. State: the actual ratio and which line it breached, in plain language what that number would normally mean, and then the three things that were actually verified (real revenue growth, the shortfall traced to working capital, no sign of the cash simply piling up) — see the worked example in §5d. A CLEARED verdict that carries this warning must still say "CLEARED TO PHASE 2 means safe enough to study further, not buy" exactly as any other CLEARED verdict does; the warning is a caveat on one input, not a downgrade of the overall verdict once it has legitimately passed.
5a. Worked example — REJECT verdict, translated

The short answer: This company failed our honesty check — one of its promoters has pledged a large and rising share of their stock as loan collateral. We stop here and do not go further.

Here's what that means. When a promoter (the founder or controlling owner) borrows money against their own shares in the company, it's called a share pledge. Think of it like someone taking a personal loan by putting up their house as collateral — if things go wrong, the lender can seize those shares and sell them, flooding the market and hurting every other shareholder, including you.

In this case, the promoter has pledged 34% of their holding, and that number has been rising every quarter (Screener.in, shareholding pattern, as of Jun-2026) — well above the 10% level we treat as a warning line.

So what does this mean for you? This isn't a business-quality problem, it's a trust problem — the framework caught it before you put any money in. That's the system working as intended, not a loss. We simply move on to the next candidate.

This is educational analysis only, not personalised investment advice. Please consult a SEBI-registered investment adviser before making any investment decisions.

5b. Worked example — CLEARED verdict, translated

The short answer: This company passed every honesty check we ran. That doesn't mean "buy" — it means it's trustworthy enough to be worth studying further.

We checked things like: has the company's auditor ever walked away mid-job, is the promoter (founder/owner) borrowing against their own shares, is profit actually turning into real cash in the bank rather than staying on paper, and has the finance chief (CFO — the senior executive in charge of the company's money) been stable rather than changing every year. All six came back clean.

For example, out of the profit the company reported over the last five years, more than 100% of it actually showed up as cash in the bank — a sign the earnings are real, not just accounting entries (5-yr Annual Report cash flow statements vs P&L).

So what does this mean for you? Think of this like a background check before hiring a contractor — passing it means they're honest and stable enough to talk to, not that you've already agreed to hire them. The next step, Phase 2, checks whether this is actually a good business — decent profits, healthy margins, manageable debt — before price ever enters the conversation.

This is educational analysis only, not personalised investment advice. Please consult a SEBI-registered investment adviser before making any investment decisions.

5c. Worked example — confidence labelling in practice (new in v2)

Promoter pledge — 0%, and stable as far as we can confirm. Cyient Limited (the parent company) holds about 52% of Cyient DLM, and has pledged none of it. A regulatory filing from April 2026 also confirms no new pledge was created recently.

One honest limitation: we weren't able to pull the actual quarter-by-quarter pledge history for the trailing four quarters — only today's figure plus that April filing. So while we're confident the pledge is zero right now, we can't independently show you the trend line the way we can for a company where that quarterly series was available. This didn't change the result here (0% is 0% either way), but it's a thinner piece of evidence than the rest of this report.

5d. Worked example — Check 5 PASS-with-warning via use-of-funds verification (new)

Cash conversion — passed, but with a flag worth reading. Of every rupee of profit this company reported over the last five years, only about 6 paise actually showed up as cash in the bank — normally, a number that low would be an automatic stop for us.

Here's why we didn't stop there. We traced where that "missing" cash actually went, using the company's own Cash Flow Statement, and three things checked out: first, this isn't a company standing still — its revenue nearly quadrupled over the same five years, so it needed a lot more materials and unfinished work sitting on its books to keep building. Second, the shortfall lines up almost exactly with that working-capital buildup, not with some unexplained gap. Third — and this is the part that matters most — the company isn't quietly stockpiling cash on top of that; its cash-and-deposits cushion actually shrank relative to the size of the business, and it kept paying dividends throughout without borrowing to do it.

So what does this mean for you? A low cash-conversion number is normally one of our clearest red flags, and here it would have failed outright under a flat rule. But "failed outright" and "we checked and it's explained" are different findings, and investors deserve to see both. This one cleared every honesty check — this is simply the one place where the underlying number needs a bit more context than the headline "PASS" gives you, and we're giving you that context rather than hiding it. CLEARED TO PHASE 2 still means "safe enough to study further," not "buy" — Phase 2 is exactly where a reader should look more closely at how sustainably that working-capital cycle behaves going forward.

6. Guardrails (non-negotiable)
One fail = reject. No averaging, no "5 of 6 is good enough," no overriding a red flag with a growth story — with one narrow, explicit exception: Check 5's use-of-funds verification (§8.4-H) may reclassify a cash-conversion trigger to PASS-with-warning, but only when all three of §8.4-H's sourced conditions are independently verified from the Cash Flow Statement and Balance Sheet. A management claim, an MD&A narrative, or an analyst's own judgment that "it's probably just growth" does NOT qualify — the override runs on the same numbers-and-citations discipline as every other figure in this screen, not on a story. No other check has any comparable exception; do not generalise this pattern to Checks 1-4 or 6 without a rules-file change of the same rigor as §8.4-H.
No return promises. Never state or imply a target return, "guaranteed" outcome, or profit figure — this screen makes no forecast at all.
Flag missing data, don't estimate. An unverifiable input is INCONCLUSIVE, never a confident guess.
Passing ≠ buy. CLEARED means eligible for Phase 2 study only. Say so every time, in the investor's own translation table language.
PSU exception is narrow. It applies to Check 2 (pledge) only — a government PSU still faces all five other checks.
Educational only. Close every verdict with the SEBI-registered-adviser reminder, verbatim from user.md §9.
Communication is mandatory, not optional. An investor-facing Phase 1 response that skips the user.md plain-English wrapping (§5 above) is incomplete, even if the underlying six-check analysis is correct.
Scope. This file covers Phase 1 only. Debt/leverage (Section F) and business-quality checks belong to Phase 2, which is out of scope here.
v2 — confidence is not optional either. A finding sourced from a fallback path (§8.4) must carry its confidence tag through the internal table (§4) into the investor-facing write-up (§5). Silently upgrading a fallback-sourced finding to read like a fully-verified one is treated the same as an unsourced number — not allowed.
7. Definition of done
 All six checks assessed (or explicitly marked inconclusive with the missing source named).
 Each check shows the actual figure against its threshold, with a citation.
 A single clear verdict: REJECT / CLEARED TO PHASE 2 / HOLD — INCONCLUSIVE.
 Any Fail names the specific check and breached threshold.
 The investor-facing write-up follows user.md — plain-English lead, terms explained, numbers translated, Pass/Fail table used, "so what does this mean for me" per section.
 No specific return is promised or implied; the SEBI disclaimer is present verbatim.
 (v2) Every Check 1/5/6 finding based on a shorter-than-required window states "(N of M years)" in both the internal table and the investor-facing text.
 (v2) Check 1's regulatory-action finding and Check 6's restatement finding are each sourced per §8.4, with a confidence tag if the primary registry/search wasn't reachable.
 (v2) Check 2's pledge trend is sourced from the actual trailing-4-quarter series per §8.4-B, or explicitly flagged as a latest-quarter-plus-filing fallback if not.
 (new) If Check 5 resolved via the §8.4-H use-of-funds override, all three verification conditions (and which passed) are shown in the internal table, and the investor-facing text carries its own labelled warning paragraph per §5d — never a silent PASS.
8. Data Retrieval & Execution Solution (Sources, Links & Approach)

This section defines the automated/standard retrieval pipeline for running Phase 1 on any Indian listed stock given just the company name or stock ticker.

8.1 Common URLs & Repositories
Repository / Platform	URL Pattern / Query	Primary Purpose in Phase 1
Screener.in (Primary Hub)	https://www.screener.in/company/{TICKER}/consolidated/
(or /company/{TICKER}/ for standalone)	Multi-year CFO & PAT tables (Check 5), quarterly promoter pledge trend (Check 2), and direct PDF links to Annual Reports.
BSE Corporate Announcements	https://www.bseindia.com/corporates/ann.html
(Filter: Category = "Company Update / Resignation")	Immediate disclosures on mid-tenure auditor resignations (Check 1) and CFO departures (Check 6) post-dating the latest Annual Report.
BSE Shareholding Pattern (Cross-verification)	https://www.bseindia.com/corporates/shpSecA.aspx?scripcd={BSE_SCRIP_CODE}	Official Regulation 31 filing for promoter pledge verification (Check 2) — this is the primary source for the trailing-4-quarter pledge series required by §8.4-B.
NSE Corporate Announcements (Alternative)	https://www.nseindia.com/companies-listing/corporate-filings-announcements
(Query by {TICKER})	Backup exchange feed for corporate announcements and material events.
SEBI Enforcement Orders Archive	https://www.sebi.gov.in/enforcement/orders.html	Searchable repository for official adjudication orders, debarments, or active fraud probes (Check 1) — this is the primary source required by §8.4-A, not a generic web search.
Targeted Regulatory Press Scan	Query syntax:
"{Company Name}" AND (SEBI OR "Enforcement Directorate" OR SFIO OR CBI) AND (fraud OR investigation OR debarred OR "show cause")	Web scan to detect ongoing raids, charge-sheets, or criminal probes not yet formally closed or reported in company filings — a supplement to the SEBI archive search, not a substitute for it.
8.2 What Files to Pull from Each Link
Link / Source	File / Document to Pull	Storage / Working Name	Details to Extract from File
Screener.in → "Documents" section	Annual Report PDFs for the last 5 financial years	{TICKER}_AR_FY{YYYY}.pdf (e.g. TATAMOTORS_AR_FY24.pdf)	• Independent Auditor's Report: Opinion type ("unqualified/clean" vs "qualified/adverse"), and Emphasis of Matter paragraph (check for restatement language per §8.4-D).
• Notes to Accounts (Other Expenses): "Legal and professional charges".
• Notes to Accounts (Auditor Remuneration): Statutory audit fee.
• Notes to Accounts (Related Parties): Total RPT sales/purchases, affiliate loans.
• Notes to Accounts (Contingent Liabilities): Total contingent claims.
• Balance Sheet: Net worth (Shareholders' funds).
• Board's Report: CFO/KMP appointments and resignations over 3 years.
Screener.in → Main page HTML	Tabular data rendered on company page	Raw extracted tables (JSON/Text)	• 5-year Cash Flow statement (Cash from Operating Activity).
• 5-year Profit & Loss statement (Net Profit). If fewer than 5 years render on Screener's default view, use its "10-year" toggle or the company's RHP/DRHP before falling back to a partial window (§8.4-C).
• Trailing 4-to-8 quarters Promoter holding % and Pledged % — this quarterly table, not the summary figure alone, is what closes Check 2's trend requirement (§8.4-B).
BSE / NSE Announcements	Regulation 30 corporate disclosure letters (PDF/Text)	{TICKER}_Reg30_{EventDate}.pdf	• Formal resignation letters of statutory auditors (reason given for resignation).
• Resignation/replacement letters for CFOs.
SEBI Portal / Legal Archive	Regulatory orders / Show-cause rulings (PDF/Web page)	{TICKER}_SEBI_Order_{Date}.pdf	• Relevant operative paragraphs finding management guilty of fraud, diversion of funds, or market manipulation.
8.3 Step-by-Step Extraction Approach

When initiating a Phase 1 review with just {TICKER}:

Step 1 — Rapid Screen via Screener.in:
Fetch the Screener company page.
Extract the 5-year CFO and PAT numbers. Immediately compute the 5-year cumulative CFO ÷ PAT ratio and count negative-CFO years (Check 5). If only fewer than 5 years render, follow §8.4-C before accepting a partial window.
Extract the trailing 4 quarters of promoter shareholding and pledge percentage as an actual series, not a single figure (Check 2 — see §8.4-B).
Step 2 — Annual Report PDF Acquisition:
From the "Documents" section of the Screener page, download the latest Annual Report PDF ({TICKER}_AR_latest.pdf) and prior reports if required.
Step 3 — Deep Audited Notes Extraction:
In the latest Annual Report:
Search for "Independent Auditor's Report" → check the Opinion paragraph, and separately check for an Emphasis of Matter paragraph mentioning restatement (Check 1, Check 6 — see §8.4-D).
Search for "Auditor's remuneration" and "Legal and professional" under Notes to Financial Statements → calculate Legal Fees ÷ Audit Fees (Check 1).
Search for "Related Party" note → sum sales + purchases, calculate as % of Revenue (Check 3).
Search for "Contingent Liabilities" note and "Balance Sheet" → calculate Contingent Liabilities ÷ Net Worth × 100 (Check 4).
Search "Board's Report" / "Corporate Governance Report" for KMP changes → verify CFO tenure stability over the last 3 years (Check 6).
Step 4 — Watchdog & Corporate Announcement Verification:
Query BSE/NSE corporate announcements for the trailing 12 months for keyword "Auditor" or "CFO" to catch mid-tenure exits after the Annual Report date.
Execute the targeted SEBI/regulatory query per §8.4-A to ensure no active fraud/ED/CBI charge-sheets exist.
Step 5 — Verdict Synthesis:
Populate the §4 Internal Working Table with exact numbers, dates, file citations, and the new Confidence column.
Format the final investor-facing output through §5 and user.md.
8.4 Targeted retrieval per check — closing v1 gaps (new in v2)

These four sub-steps exist because a v1 live run (Cyient DLM, Sep 2026) showed that a generic web search can quietly stand in for a targeted registry query without anyone noticing, until someone asks "where exactly did that come from." Each one names the primary source and what to do if it can't be reached.

8.4-A — Check 1's regulatory-action sub-check

Query https://www.sebi.gov.in/enforcement/orders.html directly for the company name and, separately, the promoter/holding-company name (a subsidiary is sometimes named in an order against the parent).
Supplement with the generic press-scan query from §8.1 — but the SEBI archive query is the primary source; the press scan is corroboration, not a replacement.
If the SEBI portal cannot be reached (rate-limited, down, or the search tool returns nothing usable), fall back to the generic web search alone — but tag the resulting "no action found" as confidence: MEDIUM in §4's table, and say so in the investor-facing text per §5.

8.4-B — Check 2's pledge-trend sub-check

Pull the actual trailing-4-quarter series from Screener.in's shareholding-pattern view or the BSE Regulation 31 filing (shpSecA.aspx) — four distinct quarterly pledge-% data points, not one.
Only if that series is genuinely unobtainable, fall back to: latest-quarter pledge % plus the most recent promoter-group compliance filing (which confirms whether any new pledge was created, but says nothing about the trend of an existing one). Tag this fallback confidence: MEDIUM and disclose it per §5c.
Never silently present a fallback-sourced "stable" finding with the same confidence as an actual 4-quarter series — see Guardrail 9 in §6.

8.4-C — Check 5's 5-year data-completeness sub-step

Before accepting fewer than 5 years, try: (a) Screener's extended/10-year view, (b) the company's RHP or DRHP (pre-listing prospectus) for years before its IPO, (c) an older Annual Report not otherwise in scope for this run.
If a genuine 5-year series still cannot be assembled, proceed under §1a: evaluate on the years available, and state "(N of 5 years)" in the finding regardless of PASS/FAIL/ INCONCLUSIVE outcome.

8.4-D — Check 6's restatement sub-check

Search the Annual Report specifically for: "restatement", "prior period error", "Ind AS 8", and "restated" — and separately open the Auditor's Report to check for an Emphasis of Matter paragraph, which is where a material restatement is most likely to be flagged even if the word "restate" doesn't appear elsewhere.
Disambiguation: ESG/BRSR (sustainability) data restatements — e.g. a revised water- withdrawal or emissions figure for comparability — are not a financial restatement and do not trigger this check. Only a restatement of the financial statements themselves (P&L, Balance Sheet, Cash Flow, or their notes) counts. Note in the finding text which kind of restatement mentions (if any) were found and excluded, so a reader can see the distinction was actually checked, not assumed.
If neither the targeted search nor the Auditor's Report review surfaces anything, mark "no restatement found" confidence: HIGH — this sub-check, unlike 8.4-A, has a reasonably complete primary source (the Annual Report itself) that a targeted search can exhaustively cover.

8.4-E — Check 1's legal-fee-anomaly sub-check: industry-tiered revenue bands (new)

Why this replaced the flat 5x/2x rule. A single cross-industry, cross-size multiple of audit fees is not defensible: (1) no published benchmark exists for a "legal fee ÷ audit fee" ratio — searches of forensic-accounting and audit literature turn up fee-independence thresholds (e.g. non-audit fees > 15% of total auditor fees triggering a disclosure requirement) and general "compare to industry benchmark data" guidance, but never this specific ratio; (2) audit fees are a poor denominator on their own — Indian audit-fee research finds the correlation between fee and turnover "modest," consistent with a fixed-cost floor in statutory audit engagements, so the ratio is inflated for smaller/mid-cap companies and compressed for large caps regardless of actual legal intensity. What the audit/legal-benchmarking literature does support is legal & professional spend as a % of revenue, and that figure varies meaningfully by industry.

Data sources for the bands below:
- Acritas "Patterns in Legal Spend" report — legal department spend as % of revenue, reported by sector: Financial Services 0.89%, Pharma/Bioscience 0.48%, Government/Public sector 0.45%, Healthcare 0.42%, Insurance 0.41%, Manufacturing 0.28%, Retail/Wholesale 0.18%.
- ACC (Association of Corporate Counsel) Law Department Management Benchmarking Report — overall cross-industry average legal spend as % of revenue: 0.43%–0.63% depending on survey year (trending down); used as the default band for any sector not separately listed.
- Both surveys are global (predominantly US/UK-headquartered legal departments) — no India-specific, sector-wise legal-spend-to-revenue benchmark was found in available research. Treat the bands below as directional, not India-calibrated. To absorb that uncertainty (plus normal point-estimate noise in a single-year figure), each flag threshold is set at roughly 1.5x the sourced band's upper bound, not the raw band itself — this is a deliberate buffer, not the underlying benchmark number.

| Sector tier | NSE/BSE sector examples | Sourced band (legal & professional ÷ revenue) | Flag threshold (this check) | How the tier was set |
| :-- | :-- | :-: | :-: | :-- |
| 1 — High intensity | Banks, NBFCs, Insurance, Capital Markets/Broking ("Financial Services") | 0.6%–0.9% | **> 1.35%** | Direct — Acritas Financial Services (0.89%) + Insurance (0.41%) |
| 2 — Elevated | Pharmaceuticals, Healthcare, Biotechnology, IT/Technology | 0.35%–0.5% | **> 0.75%** | Pharma/Healthcare direct from Acritas; IT/Technology added by analogy — cited industry commentary places IT alongside Pharma as having "significantly higher... spend ratios" than low-margin sectors, but no exact IT figure was found, so treat the IT placement as a reasoned estimate, not a sourced number |
| 3 — Moderate (regulated) | Government/PSU, diversified conglomerates, Telecom, Oil & Gas, Power/Utilities | 0.3%–0.45% | **> 0.68%** | Govt/Public direct from Acritas (0.45%); Telecom/Oil & Gas/Power added by analogy (land acquisition, environmental clearance, and tariff-dispute litigation exposure) — an estimate, not a sourced figure for those three |
| 4 — Moderate-low | General Manufacturing, Industrials/Capital Goods, Auto & Auto Components, Construction/Infra, Metals & Mining, Chemicals | 0.2%–0.3% | **> 0.45%** | Direct — Acritas Manufacturing (0.28%) |
| 5 — Low intensity | FMCG, Consumer Durables, Retail/Wholesale Trading, Consumer Services | 0.15%–0.2% | **> 0.3%** | Direct — Acritas Retail/Wholesale (0.18%) |
| Unclassified / other | Any sector not listed above, or classification unavailable | 0.43%–0.63% (overall average) | **> 0.75%** | ACC overall average, used conservatively (same threshold as Tier 2) rather than assuming low intensity by default |

Sourcing steps:
1. Pull the company's sector/industry classification from Screener.in's company header (which mirrors NSE/BSE classification) — this is an objective, independently-verifiable tag, not an inference from AR narrative text. Map it to one of the five tiers above using the "NSE/BSE sector examples" column.
2. Pull revenue from the same statement, FY, and basis as the legal & professional charges figure (reuse the comparability guard already required for Check 3).
3. Compute `legal & professional charges ÷ revenue × 100` and compare to the mapped tier's flag threshold.
4. For the surge sub-check (b above), before treating a > 2x YoY increase as a fail trigger, check the Contingent Liabilities note, Board's Report, and a news scan for a disclosed one-off cause. Record whichever was found (or that none was found) in the finding text, mirroring the disambiguation discipline already required in §8.4-D.
5. If sector classification cannot be established, use the "Unclassified / other" row rather than leaving the check unresolved — do not silently default to the lowest-intensity tier, which would under-flag.
6. If India-specific, sector-wise legal-spend or audit-fee benchmarking data becomes available (e.g. an ICAI/NFRA study, or an India-focused legal-ops survey), this table should be recalibrated against it and the "directional, not India-calibrated" caveat above revisited.

8.4-F — Check 4's litigation-vs-routine contingent-liability split (new)

Why this replaced the flat 15%-of-net-worth rule. Schedule III to the Companies Act, 2013 already requires every company to disclose contingent liabilities broken into standard sub-categories, not as one lump figure: (a) claims against the company not acknowledged as debts, (b) guarantees given by/on behalf of the company, (c) letters of credit, (d) bills discounted, (e) disputed tax demands (income tax/GST/customs/excise/municipal), (f) contested claims for non-execution of orders. Of these, (b)/(c)/(d) scale with a company's ordinary trade-finance and banking activity and are not a governance signal on their own — a bank's letters of credit and guarantees, or an EPC contractor's performance/bid bonds, are routine features of how those businesses operate, and their aggregate size can legitimately run to several times net worth in an ordinary year for a bank/NBFC purely from forex, derivative, and guarantee/LC business. A flat ratio computed on the *total* figure conflates this routine volume with the genuinely risk-bearing categories (a)/(e)/(f), which is what causes the old flat rule to reject entire sectors (banking, NBFC, EPC/infrastructure) regardless of whether anything is actually wrong.

Litigation & claims exposure (the check's numerator) = (a) claims against the company not acknowledged as debts + (e) disputed tax demands + (f) contested claims for non-execution of orders + any guarantee under (b) given specifically on behalf of a promoter-group or related-party entity outside the ordinary course of business (cross-reference Check 3's rpt_sales_plus_purchases / unusual_affiliate_dealings — a related-party guarantee is exactly the kind of item Check 3 is also watching for, so flag it to both checks, not just one).

Routine, business-linked exposure (excluded from the numerator entirely) = ordinary-course guarantees and letters of credit under (b)/(c) + bills discounted under (d).

Flag threshold: litigation & claims exposure > **20% of net worth**. This is a single, non-industry-tiered threshold, deliberately conservative rather than further refined by sector — available benchmarking data (an aggregate contingent-liability/equity study) gives a market-wide median of roughly 11% for the *total*, unsplit contingent-liability figure across companies that disclose one; a litigation-only figure, after stripping out routine guarantees/LCs, should ordinarily run well below that market-wide total-basis median for most industries. No benchmark specifically for a litigation-only ratio, by industry, was found, so this check intentionally does not attempt an industry-tiered table the way §8.4-E and §8.4-G do — the split itself (not a further multiplier) is what does the real work of fixing the false-positive problem, and a single conservative threshold on the already-narrowed figure is more defensible than an industry table built on weak analogy.

Sourcing steps:
1. Locate the Contingent Liabilities note in the Annual Report and extract every disclosed sub-category separately — do not accept a single total figure if any breakdown is given.
2. Sum the litigation/claims sub-categories per the definition above for the numerator; sum the routine sub-categories separately (retained for reference/citation, but excluded from the ratio).
3. Cross-check any related-party guarantee found against Check 3's RPT data.
4. If the Annual Report discloses only a single lump-sum contingent liabilities figure with no sub-category breakdown (uncommon under Schedule III, but possible for an abbreviated or non-compliant disclosure): if that lump total is already ≤ 5% of net worth, treat it as immaterial and PASS without needing the breakdown (the split cannot change a PASS on a number that small); otherwise mark Check 4 **INCONCLUSIVE — contingent liabilities disclosed as a single total, litigation/routine split not available** rather than guessing which portion is which.
5. If India-specific litigation-only contingent-liability benchmarking data becomes available by sector, this single threshold should be revisited and potentially replaced with an industry-tiered table, mirroring §8.4-E's structure.

8.4-G — Check 5's working-capital-cycle tiering (new)

Why this replaced the flat 0.80 / ≥3-of-5-years rule. Available commentary on CFO/PAT quality-of-earnings analysis is explicit that comparing an EPC/infrastructure firm's cash-conversion ratio to an FMCG company's "as if they were equivalent is analytical laziness" — a capital-intensive or project-accounting business structurally converts profit to cash on a different timeline than an asset-light services business, for reasons that have nothing to do with earnings quality: percentage-of-completion revenue recognition (real estate, EPC), long receivable/milestone cycles (construction, running 90–120+ days), and heavy non-cash depreciation add-backs (asset-heavy manufacturing, telecom, utilities) all shift the ratio in normal, explainable ways. The same commentary gives a concrete anchor: an EPC/infrastructure firm can legitimately sit near **0.7x** CFO/PAT, while a cumulative ratio **below 0.5x** is a hard stop regardless of sector ("you should not proceed to valuation").

Working-capital-cycle tiers:

| Tier | Sector examples | CFO/PAT flag threshold (below this = FAIL) | Negative-CFO-years FAIL trigger | Rationale |
| :-- | :-- | :-: | :-: | :-- |
| Long-cycle / project accounting | EPC, Construction, Infrastructure, Real Estate/Realty, large turnkey Capital Goods contracts | **< 0.65** | **≥ 4 of 5 years** | Set below the ~0.7x cited as a legitimate normal level for this tier, leaving headroom for ordinary single-year noise while still catching real deterioration; the wider negative-years allowance reflects genuinely volatile multi-year project cash cycles |
| Moderate-cycle | General Manufacturing, Auto & Auto Components, Industrials, Chemicals, Metals & Mining | **< 0.75** | **≥ 3 of 5 years** (unchanged default) | Between the two extremes — some working-capital drag, no project-accounting timing mismatch |
| Short-cycle / asset-light | IT/Technology Services, FMCG, Pharma, Healthcare, Consumer Services | **< 0.85** | **≥ 3 of 5 years** (unchanged default) | Tightened from the old flat 0.80 — a shortfall is more suspicious in a business with minimal structural working-capital drag |
| Lending institutions | Banks, NBFCs, Insurance | **Not applicable — see below** | Not applicable | CFO is dominated by loan-book/deposit movement, not P&L-linked working capital; the ratio is not meaningful in either direction for this tier |
| Unclassified / other | Any sector not listed above, or classification unavailable | **< 0.75** (Moderate-cycle default) | **≥ 3 of 5 years** | Conservative default, mirroring §8.4-E's "never silently default to the most lenient tier" rule |

Global backstops, applied before and regardless of tier: cumulative PAT ≤ 0 → FAIL; cumulative CFO ÷ PAT < 0.50 → FAIL. Neither is loosened by any tier — a long working-capital cycle explains a ratio of 0.65–0.79, not one below 0.50.

Lending institutions: do not force a CFO/PAT threshold onto a bank, NBFC, or insurer. Mark Check 5 **INCONCLUSIVE — CFO/PAT not a meaningful metric for lending institutions**, and say so explicitly in both the internal table and the investor-facing write-up, rather than silently passing or silently omitting the check. This is a genuine "not applicable" case, not a data-availability gap — the years-of-CFO-data may be fully available and still not answer the question this check is trying to answer for this company type.

Sourcing steps:
1. Pull the company's sector/industry classification from Screener.in's company header (same source as §8.4-E), and map it to one of the four working-capital-cycle tiers above (or Unclassified/other).
2. If the company is a bank, NBFC, or insurer (by the same classification), resolve Check 5 as INCONCLUSIVE per the note above rather than computing a ratio.
3. Otherwise compute cumulative CFO ÷ PAT and the negative-CFO-year count exactly as before, and compare each against the mapped tier's thresholds (or the tier-specific and global-backstop thresholds together, whichever fires first).
4. If sector classification cannot be established for a non-lending company, use the Moderate-cycle thresholds as the conservative default (row above), not the loosest (long-cycle) tier.

8.4-H — Check 5's use-of-funds verification (new)

Why this exists. §8.4-G's tiering already accepts that a long-cycle business converts profit to cash more slowly. But tiering alone is a blunt instrument — it widens the acceptable band, it doesn't distinguish, within a company that still breaches even the widened band, between "this cash is funding real growth" and "this cash has genuinely gone missing." A live Phase 1 run on GRSE (Sep 2026) hit exactly this: a cumulative CFO/PAT ratio of 0.055 — a wide breach even of the long-cycle tier's 0.65 floor and the 0.50 hard floor — that a follow-up forensic trace showed was overwhelmingly working-capital absorption behind a revenue base that nearly quadrupled over the same five years, not cash disappearing. Rejecting a company outright on a ratio without ever asking where the shortfall went treats a symptom as if it were always the disease. This sub-check gives that question a defined, sourced, and gameable-resistant answer.

The three conditions, in exact terms:

(a) Growth is real. `revenue_last_5y[-1] / revenue_last_5y[0] >= 1.5` — the same 5-year revenue series already required for context on this company; a new field, but pulled from the same Annual Reports / Screener.in multi-year view already in scope for this run. This guards against a company claiming "we're investing in growth" when revenue is flat or declining and the working-capital buildup is really just deteriorating receivables/inventory quality.

(b) The shortfall is a working-capital story. `abs(cumulative_working_capital_change_5y) / abs(cumulative_pat_5y - cumulative_cfo_5y) >= 0.60`. `cumulative_working_capital_change_5y` is the Cash Flow Statement's own "Changes in working capital" (or equivalently-labelled) reconciling subtotal, summed across the same five years — every Ind AS 7 indirect-method cash flow statement in India presents this as a single named line between "Operating profit before working capital changes" and "Cash generated from operations," so this is a direct extraction, not a synthetic construct built by summing individual note-level balance-sheet movements (which are noisier and less consistently disclosed). This guards against a shortfall that's actually driven by something other than working capital — e.g. large one-off provisions, unusual finance-cost timing, or items that have nothing to do with "the business is growing."

(c) Not hoarding. Let `cushion_pct_first = liquid_cushion_first_year / revenue_last_5y[0]` and `cushion_pct_last = liquid_cushion_last_year / revenue_last_5y[-1]`, where liquid cushion = cash & cash equivalents + other bank balances (incl. fixed deposits) + current investments, read off the Balance Sheet for the first and last year of the same 5-year window. Condition holds if `cushion_pct_last <= cushion_pct_first * 1.10` (a 10% tolerance band for ordinary year-to-year noise). This guards against the opposite failure mode from (a)/(b) alone: a company could show real revenue growth and a working-capital-dominated shortfall while ALSO quietly letting cash pile up beyond what growth or advances require — (c) checks that the liquid cushion isn't growing faster than the business itself, which is the actual signature of hoarding rather than deploying.

Sourcing steps:
1. Pull `revenue_last_5y` from the same multi-year source already used for `cfo_last_5y`/`pat_last_5y` (Screener.in 5-year view or the Annual Reports directly), same FY alignment and basis.
2. Pull `cumulative_working_capital_change_5y` directly from each year's Cash Flow Statement — do not derive it by summing individual balance-sheet note movements; use the Statement's own named subtotal, summed across the five years.
3. Pull `liquid_cushion_first_year` and `liquid_cushion_last_year` from the Balance Sheet (Cash & cash equivalents + Other bank balances + Current investments notes) for the first and last year of the window only — the two endpoints are sufficient for the trend test, a full 5-year series is not required for this sub-check.
4. If any of the three fields cannot be sourced, do not guess or interpolate — the verification cannot run, and per the golden rule the disqualifying trigger stays FAIL rather than being silently upgraded.
5. If all three fields are available, evaluate (a), (b), (c) in order and record which passed/failed in the finding text regardless of the outcome — a reader must be able to see the verification was actually attempted, not merely asserted.
6. This sub-check runs once per Phase 1 evaluation (not once per disqualifying trigger) — if multiple triggers fire (e.g. both the ratio and the negative-years count), one verification result governs all of them, since they are different symptoms of the same underlying cash-timing question.