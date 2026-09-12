# Baseline Engine Implementation Plan: Full-Spectrum Governance & Quality Tool

This document serves as the **Technical Baseline Specification** for the end-to-end implementation of the stock analysis tool. It integrates the binary "Trust Checks" of Phase 1 and the nuanced "Quality Checks" of Phase 2 into a single, configuration-driven execution engine.

The core philosophy is **"Logic in Excel, Execution in Code."** The engine does not "know" what a red flag is; it only knows how to compare a data point against a threshold provided in the configuration files.

---

## 1. The Master Configuration Schema (The Excel Baseline)

The engine requires a standardized set of Excel workbooks. These workbooks are the "Source of Truth." If a user wants to change a rule, they change it here, not in the code.

### 1.1 `Master_Rule_Definitions.xlsx`
This sheet lists every single check from 1 to 18. It defines the "What" and "How" of each check.

| Phase | Check # | Check Name | Input Metric | Logic Type | Default Op | Default Fail Value | Sector-Aware? |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | 1 | Auditor Integrity | Audit_Opinion | Categorical | $\neq$ | "Clean" | No |
| 1 | 2 | Promoter Pledge | Pledge_Pct | Numeric | $>$ | 10% | No |
| 1 | 3 | RPT Leakage | RPT_Revenue_Pct | Numeric | $>$ | 5% | No |
| 1 | 4 | Contingent Liab | Cont_Liab_NW_Pct | Numeric | $>$ | 15% | **Yes** |
| 1 | 5 | Cash Conversion | CFO_PAT_Ratio | Ratio | $<$ | 0.80 | No |
| 1 | 6 | Exec Stability | CFO_Changes | Count | $>$ | 1 | No |
| 2 | 7 | RoCE | Median_RoCE | Numeric | $<$ | 10% | **Yes** |
| 2 | 8 | Margin Trend | EBITDA_Margin_Var | Relative | $<$ | -25% | No |
| 2 | 9 | Seg Economics | Seg_Rev_Margin_Trend| Trend | Deteriorate | N/A | No |
| 2 | 10 | Leverage | NetDebt_EBITDA | Numeric | $>$ | 3.0x | **Yes** |
| 2 | 11 | Int Coverage | Interest_Coverage | Numeric | $<$ | 2.0x | **Yes** |
| 2 | 12 | Maturity | ST_Debt_Coverage | Boolean | $\neq$ | True | No |
| 2 | 13 | Credit Rating | Credit_Rating | Categorical | $<$ | "BBB-" | No |
| 2 | 14 | Loans Given | Loan_NW_Pct | Numeric | $>$ | 25% | No |
| 2 | 15 | Guarantees | Guar_NW_Pct | Numeric | $>$ | 50% | No |
| 2 | 16 | WC Cycle | CCC_Deterioration | Numeric | $>$ | 60 days | **Yes** |
| 2 | 17 | Moat Corrob | Moat_Evidence_Count | Count | $<$ | 2 | No |
| 2 | 18 | Comp Position | Market_Share_Trend | Trend | Decline | N/A | No |

### 1.2 `Sector_Boundary_Matrix.xlsx`
For every check marked **"Sector-Aware = Yes"**, the engine looks up the values here.

| Sector Profile | Metric | Pass_Threshold | Fail_Threshold | Critical_Cap |
| :-- | :-- | :-- | :-- | :-- |
| Asset-Light | RoCE | 20% | 15% | N/A |
| Standard | RoCE | 15% | 10% | N/A |
| Cap-Intensive | RoCE | 12% | 8% | N/A |
| Regulated | RoCE | 10% | 6% | N/A |
| Asset-Light | NetDebt_EBITDA | 1.0x | 2.0x | N/A |
| Standard | NetDebt_EBITDA | 2.0x | 3.0x | N/A |
| ... | ... | ... | ... | ... |
| Asset-Light | CCC_Det | 30 days | 30 days | 60 days |
| Regulated | CCC_Det | 120 days | 120 days | 150 days |

### 1.3 `Company_Sector_Map.xlsx`
Maps industry keywords found in company data to the Sector Profiles.

| Industry Keyword | Sector Profile |
| :-- | :-- |
| "Software", "IT", "SaaS" | Asset-Light |
| "Steel", "Chemicals", "Auto" | Cap-Intensive |
| "Power", "Toll", "Utility" | Regulated |

---

## 2. Engine Execution Logic (The "Baseline")

The engine is a Python-based processor that follows this linear sequence for every stock.

### Phase 1: The Red-Flag Filter (Binary Gate)
1. **Load Config:** Read `Master_Rule_Definitions` for Checks 1–6.
2. **Fetch Data:** Pull corresponding metrics from `Stock_Data.xlsx`.
3. **Apply Logic:** 
   - For each check: If `Metric` $\text{ [Operator] } \text{ [Threshold]} \to$ `FAIL`.
   - Exception: If `Sector-Aware == Yes`, fetch threshold from `Sector_Boundary_Matrix`.
4. **Verdict:** If any check is `FAIL` $\to$ **REJECT**. Stop immediately. Else $\to$ `CLEARED TO PHASE 2`.

### Phase 2: The Quality Screen (Nuanced Grading)
1. **Load Config:** Read `Master_Rule_Definitions` for Checks 7–18.
2. **Fetch Data:** Pull corresponding metrics.
3. **Apply Logic:**
   - **Pass/Fail/Concern:** 
     - $\text{Value} \ge \text{Pass\_Threshold} \to$ `PASS`.
     - $\text{Value} < \text{Fail\_Threshold} \to$ `FAIL`.
     - $\text{Pass} > \text{Value} > \text{Fail} \to$ `CONCERN`.
4. **Trend Modifier:**
   - Apply 3-year improvement/deterioration logic to shift `PASS` $\leftrightarrow$ `CONCERN`.
5. **Verdict Synthesis:**
   - $\text{Any FAIL} \to$ `REJECT`.
   - $\ge 3 \text{ CONCERNS} \to$ `REJECT`.
   - $\ge 1 \text{ INCONCLUSIVE} \to$ `HOLD — INCONCLUSIVE`.
   - $\ge 1 \text{ CONCERN} \to$ `HOLD — WATCH LIST`.
   - Else $\to$ `CLEARED TO PHASE 3`.

---

## 3. Data Pipeline & Tooling

### 3.1 The Data Flow
`Screener/ARs` $\to$ `Data Extractor` $\to$ `Stock_Data.xlsx` $\to$ `Rule Engine` $\to$ `Verdict Table` $\to$ `Narrative Report`.

### 3.2 Component Stack
- **Configuration:** MS Excel / CSV (The user's interface).
- **Engine Core:** Python (Pandas for data frames, OpenPyXL for Excel interaction).
- **PDF Parser:** PyMuPDF (for extracting specific notes in Annual Reports).
- **Output:** Markdown (formatted via `user.md` templates).

---

## 4. Implementation Roadmap

| Milestone | Task | Deliverable |
| :--- | :--- | :--- |
| **M1: Schema** | Finalise all Excel column headers and data types. | `Baseline_Templates.xlsx` |
| **M2: Core Logic** | Build the Python class that performs the "Compare $\to$ Status" logic. | `baseline_engine.py` |
| **M3: Matrix Link** | Implement the sector-lookup logic from the Boundary Matrix. | Sector-Mapping Module |
| **M4: Pipeline** | Connect the data extractor (scrapers) to the engine input. | Data Connector |
| **M5: Reporting** | Build the Markdown generator for the internal and investor reports. | Report Generator |

## 5. Definition of Done
- [ ] All 18 checks are listed in the `Master_Rule_Definitions` Excel.
- [ ] The engine can execute Phase 1 and Phase 2 sequentially.
- [ ] Changing a value in the Excel sheet immediately changes the tool's verdict.
- [ ] Sector-specific thresholds are applied automatically based on company keywords.
- [ ] The output is a fully sourced internal table and a `user.md` narrative report.
