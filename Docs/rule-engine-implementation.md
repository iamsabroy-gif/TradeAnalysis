# Rule Engine Implementation Plan: Dynamic Configuration System

This document defines the architecture for a **Configuration-Driven Rule Engine** that handles both Phase 1 and Phase 2 checks. The core objective is to decouple the **logic thresholds** from the **execution code**, allowing a user to update boundaries and sector matrices via an Excel upload without needing to modify the software.

## 1. Conceptual Architecture

The system moves from hard-coded logic to a "Triple-Input" model:
`[Stock Data]` + `[Rules Configuration]` + `[Sector Mapping]` $\to$ **Rule Engine** $\to$ `[Verdict]`

### 1.1 The Input Layer (Excel-Based)

Instead of the tool deciding what "15% RoCE" means, it looks up the value from a user-uploaded Excel file.

#### A. The Configuration Workbook (`Rules_Config.xlsx`)
This is the "Control Panel" for the analyst. It contains three primary sheets:

**Sheet 1: `Phase1_Thresholds`**
| Check # | Metric | Fail_Threshold | Operator | Sector_Aware? | Note |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 2 | Promoter_Pledge | 10% | $>$ | No | Standard red flag |
| 4 | Contingent_Liab | 15% | $>$ | Yes | Uses Sector Matrix |
| 5 | CFO_PAT_Ratio | 0.80 | $<$ | No | Cash conversion floor |

**Sheet 2: `Phase2_Matrix` (The Industry Boundary Matrix)**
| Sector Profile | Metric | Pass_Threshold | Fail_Threshold | Operator |
| :-- | :-- | :-- | :-- | :-- |
| Asset-Light | RoCE | 20% | 15% | Range |
| Standard | RoCE | 15% | 10% | Range |
| Cap-Intensive | RoCE | 12% | 8% | Range |
| Regulated | RoCE | 10% | 6% | Range |
| ... | ... | ... | ... | ... |

**Sheet 3: `Sector_Mapping`**
| Industry Keyword | Sector Profile |
| :-- | :-- |
| "SaaS", "IT Services", "FMCG" | Asset-Light |
| "Cement", "Steel", "Chemicals" | Cap-Intensive |
| "Power", "Toll", "Pipeline" | Regulated |

#### B. The Data Workbook (`Stock_Analysis_Data.xlsx`)
This provides the raw evidence for the specific stock under review.
- **Columns:** `TICKER`, `Sector_Keyword`, `Check_7_RoCE`, `Check_10_NetDebt_EBITDA`, etc.
- **Source:** Populated either manually by the analyst or via the Scraper pipeline.

---

## 2. Technical Execution Workflow

### Step 1: Configuration Loading
- The tool loads `Rules_Config.xlsx` into a memory-resident data frame (e.g., using Pandas).
- It validates that all required checks (1–18) have associated thresholds.

### Step 2: Sector Identification
- The engine reads the `Sector_Keyword` from the `Stock_Analysis_Data.xlsx`.
- It performs a lookup in the `Sector_Mapping` sheet to assign the company a **Sector Profile** (e.g., "Cap-Intensive").

### Step 3: Dynamic Rule Execution
For each check (1 through 18), the engine performs the following logic:
1. **Lookup Threshold:**
   - If `Sector_Aware == No` $\to$ Use the flat `Fail_Threshold` from `Phase1_Thresholds`.
   - If `Sector_Aware == Yes` $\to$ Look up the `Pass/Fail` range in `Phase2_Matrix` for the assigned **Sector Profile**.
2. **Comparison:**
   - Apply the `Operator` (e.g., $\text{Metric} > \text{Threshold}$) to the data point.
3. **Status Assignment:**
   - If value breaches Fail $\to$ `FAIL`.
   - If value is between Pass and Fail $\to$ `CONCERN`.
   - If value meets Pass $\to$ `PASS`.

### Step 4: Verdict Aggregation
The engine applies the decision rules:
- **Phase 1:** Binary logic (Any `FAIL` $\to$ `REJECT`).
- **Phase 2:** Cumulative logic (Check `FAIL`s $\to$ Count `CONCERN`s $\to$ Check `INCONCLUSIVE`).

---

## 3. User Interface & Experience (UX)

The tool will provide a simple "Upload & Execute" interface:
1. **Upload Config:** `[Select Rules_Config.xlsx]` $\to$ Tool confirms "Thresholds loaded for 18 checks."
2. **Upload Data:** `[Select Stock_Data.xlsx]` $\to$ Tool confirms "Data loaded for TICKER: XYZ."
3. **Run Engine:** `[Execute Analysis]` $\to$ Tool generates the Internal Technical Table and the Investor-facing Narrative.
4. **Iterate:** If the user feels the RoCE floor for "Regulated" businesses is too low, they edit the Excel sheet, re-upload, and run the analysis again in seconds.

---

## 4. Implementation Roadmap

| Phase | Task | Deliverable |
| :--- | :--- | :--- |
| **1. Design** | Finalise the exact column names for the Excel templates. | `Excel_Templates.xlsx` |
| **2. Core Engine** | Build the Python logic to load Excel and perform the dynamic lookup. | `rule_engine.py` |
| **3. Integration** | Link the Scraper output to the `Stock_Data` format. | Data Connector |
| **4. Reporting** | Connect the Engine output to the `user.md` narrative generator. | Narrative Module |
| **5. Testing** | Run 5 diverse stocks through the engine with 3 different Config versions. | Test Report |

## 5. Definition of Done (Rule Engine)
- [ ] User can change a threshold in Excel and see the verdict change without touching code.
- [ ] Sector-based thresholds are applied correctly based on the mapping sheet.
- [ ] Both Phase 1 and Phase 2 are executed in a single run.
- [ ] The output includes a "Thresholds Used" section (e.g., "RoCE judged against 12% floor for Cap-Intensive sector").
