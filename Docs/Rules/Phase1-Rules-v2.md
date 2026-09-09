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
0. Core principle

Phase 1's job is capital preservation, not opportunity-finding. It answers one question: is this company honest and stable enough to be worth studying? Six checks stand at the door — the same six questions as Section A of the question set. If a stock fails even one check, it is REJECTED — stop immediately. Do not build a valuation, do not look at the price chart, do not weigh the growth story against a red flag. The moment one check fails, the analysis is over and the verdict is REJECT.

Treat this as strictly pass/fail per check, never a score out of six.

1. Inputs (what to gather before deciding)

For the stock under review, collect these data points. Cite the source and period for each. The "Section A Q#" column shows which question set item each check answers. The "Retrieval requirement" column is new in v2 — it names the specific query or registry each field needs, not just a preferred source, per §8.4.

#	Section A Q#	Check	Data to pull	Preferred source	Retrieval requirement (v2)
1	Q1	Auditor & regulator	Auditor resignation (last 3 yrs)? Audit opinion type? Active/5-yr fraud probe (SEBI/ED/CBI/SFIO)? Legal vs. audit fee anomaly?	Annual Report → Independent Auditors' Report → "Opinion", Notes → "Auditor remuneration" & "Legal charges"; Google name + auditor resigns, + SEBI	Regulatory-action sub-check MUST be run against §8.4-A (named registry + query string), not a generic web search alone
2	Q2	Promoter pledge	Promoter pledge % (latest); pledge trend over last ~4 quarters; is it a govt PSU or zero-promoter (professionally managed)?	Screener.in → Shareholding Pattern	Trend MUST be the actual trailing-4-quarter series per §8.4-B; a single latest figure plus a "no new pledge" filing is a flagged fallback only, per §1a
3	Q3	Related-party leakage	RPT (sales + purchases) as % of revenue; any unusual affiliate loans/deals	Annual Report → notes → "Related Party Transactions"	—
4	Q4	Contingent liabilities	Total contingent liabilities; net worth (total equity); material litigation disclosed	Annual Report → "Contingent Liabilities" note; balance sheet	—
5	Q5	Cash conversion	5-yr cumulative CFO (cash from operations); 5-yr cumulative PAT (profit after tax); count of years (of 5) with negative CFO	Cash Flow statement vs P&L, 5 years (Screener.in or Annual Reports)	If fewer than 5 years of source documents are available, actively attempt to close the gap per §8.4-C (Screener 5-yr view, RHP/DRHP pre-listing financials, or an older Annual Report) before falling back to a partial window; §1a governs disclosure either way
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
Legal vs. Audit fee anomaly: Legal & professional charges exceed statutory audit fees by > 5x, or show an unexplained > 2x surge in a single year (potential signal of hidden litigation/regulatory defense).
PASS only if all conditions are clear (clean opinion, no mid-tenure resignation, no fraud-related probes/sanctions, and normal legal/audit fee ratios).

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

FAIL if net worth ≤ 0 (broken balance sheet), OR contingent liabilities > 15% of net worth.
PASS if contingent liabilities ≤ 15% of net worth.
Formula: Contingent Liabilities ÷ Net Worth × 100.

Check 5 — Show Me the Cash (Section A Q5, two independent triggers — fail either one)

FAIL if: negative operating cash flow in ≥ 3 of the last 5 years, OR cumulative PAT ≤ 0, OR cumulative CFO ÷ PAT < 0.80.
PASS if CFO ÷ PAT ≥ 0.80 (ideal > 1.0) and negative-CFO years ≤ 2.
v2: if evaluated on fewer than 5 years (see §1a), the finding text must state "(based on N of 5 years)" regardless of whether the result is FAIL or INCONCLUSIVE.

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
Never soften a Fail into a "watch item." A breached threshold is a Fail and a REJECT.
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

6. Guardrails (non-negotiable)
One fail = reject. No averaging, no "5 of 6 is good enough," no overriding a red flag with a growth story.
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