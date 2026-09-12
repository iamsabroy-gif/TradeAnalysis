# Phase 1 Gatekeeper Rules

*Operating instructions for running the "Trust Check" governance screen on a stock and
returning the verdict. Read this file top to bottom before analysing. It defines the data
to gather, the exact pass/fail logic, the decision
rule, and how the result must be written
up for the investor. This is a **red-flag elimination filter**, not a buy signal — the only
outputs are REJECT, CLEARED TO PHASE 2, or HOLD — INCONCLUSIVE.*

**Source checklist:** this screen operationalises **Section A — Red Flags & Governance,
Q1–Q6** of this project's own
`Stock - Analysis - Question - Set.md`. Every check below maps
1:1 to one of those six questions. Debt and leverage (Section F of the question set) is
deliberately **not** part of this filter — that belongs to Phase 2 (Core Health). Keep that
boundary.

**Communication rules:** every investor-facing verdict produced from this file must be
written through `user.md` — plain English first, jargon explained the moment it appears,
numbers translated into relatable facts, the Pass/Fail translation table, a "so what does
this mean for you" line per section, and the fixed disclaimer from `user.md` §9. §5 of this
file shows exactly how that wrapping works.

---

## 0. Core principle

Phase 1's job is **capital preservation**, not opportunity-finding. It answers one question:
*is this company honest and stable enough to be worth studying?* Six checks stand at
the door — the same six questions as Section A of the question set. **If a stock fails even one
check, it is REJECTED — stop immediately.** Do not build a valuation, do not look at
the price chart, do not weigh the growth story against a red flag. The moment one check fails,
the analysis is over and the verdict is REJECT.

Treat this as strictly **pass/fail per check**, never a score out of six.

---

## 1. Inputs (what to gather before deciding)

For the stock under review, collect these data points. Cite the source and period for each.
The "Section A Q#" column shows which question set item each check answers.

| # | Section A Q# | Check | Data to pull | Preferred source |
| :-: | :-: | :-- | :-- | :-- |
| 1 | Q1 | Auditor & regulator | Auditor resignation (last 3 yrs)? Audit opinion type? Active/5-yr fraud probe (SEBI/ED/CBI/SFIO)? Legal vs. audit fee anomaly? | Annual Report → Independent Auditors' Report → "Opinion", Notes → "Auditor remuneration" & "Legal charges"; Google `name + auditor resigns`, `+ SEBI` |
| 2 | Q2 | Promoter pledge | Promoter pledge % (latest); pledge trend over last ~4 quarters; is it a govt PSU or zero-promoter (professionally managed)? | Screener.in → Shareholding Pattern |
| 3 | Q3 | Related-party leakage | RPT (sales + purchases) as % of revenue; any unusual affiliate loans/deals | Annual Report → notes → "Related Party Transactions" |
| 4 | Q4 | Contingent liabilities | Total contingent liabilities; net worth (total equity); material litigation disclosed | Annual Report → "Contingent Liabilities" note; balance sheet |
| 5 | Q5 | Cash conversion | 5-yr cumulative CFO (cash from operations); 5-yr cumulative PAT (profit after tax); count of years (of 5) with negative CFO | Cash Flow statement vs P&L, 5 years (Screener.in or Annual Reports) |
| 6 | Q6 | Executive stability | Number of CFO changes (last 3 yrs); any restatement of past accounts | Board's Report (KMP changes); Google `name CFO resigns` |

**If a required data point is unavailable or unverifiable, do not guess.** Mark that check
**INCONCLUSIVE — data not available**, and treat it as a hold (see §3): the stock cannot be
CLEARED while any check is inconclusive, but do not fabricate a Fail either. State exactly
what is missing and where it would normally be found.

**Track record shorter than the lookback window:** If the company has been listed or
reporting for less than the required window (3 years for Checks 1 & 6, 5 years for Check 5),
do not FAIL or PASS on partial data. Evaluate over whatever full years are
actually available and mark the check **INCONCLUSIVE — insufficient track record (only N years available)** rather than PASS or FAIL. Exception: if even one available year shows a
disqualifying event (e.g. a qualified audit opinion, a CFO exit tied to a restatement),
that still triggers an immediate FAIL — a short history can still fail, it just cannot
"pass" prematurely.

---

## 2. Pass / Fail logic (exact thresholds)

Apply each rule literally. "Safe" = Pass; any listed danger condition = Fail.

**Check 1 — Auditor & Regulator Integrity** *(Section A Q1)*
- FAIL if **any** of the following apply:
  1. **Auditor resignation:** Statutory auditor resigned mid-tenure within the last 3 years.
  2. **Audit opinion:** Most recent audit report contains a "qualified", "adverse", or "disclaimer of opinion".
  3. **Regulatory / Criminal action:** Active or past 5-year investigation, charge-sheet, probe, or material sanction/debarment by SEBI, RBI, SFIO, ED, CBI, or EOW involving fraud, siphoning, market manipulation, or accounting irregularities (excludes routine, immaterial secretarial/procedural fines).
  4. **Legal vs. Audit fee anomaly:** Legal & professional charges exceed statutory audit fees by > 5x, or show an unexplained > 2x surge in a single year (potential signal of hidden litigation/regulatory defense).
- PASS only if all conditions are clear (clean opinion, no mid-tenure resignation, no fraud-related probes/sanctions, and normal legal/audit fee ratios).

**Check 2 — Promoter Pledge & Encumbrance** *(Section A Q2)*
- **Auto-PASS Exceptions:**
  - **Government-owned PSUs:** Defined as government (central + state, direct or indirect)
    shareholding **≥ 51%** per the latest shareholding pattern (e.g. GRSE, HAL, BEL, NTPC) —
    government does not pledge; this check is N/A. A partially-disinvested former PSU below
    this 51% threshold does **not** qualify for the auto-pass and must be evaluated under the
    normal thresholds below like any other company.
  - **Professionally managed companies:** Zero (0%) promoter holding (e.g. ITC, L&T, ICICI Bank) — no promoter shares exist to pledge.
- **FAIL if either of the following applies:**
  1. **Absolute threshold:** Latest pledged/encumbered shares **> 10%** of total promoter holding.
  2. **Rising trend:** Pledged % has shown an upward trend over the last 2–4 quarters (or an unexplained single-quarter spike of > 2%), signaling promoter liquidity stress.
- **PASS only if:** Pledged shares are **≤ 10%** of promoter holding **AND** stable or declining over the last 4 quarters (ideal is 0%).
- **Low-base guard:** If promoter holding is **below 5%** of total company shares outstanding,
  do not apply the >10%-of-promoter-holding threshold in isolation — a tiny promoter base can
  make a small pledge look alarming in percentage terms. Also compute pledged shares as **% of
  total company shares outstanding**. FAIL only if *either* (a) pledged shares exceed 10% of
  promoter holding **and** pledged shares exceed 0.5% of total company shares, **or** (b) the
  absolute value of pledged shares is material relative to the promoter's other disclosed
  liquidity. Otherwise mark PASS with a note: "pledge % elevated due to small promoter base,
  not treated as a red flag."

**Check 3 — Related-Party "Leakage"** *(Section A Q3)*
- FAIL if: RPT (sales + purchases) **> 5%** of revenue (excluding ordinary, heavily
  regulated dealings), **OR** there are large/unexplained loans or deals with promoter-owned
  unlisted affiliates.
- PASS if RPT ≤ 5% and no suspicious affiliate transactions.

**Check 4 — Contingent Liabilities** *(Section A Q4)*
- FAIL if net worth ≤ 0 (broken balance sheet), **OR** contingent liabilities exceed the
  **Industry Sector Cap** (below):
  - **Standard Sectors** (Pharma, Software, FMCG, etc.): **> 15%** of net worth.
  - **High-Exposure Sectors** (Retail, Food, Construction, Real Estate): **> 50%** of net worth.
- PASS if contingent liabilities are within the sector cap.
- Formula: `Contingent Liabilities ÷ Net Worth × 100`.

**Check 5 — Show Me the Cash** *(Section A Q5, two independent triggers — fail either one)*
- FAIL if: negative operating cash flow in **≥ 3** of the last 5 years, **OR** cumulative PAT
  ≤ 0, **OR** cumulative `CFO ÷ PAT < 0.80`.
- PASS if `CFO ÷ PAT ≥ 0.80` (ideal > 1.0) **and** negative-CFO years ≤ 2.

**Check 6 — Executive Stability** *(Section A Q6)*
- FAIL if: **> 1** CFO change in the last 3 years, **OR** any retroactive restatement of
  past accounts.
- PASS if CFO changes ≤ 1 and no restatement.

---

## 3. Decision rule (the gate)

1. Evaluate all six checks (PSUs and zero-promoter companies auto-pass Check 2).
2. **If any check = FAIL $\to$ verdict is REJECT.** Report the failing check(s) and stop. Do not
   proceed to any further analysis.
3. **If any check = INCONCLUSIVE (and none failed) $\to$ verdict is HOLD — INCONCLUSIVE.** List
   what data is missing to close it.
4. **If all six checks = PASS $\to$ verdict is CLEARED TO PHASE 2.** State explicitly that this
   means *only* "honest enough to study," **not** "buy." A CLEARED verdict is a passed
   background check, nothing more.

Order of reporting: it is fine to short-circuit — once a Fail is found, the stock is
rejected regardless of the other checks — but for a full record, still report the status of
every check that was actually assessed.

---

## 4. Internal working table (analyst view — precise, technical)

This is the raw evidence table. It stays exact and numeric — the plain-English wrapping
happens in §5, on top of this table, never instead of it.

```
# Phase 1 — <Company Name> (<TICKER>)
**As of:** <date data pulled>   **Type:** <Private promoter / Govt PSU / Professionally managed (0% promoter)>

## VERDICT: <REJECT | CLEARED TO PHASE 2 | HOLD — INCONCLUSIVE>
<one line: e.g. "Failed Check 2 (promoter pledge 34%, rising) — stop here.">

| # | Check | Finding (with number) | Source | Pass/Fail |
| :-: | :-- | :-- | :-- | :-: |
| 1 | Auditor & regulator | | | |
| 2 | Promoter pledge | | | |
| 3 | Related-party txns | | | |
| 4 | Contingent liabilities | | | |
| 5 | Cash conversion | | | |
| 6 | CFO stability | | | |

## Why the verdict
- <for each FAIL: the number, the threshold it breached, and the plain-language risk>
- <for a CLEARED verdict: confirm all six passed and restate the thresholds cleared>

## What the data does NOT let us conclude
- <any check marked inconclusive, and exactly which document would close it>
```

Formatting rules for this internal table:
- Every quantitative finding must be **sourced** (document + period, e.g. "FY24 AR, Note 34"
  or "Screener, as of DD-MMM-YYYY"). No unsourced numbers.
- Show the **actual number against the threshold** for each check ("pledge 12% vs 10% limit"),
  not just "Fail".
- Separate **what the data shows** from **what it implies**.
- Never soften a Fail into a "watch item." A breached threshold is a Fail and a REJECT.

---

## 5. Investor-facing output (must run through `user.md`)

The internal table in §4 is the analyst's working evidence. **It is never shown to the
investor on its own.** Every time this screen is actually run against a real stock, the final response
must be re-expressed through `user.md`'s rules before it is sent:

- Open with a one-to-two sentence plain-English verdict in storytelling form — the investor
  should know the answer before any numbers appear.
- Explain every technical term (promoter pledge, contingent liabilities, CFO, PAT, etc.) in
  plain language the moment it is first used — analogy first, label second (`user.md` §2, §10).
- Translate every number into a relatable fact, not a bare figure.
- Use the exact Pass/Fail translation table from `user.md` §4:
  - `CLEARED TO PHASE 2` → "Passed the honesty check — safe to look deeper"
  - `REJECT (Phase 1)` → "Failed the honesty check — stop here, do not invest"
- Close every section with a "so what does this mean for me" line.
- Keep paragraphs short (3–4 lines) for mobile reading.
- End with the disclaimer, verbatim, from `user.md` §9.
- Never imply a guaranteed return anywhere in the write-up (this screen makes no return forecast at all).
- **CLEARED TO PHASE 2 means "safe enough to study further" — it is never a buy signal.**
  Say this explicitly every time a CLEARED verdict is delivered, per `user.md`'s own
  translation table.

### 5a. Worked example — REJECT verdict, translated

> **The short answer:** This company failed our honesty check — one of its promoters has
> pledged a large and rising share of their stock as loan collateral. We stop here and do
> not go further.
>
> Here's what that means. When a promoter (the founder or controlling owner) borrows money
> against their own shares in the company, it's called a **share pledge**. Think of it like
> someone taking a personal loan by putting up their house as collateral — if things go wrong,
> the lender can seize those shares and sell them, flooding the market and hurting
> every other shareholder, including you.
>
> In this case, the promoter has pledged **34% of their holding, and that number has been
> rising every quarter** (Screener.in, shareholding pattern, as of Jun-2026) — well above
> the 10% level we treat as a warning line.
>
> **So what does this mean for you?** This isn't a business-quality problem, it's a trust
> problem — the framework caught it before you put any money in. That's the system working
> as intended, not a loss. We simply move on to the next candidate.
>
> *This is educational analysis only, not personalised investment advice. Please consult a
> SEBI-registered investment adviser before making any investment decisions.*

### 5b. Worked example — CLEARED verdict, translated

> **The short answer:** This company passed every honesty check we ran. That doesn't mean
> "buy" — it means it's trustworthy enough to be worth studying further.
>
> We checked things like: has the company's auditor ever walked away mid-job, is the
> promoter (founder/owner) borrowing against their own shares, is profit actually turning
> into real cash in the bank rather than staying on paper, and has the finance chief
> (**CFO** — the senior executive in charge of the company's money) been stable rather than
> changing every year. All six came back clean.
>
> For example, out of the profit the company reported over the last five years, **more than
> 100% of it actually showed up as cash in the bank** — a sign the earnings are real, not
> just accounting entries (5-yr Annual Report cash flow statements vs P&L).
>
> **So what does this mean for you?** Think of this like a background check before hiring a
> contractor — passing it means they're honest and stable enough to talk to, not that you've
> already agreed to hire them. The next step, Phase 2, checks whether this is
> actually a *good* business — decent profits, healthy margins, manageable debt — before
> price ever enters the conversation.
>
> *This is educational analysis only, not personalised investment advice. Please consult a
> SEBI-registered investment adviser before making any investment decisions.*

---

## 6. Guardrails (non-negotiable)

1. **One fail = reject.** No averaging, no "5 of 6 is good enough," no overriding a red flag
   with a growth story.
2. **No return promises.** Never state or imply a target return, "guaranteed" outcome, or
   profit figure — this screen makes no forecast at all.
3. **Flag missing data, don't estimate.** An unverifiable input is INCONCLUSIVE, never a
   confident guess.
4. **Passing ≠ buy.** CLEARED means eligible for Phase 2 study only. Say so every time, in
   the investor's own translation table language.
5. **PSU exception is narrow.** It applies to Check 2 (pledge) only — a government PSU still
   faces all five other checks.
6. **Educational only.** Close every verdict with the SEBI-registered-adviser reminder,
   verbatim from `user.md` §9.
7. **Communication is mandatory, not optional.** An investor-facing Phase 1 response that
   skips the `user.md` plain-English wrapping (§5 above) is incomplete, even if the
   underlying six-check analysis is correct.
8. **Scope.** This file covers Phase 1 only. Debt/leverage (Section F) and business-quality
   checks belong to Phase 2, which is out of scope here.

---

## 7. Definition of done

- [ ] All six checks assessed (or explicitly marked inconclusive with the missing source named).
- [ ] Each check shows the actual figure against its threshold, with a citation.
- [ ] A single clear verdict: REJECT / CLEARED TO PHASE 2 / HOLD — INCONCLUSIVE.
- [ ] Any Fail names the specific check and breached threshold.
- [ ] The investor-facing write-up follows `user.md` — plain-English lead, terms explained,
      numbers translated, Pass/Fail table used, "so what does this mean for you" per section.
- [ ] No specific return is promised or implied; the SEBI disclaimer is present verbatim.

---

## 8. Data Retrieval & Execution Solution (Sources, Links & Approach)

*This section defines the automated/standard retrieval pipeline for running Phase 1 on any
Indian listed stock given just the company name or stock ticker.*

### 8.1 Common URLs & Repositories

| Repository / Platform | URL Pattern / Query | Primary Purpose in Phase 1 |
| :-- | :-- | :-- |
| **Screener.in (Primary Hub)** | `https://www.screener.in/company/{TICKER}/consolidated/`<br>*(or `/company/{TICKER}/` for standalone)* | Multi-year CFO & PAT tables (Check 5), quarterly promoter pledge trend (Check 2), and direct PDF links to Annual Reports. |
| **BSE Corporate Announcements** | `https://www.bseindia.com/corporates/ann.html`<br>*(Filter: Category = "Company Update / Resignation")* | Immediate disclosures on mid-tenure auditor resignations (Check 1) and CFO departures (Check 6) post-dating the latest Annual Report. |
| **BSE Shareholding Pattern (Cross-verification)** | `https://www.bseindia.com/corporates/shpSecA.aspx?scripcd={BSE_SCRIP_CODE}` | Official Regulation 31 filing for promoter pledge verification (Check 2). |
| **NSE Corporate Announcements (Alternative)** | `https://www.nseindia.com/companies-listing/corporate-filings-announcements`<br>*(Query by `{TICKER}`)* | Backup exchange feed for corporate announcements and material events. |
| **SEBI Enforcement Orders Archive** | `https://www.sebi.gov.in/enforcement/orders.html` | Searchable repository for official adjudication orders, debarments, or active fraud probes (Check 1). |
| **Targeted Regulatory Press Scan** | Query syntax:<br>`"{Company Name}" AND (SEBI OR "Enforcement Directorate" OR SFIO OR CBI) AND (fraud OR investigation OR debarred OR "show cause")` | Web scan to detect ongoing raids, charge-sheets, or criminal probes not yet formally closed or reported in company filings. |

---

### 8.2 What Files to Pull from Each Link

| Link / Source | File / Document to Pull | Storage / Working Name | Details to Extract from File |
| :-- | :-- | :-- | :-- |
| **Screener.in** → "Documents" section | Annual Report PDFs for the last 5 financial years | `{TICKER}_AR_FY{YYYY}.pdf` (e.g. `TATAMOTORS_AR_FY24.pdf`) | • **Independent Auditor’s Report:** Opinion type ("unqualified/clean" vs "qualified/adverse").<br>• **Notes to Accounts (Other Expenses):** "Legal and professional charges".<br>• **Notes to Accounts (Auditor Remuneration):** Statutory audit fee.<br>• **Notes to Accounts (Related Parties):** Total RPT sales/purchases, affiliate loans.<br>• **Notes to Accounts (Contingent Liabilities):** Total contingent claims.<br>• **Balance Sheet:** Net worth (Shareholders' funds).<br>• **Board’s Report:** CFO/KMP appointments and resignations over 3 years. |
| **Screener.in** → Main page HTML | Tabular data rendered on company page | Raw extracted tables (JSON/Text) | • 5-year Cash Flow statement (`Cash from Operating Activity`).<br>• 5-year Profit & Loss statement (`Net Profit`).<br>• Trailing 4-to-8 quarters `Promoter holding %` and `Pledged %`. |
| **BSE / NSE Announcements** | Regulation 30 corporate disclosure letters (PDF/Text) | `{TICKER}_Reg30_{EventDate}.pdf` | • Formal resignation letters of statutory auditors (reason given for resignation).<br>• Resignation/replacement letters for CFOs. |
| **SEBI Portal / Legal Archive** | Regulatory orders / Show-cause rulings (PDF/Web page) | `{TICKER}_SEBI_Order_{Date}.pdf` | • Relevant operative paragraphs finding management guilty of fraud, diversion of funds, or market manipulation. |

---

### 8.3 Step-by-Step Extraction Approach

When initiating a Phase 1 review with just `{TICKER}`:

1. **Step 1 — Rapid Screen via Screener.in:**
   - Fetch the Screener company page.
   - Extract the 5-year CFO and PAT numbers. Immediately compute the 5-year cumulative `CFO ÷ PAT` ratio and count negative-CFO years (**Check 5**).
   - Extract the trailing 4 quarters of promoter shareholding and pledge percentage. Verify if pledge is ≤ 10% and not trending upward (**Check 2**).

2. **Step 2 — Annual Report PDF Acquisition:**
   - From the "Documents" section of the Screener page, download the latest Annual Report PDF (`{TICKER}_AR_latest.pdf`) and prior reports if required.

3. **Step 3 — Deep Audited Notes Extraction:**
   - In the latest Annual Report:
     - Search for *"Independent Auditor's Report"* → check the **Opinion** paragraph (**Check 1**).
     - Search for *"Auditor's remuneration"* and *"Legal and professional"* under Notes to Financial Statements → calculate `Legal Fees ÷ Audit Fees` (**Check 1**).
     - Search for *"Related Party"* note → sum sales + purchases, calculate as % of Revenue (**Check 3**).
     - Search for *"Contingent Liabilities"* note and *"Balance Sheet"* → calculate `Contingent Liabilities ÷ Net Worth × 100` (**Check 4**).
     - Search *"Board's Report"* / *"Corporate Governance Report"* for KMP changes → verify CFO tenure stability over the last 3 years (**Check 6**).

4. **Step 4 — Watchdog & Corporate Announcement Verification:**
   - Query BSE/NSE corporate announcements for the trailing 12 months for keyword `"Auditor"` or `"CFO"` to catch mid-tenure exits after the Annual Report date.
   - Execute the targeted SEBI/regulatory query to ensure no active fraud/ED/CBI charge-sheets exist.

5. **Step 5 — Verdict Synthesis:**
   - Populate the §4 Internal Working Table with exact numbers, dates, and file citations.
   - Format the final investor-facing output through §5 and `user.md`.
