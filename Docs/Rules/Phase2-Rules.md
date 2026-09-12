# Phase 2 Gatekeeper Rules — The Business Quality Check

*Operating instructions for judging whether a company that has already passed Phase 1 is
actually a **good business**, and returning the verdict. Read this file top to bottom before
analysing. It defines the data to gather, the exact pass/concern/fail logic, the decision
rule, and how the result must be written up for the investor. Phase 1 asked "is this company
honest?" Phase 2 asks "is this company any good?" — **price is never part of this phase.***

**Entry condition:** a stock may only enter Phase 2 with a Phase 1 verdict of
`CLEARED TO PHASE 2`. A `REJECT` or `HOLD — INCONCLUSIVE` at Phase 1 does not enter here.
Never re-litigate a Phase 1 check in this file.

**Source checklist:** this screen operationalises **Section E (Q18–Q20)**, **Section F
(Q22–Q28)**, and **Section G (Q29–Q31)** of this project's own
`Stock - Analysis - Question - Set.md`. Every check below maps 1:1 to one or more of those
questions. Two deliberate exclusions, both belonging to Phase 3:
- **Q21** (valuation vs. peers — P/E, P/B, EV/EBITDA) is a *price* question, not a quality
  question. It is **not** in Phase 2.
- **Q40** (Section I — return-requirement analysis) is likewise Phase 3.

Sections B, C, D, H and J of the question set are narrative and produce no pass/fail
verdict; they are handled separately (see §2.6). Keep these boundaries.

**Communication rules:** every investor-facing verdict produced from this file must be
written through `user.md` — plain English first, jargon explained the moment it appears,
numbers translated into relatable facts, the Pass/Fail translation table, a "so what does
this mean for you" line per section, and the fixed disclaimer from `user.md` §9. §5 of this
file shows exactly how that wrapping works.

---

## 0. Core principle

Phase 2's job is **quality discrimination**, not capital preservation — Phase 1 already did
the protecting. It answers one question: *does this business earn a good return on the money
put into it, and can it keep doing so?*

Twelve checks, in four groups: what the business **earns** (returns and margins), what it
**owes** (leverage and refinancing), how it **collects** (working capital), and why it
should **last** (moat and competition).

### 0.1 The deliberate departure from Phase 1

Phase 1 is strictly binary: one fail = REJECT, never a score. **Phase 2 is not binary, and
this is intentional.** `user.md` §4 already fixes three Phase 2 verdicts — `CLEARED TO
PHASE 3`, `HOLD — WATCH LIST` ("decent business but not good enough yet — keep watching"),
and `REJECT AT PHASE 2`. A middle verdict cannot be produced by a pass/fail filter, so
Phase 2 grades each check on five states instead of two:

| Status | Meaning | Effect on verdict |
| :-- | :-- | :-- |
| `PASS` | Clears the quality bar | none |
| `CONCERN` | Below the quality bar but not disqualifying | accumulates — see §3 |
| `FAIL` | Structurally disqualifying | immediate `REJECT AT PHASE 2` |
| `INCONCLUSIVE` | Required data unavailable or unverifiable | blocks a CLEARED verdict |
| `NOT_APPLICABLE` | Check does not apply (stated reason required) | excluded from counts |

**The Trend Modifier:** `CONCERN` and `PASS` are not static. 
- If a check is in the `CONCERN` zone but the metric has improved for 3 consecutive years, upgrade to `PASS`.
- If a check is in the `PASS` zone but the metric has deteriorated for 3 consecutive years, downgrade to `CONCERN`.

This is still **not a score out of twelve**. A `FAIL` is never outweighed by passes
elsewhere, and `CONCERN` counts are evaluated by rule (§3), never averaged into a rating.

### 0.2 No price, ever

**No price, market capitalisation, P/E, or valuation multiple may enter a Phase 2
assessment.** If a quality judgement needs the share price to work, it belongs to Phase 3.
This is the single easiest boundary to erode and the most damaging when it goes — a cheap
price makes a mediocre business look acceptable, which is exactly the reasoning error the
phase structure exists to prevent.

### 0.3 No short-circuit

Unlike Phase 1, Phase 2 **does not stop at the first FAIL**. Evaluate all twelve checks
every time. A rejected company still yields a useful quality profile, and a `HOLD — WATCH
LIST` verdict is meaningless without the complete picture of what would need to improve.

---

## 1. Inputs (what to gather before deciding)

For the stock under review, collect these data points. Cite the source and period for each,
exactly as Phase 1 requires. The "Q#" column shows which question set item each check answers.

| # | Q# | Check | Data to pull | Preferred source |
| :-: | :-: | :-- | :-- | :-- |
| 7 | Q19, Q20 | Return on capital | 5-yr RoCE (EBIT ÷ (total equity + total debt − cash)); 5-yr RoE | Screener.in ratios; P&L + balance sheet |
| 8 | Q19 | Margin trajectory | 5-yr gross, EBITDA and net margin; driver of each move | P&L, 5 years; MD&A for the "why" |
| 9 | Q18 | Segment economics | Per segment ≥10% of revenue: 3-yr revenue, volume, realisation, segment margin | AR → "Segment Reporting" note |
| 10 | Q22, Q20 | Leverage quantum & trend | 3-yr gross debt, cash, net debt, EBITDA, total equity | Balance sheet + P&L, 3 years |
| 11 | Q26, Q20 | Interest-service adequacy | 3-yr EBIT and finance cost | P&L, 3 years |
| 12 | Q23 | Maturity & refinancing | Short-term vs long-term borrowings; principal due within 12 months; cash; latest CFO; undrawn committed lines | AR → borrowings note + maturity schedule |
| 13 | Q24, Q25 | Cost, rating & covenants | Avg. cost of borrowing; credit rating + outlook; 3-yr rating actions; secured/unsecured split; covenant terms and any breach/waiver | Rating agency press release (CRISIL/ICRA/CARE/India Ratings); AR borrowings note |
| 14 | Q27 | Loans given to other companies | Inter-corporate deposits/loans/advances to subsidiaries, JVs, associates, related parties; net worth; interest-bearing?; any provision or write-off | AR → "Loans and advances" + related-party notes |
| 15 | Q28 | Guarantees & off-balance-sheet | Corporate guarantees, letters of comfort, security given for other entities; borrowings from group/related parties | AR → contingent liability + related-party notes |
| 16 | Q20 | Working-capital cycle | 3-yr receivable days, inventory days, payable days; advances paid to vendors | Balance sheet + P&L, 3 years |
| 17 | Q29 | Moat corroboration | Stated moat type; RoCE spread trend; gross margin trend; realisation trend | AR/MD&A narrative + the numbers from Checks 7 and 8 |
| 18 | Q31 | Competitive position | Market share over 3 yrs; growth vs. named peers | Industry bodies, AR "Industry Structure", peer filings |

**If a required data point is unavailable or unverifiable, do not guess.** Mark that check
`INCONCLUSIVE — data not available`, name exactly what is missing and where it would
normally be found, and treat it as a hold (§3). Never fabricate a `FAIL` from absence.

**Reporting basis consistency.** Every ratio in a single check must be computed from the
same basis — consolidated or standalone — and the basis must be stated. Never mix a
consolidated EBITDA with a standalone debt figure. Prefer **consolidated** throughout;
where only standalone is available, say so and mark the check's confidence accordingly.
Where the company has material subsidiaries, a standalone-only assessment of Checks 10, 14
and 15 is `INCONCLUSIVE`, because the exposure being measured sits in the subsidiaries.

**Track record shorter than the lookback window.** If the company has been reporting for
less than the window a check requires (5 years for Checks 7 and 8, 3 years for the rest),
evaluate over whatever full years exist and mark the check `INCONCLUSIVE — insufficient
track record (only N years available)`. Exception: a disqualifying condition visible in even
one available year (negative net worth, a covenant breach, a below-investment-grade rating)
still triggers an immediate `FAIL`.

**Cyclical businesses.** For companies in cyclical sectors (metals, commodities, autos,
chemicals, shipping), always judge Checks 7, 8, 10 and 11 on the **5-year median**, never the
latest year alone. A peak-cycle year flatters every one of them.

---

## 2. Pass / Concern / Fail logic (exact thresholds)

Apply each rule literally. Boundary values for FAIL/PASS are not one-size-fits-all; they vary by industry. **Read §2.5 (Industry Boundary Matrix) before applying any threshold.**

### Group A — What the business earns

**Check 7 — Return on Capital Employed** *(Q19, Q20)*

The single most important check in Phase 2. RoCE = `EBIT ÷ (Total equity + Total debt − Cash
and equivalents)`, expressed as %.

- `FAIL` if **any** of:
  1. 5-year **median** RoCE is **below the FAIL threshold for the sector** (see §2.5).
  2. RoCE declined in **4 of the last 5 years** *and* the latest year is **< 15%**.
  3. Latest-year RoCE is **negative**.
- `CONCERN` if 5-year median RoCE is **between the FAIL and PASS thresholds** for the sector.
- `PASS` if 5-year median RoCE is **≥ the PASS threshold** for the sector and not in sustained decline.

**Check 8 — Margin trajectory** *(Q19)*

Assess gross, EBITDA and net margin over 5 years, and identify the driver of each material
move (input costs, mix, pricing, operating leverage, one-offs).

- `FAIL` if **any** of:
  1. Latest-year EBITDA margin **≤ 0** (the business loses money at the operating level).
  2. EBITDA margin declined by **more than 25% of its 3-year average** over 3 years with no identified,
     non-recurring cause.
  3. Net margin negative in **≥ 2 of the last 3 years**.
- `CONCERN` if EBITDA margin declined **10–25% of its 3-year average** over 3 years, **or** the decline is
  structural (permanent pricing pressure, adverse mix shift) rather than cyclical.
- `PASS` if EBITDA margin is stable (within ±10% relative variance) or rising over 3 years, with the move
  explained.

> **Note:** a margin move with **no identified driver** is not a pass. If the numbers moved
> and the reason cannot be established from the MD&A or concall, mark `INCONCLUSIVE`.

**Check 9 — Segment economics** *(Q18)*

For each reported segment contributing **≥ 10% of revenue**, compile the 3-year trend in
revenue, volume, realisation and segment margin.

- `NOT_APPLICABLE` if the company reports a **single** operating segment — state this, and
  rely on Check 8. Do not synthesise segments that the company does not disclose.
- `FAIL` if the **dominant segment** (> 40% of revenue) shows **both** declining revenue
  **and** declining segment margin over 3 years.
- `CONCERN` if **any** segment ≥ 10% of revenue shows both declining revenue and declining
  margin, **or** if growth is concentrated entirely in the lowest-margin segment (revenue
  growing while mix degrades).
- `PASS` if the dominant segment is growing or stable on both revenue and margin.
- `INCONCLUSIVE` if the company reports multiple segments but discloses revenue only,
  without segment results — name the missing disclosure.

### Group B — What the business owes

**Check 10 — Leverage quantum & trend** *(Q22, Q20)*

Compute gross debt, cash, net debt (`gross debt − cash and equivalents`), `net debt ÷
EBITDA`, and `total debt ÷ total equity` for each of the last 3 years.

- **Net-cash auto-PASS:** if net debt is **negative** (cash exceeds total debt) in the latest
  year, this check is `PASS`. Per the question set's own instruction for net-cash companies,
  shift the weight to Checks 14 and 15 — where idle cash and inter-corporate exposure are the
  real questions — and note in the finding that leverage risk has been displaced, not absent.
- `FAIL` if **any** of:
  1. `Net debt ÷ EBITDA` is **above the FAIL threshold for the sector** (see §2.5).
  2. `Total debt ÷ total equity` is **above the FAIL threshold for the sector** (see §2.5).
  3. Total equity (net worth) is **≤ 0**.
- `CONCERN` if `net debt ÷ EBITDA` is **between the PASS and FAIL thresholds** for the sector, **and** has risen in each of the last
  3 years.
- `PASS` if `net debt ÷ EBITDA` and `debt ÷ equity` are **both ≤ the PASS thresholds** for the sector.

Cross-reference the direction of travel against the capital-allocation stance recorded at
Q17. Leverage rising while management describes a deleveraging priority is a **credibility
flag** — record it in the finding even where the ratio itself passes.

**Check 11 — Interest-service adequacy** *(Q26, Q20)*

Interest coverage = `EBIT ÷ finance cost`.

- `NOT_APPLICABLE` if the company is net cash **and** finance cost is under 1% of EBIT.
- `FAIL` if latest-year interest coverage is **below the FAIL threshold for the sector** (see §2.5), **or** coverage fell below that threshold in any
  of the last 3 years.
- `CONCERN` if coverage is **between the FAIL and PASS thresholds** for the sector, **or** coverage has declined in each of the
  last 3 years regardless of level.
- `PASS` if coverage is **≥ the PASS threshold** for the sector and stable or rising.

For order-book-driven businesses, additionally state whether coverage survives a **30%
EBITDA decline** — the question set asks for adequacy "through a downturn", not at peak.
Failing that stress test is a `CONCERN` even where the current level passes.

**Check 12 — Maturity & refinancing risk** *(Q23)*

- `NOT_APPLICABLE` if the company has no borrowings.
- `FAIL` if principal due within the next 12 months **exceeds** `cash and equivalents +
  latest-year CFO + committed undrawn credit lines`, i.e. scheduled repayment cannot be met
  without new financing that is not yet arranged.
- `CONCERN` if **either** short-term borrowings exceed **the Max ST Debt % for the sector** (see §2.5), **or** 12-month maturities are covered but only by
  drawing cash below one quarter of operating expenses.
- `PASS` if 12-month maturities are comfortably covered and the maturity profile is
  reasonably matched to asset life.

**Check 13 — Cost of debt, credit rating & covenants** *(Q24, Q25)*

- `NOT_APPLICABLE` if the company has no borrowings and no rated instruments.
- `FAIL` if **any** of:
  1. Current long-term rating is **below investment grade** (below `BBB-` on the CRISIL /
     ICRA / CARE / India Ratings scale), or the issuer is on **default/`D`**.
  2. A downgrade of **≥ 2 notches** occurred in the last 3 years.
  3. A **financial covenant breach** is disclosed — whether or not a waiver was obtained.
     A waived breach is still a breach; record the waiver in the finding.
- `CONCERN` if **any** of: a 1-notch downgrade or a move to **negative outlook** in the last
  3 years; the company carries material debt but is **unrated**; average cost of borrowing
  rose more than **150 bps** year-on-year without a corresponding move in policy rates; or
  substantially all assets are pledged as security, leaving no unencumbered collateral.
- `PASS` if the rating is investment grade and stable or upgraded, no covenant issues, and
  borrowing cost is in line with the rating.

**Check 14 — Loans and advances GIVEN to other companies** *(Q27)*

Sum inter-corporate deposits, loans and advances extended to subsidiaries, JVs, associates
and related parties; express as % of net worth. Cross-reference the related-party
disclosures already examined at Phase 1 Check 3 — but judge them here on **capital
discipline**, not honesty.

- `FAIL` if **any** of:
  1. Total such exposure **> 25% of net worth**. (Note: if company is **net-cash**, this FAIL threshold is tightened to **> 15%**).
  2. Any material portion is **non-interest-bearing** or carries a rate materially below the
     company's own cost of borrowing (the company is funding an affiliate at shareholder
     expense).
  3. Any **provision, impairment or write-off** has been recognised against these balances,
     or recoverability is qualified by the auditor.
- `CONCERN` if exposure is **10–25% of net worth**, or has grown faster than revenue over
  3 years.
- `PASS` if exposure is **≤ 10% of net worth**, interest-bearing at arm's length, and
  performing.

**Check 15 — Guarantees & debt links to OTHER companies** *(Q28)*

Quantify corporate guarantees, letters of comfort and security given on behalf of other
entities. Reconcile the total against the contingent-liability trend established at Phase 1
Check 4 — this check asks a different question of the same disclosure: not "is it large?"
but "whose obligation is it?"

- `NOT_APPLICABLE` if no guarantees or comfort letters are disclosed.
- `FAIL` if **any** of:
  1. Guarantees given on behalf of entities that are **not subsidiaries** (third parties,
     promoter-group companies, associates outside the consolidation) are **material**.
  2. Total guarantees exceed **50% of net worth**.
  3. Any guarantee has been
    invoked, or a payment has been made under one.
- `CONCERN` if total guarantees are **25–50% of net worth**, or the company has borrowed
  from group/related parties or non-institutional sources on undisclosed terms.
- `PASS` if guarantees are limited to consolidated subsidiaries and total **≤ 25% of
  net worth**.

### Group C — How the business collects

**Check 16 — Working-capital cycle** *(Q20)*

Cash conversion cycle (CCC) = `receivable days + inventory days − payable days`. Compute for
each of the last 3 years.

Judge the **trend**, not the level. Long-cycle businesses (defence, EPC, capital goods,
infrastructure) structurally carry long cycles; that is the business model, not a defect.

- `FAIL` if CCC deteriorated by **more than the FAIL threshold for the sector** (see §2.5) over 3 years **and** receivable days
  exceed **the Critical Cap for the sector** (see §2.5).
- `CONCERN` if **any** of: CCC deteriorated **between the PASS and FAIL thresholds** for the sector over 3 years; receivable days rose
  **more than 30%** over 3 years; inventory grew materially faster than revenue; or advances
  paid to vendors rose sharply without a matching order-book increase.
- `PASS` if CCC is stable or improving over 3 years.

Where the cycle is lengthening, state explicitly whether it is being **funded by suppliers**
(payable days rising in step) or **by borrowing** — the latter connects directly to Check 10
and should be noted in both findings.

### Group D — Why the business should last

**Check 17 — Moat corroboration** *(Q29)*

This check exists to stop a moat from being asserted rather than demonstrated. State the
claimed moat type (brand, scale, licence/regulatory, switching costs, network, cost advantage), then test whether the **numbers corroborate it**. A moat that is real shows up
in the financials; a moat that only appears in the annual report's narrative is marketing.

The four corroborators:
- **(a)** RoCE sustained **≥ the PASS threshold for the sector** (see §2.5) in at least **4 of the last 5 years** (from Check 7).
- **(b)** Gross margin stable or rising over 3 years (from Check 8).
- **(c)** Market share stable or rising over 3 years (from Check 18).
- **(d)** Realisation (price per unit) rising at or above input-cost inflation — evidence of
  pricing power.

- `FAIL` if the claimed moat is **contradicted**: (a), (b) and (c) are **all** deteriorating.
  A narrative moat with falling returns, falling margins and falling share is an eroding
  moat, and the stated advantage should be recorded as disproved.
- `CONCERN` if **only one** of the four corroborators is present, or if the moat rests
  entirely on a licence, subsidy or policy protection with a **known expiry or review date**
  inside 3 years.
- `PASS` if **two or more** corroborators are present, **including at least one "hard" financial proof ((a) or (b))**, and none of (a)–(c) is deteriorating.
- `INCONCLUSIVE` if fewer than two corroborators can be evaluated at all.

**Check 18 — Competitive position** *(Q31)*

Identify the key competitors and the direction of market share over 3 years.

- `FAIL` if the company's market share has declined for **3 consecutive years** in its
  primary market **and** revenue growth has trailed the industry in each of those years.
- `CONCERN` if share is flat-to-down while the industry is growing, **or** the largest
  competitor is growing materially faster, **or** a credible new entrant / substitute
  technology is displacing the core product.
- `PASS` if share is stable or rising.
- `INCONCLUSIVE` if no reliable share data exists.

---

## 2.5 Industry Boundary Matrix

Thresholds for Checks 7, 10, 11, 12, and 16. These ensure we don't penalise a power plant
for having the leverage of a software company, or a software company for having the
returns of a utility.

| Metric | Asset-Light (SaaS, FMCG, Services) | Standard (Manufacturing, Retail) | Cap-Intensive (Metals, Chem, Auto) | Regulated / Infra (Power, Toll, Pipe) |
| :-- | :-- | :-- | :-- | :-- |
| **RoCE** (Pass / Fail) | $\ge 20\% \ / \ < 15\%$ | $\ge 15\% \ / \ < 10\%$ | $\ge 12\% \ / \ < 8\%$ | $\ge 10\% \ / \ < 6\%$ |
| **Net Debt/EBITDA** (Pass / Fail) | $\le 1.0\text{x} \ / \ > 2.0\text{x}$ | $\le 2.0\text{x} \ / \ > 3.0\text{x}$ | $\le 3.0\text{x} \ / \ > 4.5\text{x}$ | $\le 4.0\text{x} \ / \ > 6.0\text{x}$ |
| **Int. Coverage** (Pass / Fail) | $\ge 6.0\text{x} \ / \ < 3.0\text{x}$ | $\ge 4.0\text{x} \ / \ < 2.0\text{x}$ | $\ge 3.0\text{x} \ / \ < 1.5\text{x}$ | $\ge 2.0\text{x} \ / \ < 1.0\text{x}$ |
| **Max ST Debt %** (Concern) | 15% | 20% | 15% | 10% |
| **CCC Det.** (Pass / Fail) | $\le 30 \text{ days} \ / \ > 30$ | $\le 60 \text{ days} \ / \ > 60$ | $\le 90 \text{ days} \ / \ > 90$ | $\le 120 \text{ days} \ / \ > 120$ |
| **Max Rec. Days** (Crit Cap) | 60 days | 90 days | 120 days | 150 days |

**Application rules:**
1. **Classification:** The analyst must state the sector classification before applying the matrix.
2. **The "Between" Zone:** If a value falls between the PASS and FAIL thresholds, it is a `CONCERN` (unless the Trend Modifier in §0.1 applies).
3. **Regulated/Infra Exception:** The relaxed thresholds for Regulated/Infra apply only if the company can prove $\ge 70\%$ of its revenue comes from long-term regulated contracts.

---

## 3. The Decision Rule

Evaluate the results of the twelve checks. A verdict is determined by the presence of `FAIL`s, `CONCERN`s, and `INCONCLUSIVE`s.

1. **Any `FAIL` $\to$ verdict is `REJECT AT PHASE 2`.**
   Immediate disqualification. No offsetting.
2. **If no `FAIL`s, but $\ge 3$ `CONCERN`s $\to$ verdict is `REJECT AT PHASE 2`.**
   Three warnings across different groups indicate a business that is structurally mediocre.
3. **If no `FAIL`s and $< 3$ `CONCERN`s, but $\ge 1$ `INCONCLUSIVE` $\to$ verdict is `HOLD — INCONCLUSIVE`.**
   The quality is not yet proven. Do not move to price until the data gap is closed.
4. **If no `FAIL`s and $< 3$ `CONCERN`s, and no `INCONCLUSIVE`s, but $\ge 1$ `CONCERN` $\to$ verdict is `HOLD — WATCH LIST`.**
   A decent business with a specific flaw. State the specific improvements that would move it to CLEARED, and what to re-check next
   quarter.
5. **Else $\to$ verdict is `CLEARED TO PHASE 3`.**
   State explicitly that this means *only* "this is a good business" — **not** "buy". Price
   has not been examined at all. A CLEARED verdict at Phase 2 says the apartment is worth
   living in; it says nothing about the asking price.

`NOT_APPLICABLE` checks are excluded from all counts, but each one must carry a stated
reason. An unexplained `NOT_APPLICABLE` is treated as `INCONCLUSIVE`.

---

## 4. Internal working table (analyst view — precise, technical)

This is the raw evidence table. It stays exact and numeric — the plain-English wrapping
happens in §5, on top of this table, never instead of it.

```
# Phase 2 — <Company Name> (<TICKER>)
**As of:** <date data pulled>   **Basis:** <Consolidated / Standalone>
**Sector treatment:** <Default / Regulated infra / Cyclical / Asset-light / Out of scope>
**Phase 1:** CLEARED TO PHASE 2 on <date>  (result_id: <id>)

## VERDICT: <CLEARED TO PHASE 3 | HOLD — WATCH LIST | REJECT AT PHASE 2 | HOLD — INCONCLUSIVE>
<one line: e.g. "Failed Check 7 (5-yr median RoCE 9.4% vs 12% floor) — not a quality business.">
**Concerns:** <n> (<group letters>)   **Inconclusive:** <n>

### Group A — What it earns
| # | Check | Finding (with number vs threshold) | Source | Status |
| :-: | :-- | :-- | :-: | :-: |
| 7 | Return on capital | | | |
| 8 | Margin trajectory | | | |
| 9 | Segment economics | | | |

### Group B — What it owes
| # | Check | Finding (with number vs threshold) | Source | Status |
| :-: | :-- | :-- | :-: | :-: |
| 10 | Leverage quantum & trend | | | |
| 11 | Interest-service adequacy | | | |
| 12 | Maturity & refinancing | | | |
| 13 | Cost, rating & covenants | | | |
| 14 | Loans given to others | | | |
| 15 | Guarantees & off-BS | | | |

### Group C — How it collects
| # | Check | Finding (with number vs threshold) | Source | Status |
| :-: | :-- | :-- | :-: | :-: |
| 16 | Working-capital cycle | | | |

### Group D — Why it lasts
| # | Check | Finding (with number vs threshold) | Source | Status |
| :-: | :-- | :-- | :-: | :-: |
| 17 | Moat corroboration | | | |
| 18 | Competitive position | | | |

## PESTLE context (no verdict — Q30)
- <factor>: <what it affects, and what would have to change for it to matter>

## Why the verdict
- <for each FAIL: the number, the threshold it breached, and the plain-language risk>
- <for each CONCERN: the number, the bar it missed, and what would clear it>
- <for a CLEARED verdict: confirm the hard thresholds cleared and name the strongest evidence>

## What the data does NOT let us conclude
- <any check marked inconclusive, and exactly which document would close it>

## What would change this verdict
- <specific, observable events — "net debt/EBITDA below 2.0x for two consecutive years",
   "receivable days back under 90" — not vague improvement>
```

Formatting rules for this internal table:
- Every quantitative finding must be **sourced** (document + period, e.g. "FY25 AR, Note 41"
  or "Screener, as of DD-MMM-YYYY"). No unsourced numbers.
- Show the **actual number against the threshold** for each check ("net debt/EBITDA 3.4x vs
  3.0x limit"), not just "Fail".
- State the **reporting basis** on any check where consolidated and standalone would differ.
- Separate **what the data shows** from **what it implies**.
- Never soften a `FAIL` into a `CONCERN` because the business is otherwise attractive. The
  `CONCERN` state exists for genuinely sub-threshold-but-not-disqualifying findings, and it
  is the one place where this framework could quietly be talked into a bad answer.
- Never mention the share price, market cap, or any valuation multiple anywhere in this
  table (§0.2).

---

## 5. Investor-facing output (must run through `user.md`)

The internal table in §4 is the analyst's working evidence. **It is never shown to the
investor on its own.** Every time this screen is run against a real stock, the final response
must be re-expressed through `user.md`'s rules before it is sent:

- Open with a one-to-two sentence plain-English verdict in storytelling form — the investor
  should know the answer before any numbers appear.
- Introduce the phase with the standard Phase 2 framing from `user.md`'s Quick Reference:
  *"Now we check if the business is actually good... Think of it as inspecting the apartment
  before you agree to buy it."*
- Explain every technical term the moment it is first used — analogy first, label second
  (`user.md` §2, §10). Phase 2 is dense with the exact terms `user.md` §6 forbids leaving
  unexplained: **RoCE, EBITDA, EBIT, debt-to-equity, interest coverage, working capital days,
  moat, contingent liabilities, capex**. Every one of them needs its plain-English
  explanation on first use, in the same or next sentence.
- Translate every number into a relatable fact: *"for every ₹100 put into this business, it
  earns ₹18 a year in profit"* — not *"RoCE is 18%"*.
- Use the exact translation table from `user.md` §4:
  - `CLEARED TO PHASE 3` → "Good business — now check if the price is fair"
  - `HOLD — WATCH LIST` → "Decent business but not good enough yet — keep watching"
  - `REJECT AT PHASE 2` → "Not a quality business — do not invest"
- Close every section with a "so what does this mean for me" line.
- Keep paragraphs short (3–4 lines) for mobile reading.
- End with the disclaimer, verbatim, from `user.md` §9.
- Never imply a guaranteed return anywhere in the write-up.
- **`CLEARED TO PHASE 3` means "this is a good business" — it is never a buy signal**, because
  the price has not been looked at. Say this explicitly every time a CLEARED verdict is
  delivered.

### 5a. Worked example — REJECT AT PHASE 2, translated

> **The short answer:** This company is honest — it passed our first check — but it isn't a
> good enough business to own. For every ₹100 invested in it, it earns only about ₹9 a year,
> and that number has been shrinking. We stop here.
>
> Here's what that means. The most important question about any business is simple: *if I
> put ₹100 into it, how much profit does it make me each year?* That's called **Return on
> Capital Employed**, or RoCE. Think of a shop — if you put ₹100 into stock and fittings and
> it earns you ₹20 a year, that's a 20% return, and a good one.
>
> This company earns about **₹9 on every ₹100** (5-year median RoCE 9.4%, FY21–FY25 annual
> reports). A fixed deposit pays you around ₹7 with no risk at all. So you'd be taking on
> all the risk of owning a business for barely more than a bank deposit — and the trend is
> downward, not upward.
>
> Its debts add to the problem. The company owes about **3.4 times** what it earns in a year
> before interest and depreciation (net debt to EBITDA of 3.4x vs. the 3.0x line we treat as
> the limit; FY25 balance sheet). Imagine someone earning ₹10 lakh a year carrying a ₹34 lakh
> loan — manageable in a good year, dangerous in a bad one.
>
> **So what does this mean for you?** Nothing here says the company is dishonest. It simply
> isn't a good enough business to be worth your money at any price — so we never even get to
> the question of whether the stock is cheap. That's the framework doing its job: it stopped
> you two steps before a mistake.
>
> *This is educational analysis only, not personalised investment advice. Please consult a
> SEBI-registered investment adviser before making any investment decisions.*

### 5b. Worked example — HOLD — WATCH LIST, translated

> **The short answer:** This is a decent business with one problem worth watching — it's
> taking much longer to collect money from its customers than it used to. Good enough to keep
> an eye on, not good enough to move forward on yet.
>
> The good part first. For every ₹100 invested in the business, it earns about **₹17 a year**
> (RoCE of 17%, five-year average) — comfortably above the 15% level we look for, and steady
> rather than slipping. It also carries very little debt.
>
> Now the concern. Three years ago, customers paid their bills in about 70 days. Today it
> takes **112 days** (FY25 annual report). The company is still making the sale and still
> booking the profit — but the cash is arriving a month and a half later than it used to.
> Think of a shop that keeps selling on credit: the sales ledger looks healthy while the
> till stays empty.
>
> **So what does this mean for you?** One warning light, not a breakdown. We put this company
> on a watch list and look again after the next two results. If collections come back under
> 90 days, it moves forward to the price check. If they keep stretching, the profits on paper
> will stop turning into real cash — and that becomes a reason to walk away.
>
> *This is educational analysis only, not personalised investment advice. Please consult a
> SEBI-registered investment adviser before making any investment decisions.*

---

## 6. Guardrails (non-negotiable)

1. **One `FAIL` = reject.** No averaging, no "the growth story makes up for it," no
   offsetting a structural failure against strengths in another group. `CONCERN` accumulates
   by the rule in §3 and by nothing else.
2. **Never soften a `FAIL` into a `CONCERN`.** The three-state design exists to allow a
   genuine middle verdict, not to create room for negotiation. If a number breaches a FAIL
   threshold, it is a FAIL.
3. **No price, no valuation, no market cap.** If the analysis needs the share price, it has
   left Phase 2 (§0.2).
4. **Flag missing data, don't estimate.** An unverifiable input is `INCONCLUSIVE`, never a
   confident guess. This applies with particular force to market share (Check 18), which is
   easy to assert and hard to source.
5. **No return promises.** This screen makes no forecast of any kind.
6. **Passing ≠ buy.** `CLEARED TO PHASE 3` means the business is good and the price is still
   entirely unexamined. Say so every time, in the investor's own translation table language.
7. **Financials are out of scope.** Banks and NBFCs must be marked
   `INCONCLUSIVE — SECTOR OUT OF SCOPE`, never forced through these thresholds (§2.5).
8. **Sector adjustments must be evidenced, not assumed.** The relaxed infrastructure
   threshold applies only with the contracted-revenue percentage stated and sourced.
9. **Never re-run a Phase 1 check here.** Related-party transactions appear in Check 14 and
   contingent liabilities in Check 15, but they are asked as *capital-discipline* questions,
   not honesty questions. A stock that cleared Phase 1 is not re-tried for honesty.
10. **Communication is mandatory, not optional.** An investor-facing Phase 2 response that
    skips the `user.md` plain-English wrapping (§5) is incomplete, even if the underlying
    twelve-check analysis is correct.
11. **Scope.** This file covers Phase 2 only. Peer valuation multiples (Q21) and the
    return-requirement analysis (Q40) belong to Phase 3 and are out of scope here.
12. **Educational only.** Close every verdict with the SEBI-registered-adviser reminder,
    verbatim from `user.md` §9.

---

## 7. Definition of done

- [ ] Phase 1 verdict confirmed as `CLEARED TO PHASE 2` before starting.
- [ ] All twelve checks assessed — no short-circuit — or explicitly marked `INCONCLUSIVE` /
      `NOT_APPLICABLE` with the reason and missing source named.
- [ ] Reporting basis (consolidated / standalone) stated and consistent within every check.
- [ ] Sector treatment stated, and any relaxed threshold evidenced with its source.
- [ ] Each check shows the actual figure against its threshold, with a citation.
- [ ] PESTLE context section present (Q30), carrying no verdict.
- [ ] A single clear verdict: `CLEARED TO PHASE 3` / `HOLD — WATCH LIST` / `REJECT AT PHASE 2` / `HOLD — INCONCLUSIVE`.
- [ ] Any `FAIL` names the specific check and breached threshold.
- [ ] A `HOLD — WATCH LIST` verdict names the specific, observable changes that would clear it.
- [ ] No share price, market cap, or valuation multiple appears anywhere in the output.
- [ ] The investor-facing write-up follows `user.md` — plain-English lead, terms explained,
  numbers translated, translation table used, "so what does this mean for me" per section.
- [ ] No specific return is promised or implied; the SEBI disclaimer is present verbatim.

---

## 8. Data Retrieval & Execution Solution (Sources, Links & Approach)

*This section defines the automated/standard retrieval pipeline for running Phase 2 on any
Indian listed stock given just the company name or stock ticker. It assumes the Phase 1
pipeline has already run and its artefacts (Annual Report PDFs, Screener tables) are cached.*

### 8.1 Common URLs & Repositories

| Repository / Platform | URL Pattern / Query | Primary Purpose in Phase 2 |
| :-- | :-- | :-- |
| **Screener.in (Primary Hub)** | `https://www.screener.in/company/{TICKER}/consolidated/` | 5-yr P&L (revenue, EBITDA, EBIT, finance cost, PAT), balance sheet (debt, equity, cash), 5-yr RoCE/RoE ratio row, and the working-capital days block. Covers Checks 7, 8, 10, 11, 16 at first pass. |
| **Annual Report PDFs (via Screener → Documents)** | Latest 3–5 FYs | Segment note (Check 9), borrowings maturity schedule (Check 12), covenant and security terms (Check 13), loans-and-advances note (Check 14), guarantees note (Check 15), MD&A for margin drivers (Check 8) and moat narrative (Check 17). |
| **Credit rating agencies** | CRISIL `https://www.crisil.com/en/home/our-businesses/ratings.html`<br>ICRA `https://www.icra.in/Rating/RatedEntity`<br>CARE `https://www.careratings.com/`<br>India Ratings `https://www.indiaratings.co.in/` | Rating, outlook, 3-yr rating action history, and the agency's own commentary on leverage, covenants and liquidity (Check 12). Rating rationales are often the single best source for the maturity profile (Check 12). |
| **BSE / NSE quarterly results filings** | `https://www.bseindia.com/corporates/Comp_Results.aspx?Code={BSE_SCRIP_CODE}` | Latest quarter segment revenue and results, ahead of the next Annual Report (Checks 8, 9). |
| **Industry bodies / sector regulators** | e.g. SIAM (autos), IBEF sector reports, sector regulator dashboards | Market share and industry growth (Check 18). Where none exists, Check 18 is `INCONCLUSIVE`. |
| **Peer filings** | Screener pages of 3–5 named competitors | Relative growth and margin comparison for Check 18. **Pull operating metrics only — never valuation multiples** (§0.2). |

### 8.2 What Files to Pull from Each Link

| Link / Source | File / Document to Pull | Storage / Working Name | Details to Extract from File |
| :-- | :-- | :-- | :-- |
| **Screener.in** → main page HTML | Rendered financial tables | Raw extracted tables (JSON/Text) | • 5-yr P&L: Sales, Operating Profit, OPM %, Interest, Depreciation, Profit before tax, Net Profit.<br>• 5-yr Balance Sheet: Borrowings, Reserves, Equity Capital, Cash equivalents.<br>• Ratios row: RoCE %, RoE %.<br>• "Working Capital Days", "Debtor Days", "Inventory Days" block. |
| **Annual Report PDF** (latest 3 FYs) | `{TICKER}_AR_FY{YYYY}.pdf` (reuse Phase 1 cache) | — | • **Segment Reporting note:** segment revenue, segment results, segment assets (Check 9).<br>• **Borrowings note:** long-term vs. short-term split, repayment/maturity schedule, secured vs. unsecured, assets charged, covenant terms (Checks 12, 13).<br>• **Loans and advances note + Related Party note:** inter-corporate deposits, loans to subsidiaries/JVs/associates, interest rate charged, provisions (Check 14).<br>• **Contingent Liabilities note:** corporate guarantees, letters of comfort, security given for others (Check 15).<br>• **MD&A / Directors' Report:** stated drivers of margin movement (Check 8), stated moat and industry structure (Checks 17, 18), capital-allocation stance (cross-ref Q17). |
| **Rating agency** | Latest rating rationale + 3 yrs of prior actions (PDF) | `{TICKER}_Rating_{Agency}_{Date}.pdf` | • Current long-term rating and outlook; 3-year action history from the rating agency site (**Check 13**).<br>• Agency's stated leverage and coverage figures against the values computed in Step 1. A material divergence usually means a basis mismatch — resolve before
proceeding, do not average the two. |
| **BSE/NSE results filings** | Latest quarterly results PDF/XBRL | `{TICKER}_Q{n}FY{YY}_Results.pdf` | • Segment revenue and results for the latest quarter (Check 9), to catch deterioration post-dating the Annual Report. |
| **Industry / peer sources** | Sector report or peer Screener pages | `{SECTOR}_share_{YYYY}.*` | • Market share by player over 3 yrs; industry growth rate (Check 18). |

### 8.3 Step-by-Step Extraction Approach

When initiating a Phase 2 review with `{TICKER}` and a confirmed Phase 1 clearance:

1. **Step 0 — Gate and classify.**
   - Confirm the Phase 1 result is `CLEARED TO PHASE 2`; abort otherwise.
   - Classify the sector against §2.5. **If financial services, stop immediately** and return
     `INCONCLUSIVE — SECTOR OUT OF SCOPE`. Otherwise record which threshold set applies.
   - Fix the reporting basis (prefer consolidated) and carry it through every computation.

2. **Step 1 — Rapid quantitative screen via Screener.in.**
   - Fetch the consolidated company page.
   - Extract 5-yr EBIT, finance cost, borrowings, equity and cash. Compute 5-yr RoCE median
     (**Check 7**), interest coverage (**Check 11**), net debt/EBITDA and debt/equity 3-yr
     trend (**Check 10**).
   - Extract 5-yr OPM % and the working-capital days block → margin trajectory (**Check 8**)
     and cash conversion cycle trend (**Check 16**).
   - **If Check 7 or Check 10 already fails here, the verdict is `REJECT AT PHASE 2`** — but
     per §0.3, still complete the remaining checks before writing up.

3. **Step 2 — Annual Report deep extraction.**
   - Reuse the Phase 1 cached PDFs; download any missing years.
   - Segment note → per-segment 3-yr revenue and results (**Check 9**).
   - Borrowings note → maturity schedule, short/long split, security, covenants
     (**Checks 12, 13**).
   - Loans and advances + related-party notes → inter-corporate exposure as % of net worth
     (**Check 14**).
   - Contingent liabilities note → guarantees and comfort letters, reconciled against the
     Phase 1 Check 4 figure (**Check 15**).
   - MD&A → the stated *reason* for every material margin move (**Check 8**) and the claimed
     moat (**Check 17**).

4. **Step 3 — Credit rating and liquidity verification.**
   - Pull the latest rating rationale and the 3-year action history from the rating agency
     site (**Check 13**).
   - Cross-check the agency's leverage and coverage figures against the values computed in
     Step 1. A material divergence usually means a basis mismatch — resolve before
     proceeding, do not average the two.

5. **Step 4 — Competitive and moat corroboration.**
   - Pull 3-yr market share from an industry body or, failing that, compute relative growth
     against 3–5 named peers' reported revenue (**Check 18**). Operating metrics only.
   - Test the claimed moat against the four corroborators (**Check 17**).
   - Compile the PESTLE context section (Q30) — no verdict.

6. **Step 5 — Verdict synthesis.**
   - Populate the §4 Internal Working Table with exact numbers, thresholds, and citations.
   - Apply the §3 decision rule in order; count `CONCERN`s by group.
   - Where the verdict is `HOLD — WATCH LIST`, write the specific observable triggers that
     would move it either way.
   - Format the final investor-facing output through §5 and `user.md`.

---

_This is an educational analysis framework, not personalised investment advice. Consult a
SEBI-registered investment advisor for guidance tailored to their financial situation._
