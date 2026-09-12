# Phase 2 Implementation Plan: The Business Quality Check

This document outlines the technical and operational roadmap for implementing the Phase 2 Gatekeeper rules. While Phase 1 was a binary "Trust Check," Phase 2 is a nuanced "Quality Discrimination" engine.

## 1. Objective
To operationalize the transition from `CLEARED TO PHASE 2` (Phase 1) to a final Phase 2 verdict (`CLEARED TO PHASE 3`, `HOLD`, or `REJECT`), ensuring that all quantitative and qualitative checks are evidenced, sourced, and judged against sector-specific benchmarks.

---

## 2. Architectural Workflow

The implementation follows a five-stage pipeline:

### Stage 1: Data Acquisition (The "Gatherer")
**Goal:** Collect all raw inputs defined in `Phase2-Rules.md` §1.
- **Screener.in Integration:** 
  - Extract 5-year P&L and Balance Sheet tables.
  - Pull the "Ratios" row for RoCE/RoE.
  - Extract the "Working Capital Days" block.
- **Annual Report (PDF) Parsing:**
  - Use PDF text extraction to locate: "Segment Reporting" notes, "Borrowings/Maturity" schedules, "Loans and Advances" notes, and "Contingent Liability" tables.
  - Search MD&A for "Margin Drivers" and "Moat/Industry Structure" narratives.
- **Regulatory/Agency Scan:**
  - Fetch latest rating rationales from CRISIL/ICRA/CARE/India Ratings.
  - Query BSE/NSE for latest quarterly segment results.

### Stage 2: Quantitative Processing (The "Calculator")
**Goal:** Transform raw data into a standardized technical dataset.
- **Median/Trend Calculation:** Compute 5-year medians for RoCE and 3-year trends for EBITDA margins and CCC.
- **Ratio Engine:**
  - `Net Debt / EBITDA` $\to$ (Gross Debt - Cash) / EBITDA.
  - `Interest Coverage` $\to$ EBIT / Finance Cost.
  - `CCC` $\to$ Receivable Days + Inventory Days - Payable Days.
- **Normalization:** Ensure all figures are on a consistent basis (Consolidated preferred).

### Stage 3: Sector Classification & Judgment (The "Judge")
**Goal:** Apply the Industry Boundary Matrix (§2.5) and the Decision Rule (§3).
- **Classification Engine:** Map the company to one of four profiles:
  - Asset-Light $\to$ Standard $\to$ Cap-Intensive $\to$ Regulated/Infra.
- **Threshold Application:**
  - Compare calculated values against the specific Pass/Fail floors/ceilings of the selected sector.
- **Trend Modifier Logic:** 
  - Check for 3-year consistent improvement/deterioration to upgrade/downgrade `PASS` $\leftrightarrow$ `CONCERN`.
- **Moat Corroboration:** Verify "hard" financial proofs (RoCE/Margin) before accepting a moat claim.

### Stage 4: Verdict Synthesis (The "Decision")
**Goal:** Determine the final status.
- **Rule Application:**
  - Any `FAIL` $\to$ `REJECT AT PHASE 2`.
  - $\ge 3$ `CONCERN`s $\to$ `REJECT AT PHASE 2`.
  - $\ge 1$ `INCONCLUSIVE` $\to$ `HOLD — INCONCLUSIVE`.
  - $\ge 1$ `CONCERN` $\to$ `HOLD — WATCH LIST`.
  - Else $\to$ `CLEARED TO PHASE 3`.

### Stage 5: Reporting (The "Translator")
**Goal:** Produce the two required outputs.
- **Output A: Internal Working Table:** A precise, sourced technical table for the analyst.
- **Output B: Investor Report:** Run the internal findings through the `user.md` translation layer:
  - Plain English lead.
  - Jargon explained via analogy.
  - Numbers translated to "₹100" facts.
  - SEBI disclaimer included.

---

## 3. Technical Requirements & Tooling

| Component | Tool / Approach | Purpose |
| :--- | :--- | :--- |
| **Scraper** | Python (BeautifulSoup / Playwright) | Extracting data from Screener.in and Exchange portals. |
| **PDF Parser** | PyMuPDF / PDFPlumber | Locating specific notes and tables in Annual Reports. |
| **Calculation** | Pandas / NumPy | Median calculations, trend analysis, and ratio computation. |
| **Reporting** | Markdown Templates | Generating the structured internal table and `user.md` output. |

---

## 4. Verification & Testing Plan

To ensure the implementation is robust, the following test cases must be run:

1. **The "SaaS" Case:** A company with high RoCE, zero debt, but low absolute margins. (Should Pass Asset-Light benchmarks).
2. **The "Utility" Case:** A company with low RoCE (11%), high leverage (4.0x), but regulated contracts. (Should Pass Regulated/Infra benchmarks).
3. **The "Red Flag" Case:** A company with a 5-year RoCE of 18% but a recent covenant breach or negative net worth. (Should trigger immediate `FAIL` $\to$ `REJECT`).
4. **The "Cash Hoarder" Case:** A net-cash company with huge inter-corporate loans. (Should test the tightened 15% limit in Check 14).
5. **The "Deterioration" Case:** A company in the `PASS` zone for leverage, but whose debt has risen for 3 consecutive years. (Should be downgraded to `CONCERN` via Trend Modifier).

## 5. Definition of Done (Implementation)
- [ ] Data pipeline successfully extracts all 12 check inputs.
- [ ] Sector classification is explicit and sourced.
- [ ] Industry Boundary Matrix is applied programmatically.
- [ ] Verdict follows the $\text{FAIL} \to \text{CONCERN} \to \text{INCONCLUSIVE}$ hierarchy.
- [ ] Output is delivered in both Technical (Internal) and Narrative (Investor) formats.
