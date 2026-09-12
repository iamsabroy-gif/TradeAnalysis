# User Manual: The Stock Analysis Rule Engine

Welcome to the control center of your investment screen. 

Think of this tool not as a "black box" that gives you a Yes/No answer, but as a **digital filter**. You are the one who decides how fine or coarse that filter should be. If you feel the tool is being too strict (rejecting too many good companies) or too lenient (letting mediocre companies through), you don't need a programmer to fix it—you just adjust the "knobs" in your Excel configuration files.

This manual will show you exactly how to use those knobs to customize your analysis.

---

## 1. The Big Picture: How it Works

The tool uses three Excel sheets to decide if a stock is a "Quality Business."

1. **The Master List:** Tells the tool *which* metrics to check (e.g., "Check the RoCE").
2. **The Sector Matrix:** Tells the tool *what number* is considered "good" based on the industry (e.g., "For a software company, 20% RoCE is the bar; for a power plant, 10% is enough").
3. **The Sector Map:** Tells the tool *which industry* the company belongs to (e.g., "If the company says 'SaaS', it's an Asset-Light business").

**The Workflow:**
`Upload Config` $\to$ `Upload Stock Data` $\to$ `Run Engine` $\to$ `Get Verdict`.

---

## 2. Your Three "Control Knobs" (The Excel Sheets)

### Knob 1: The Master Rule Definitions (`Master_Rule_Definitions.xlsx`)
This is the index of all 18 checks. You generally won't need to change the names here, but you can use this sheet to see exactly what the tool is looking at.

- **Check #:** The order of the test.
- **Input Metric:** The technical name of the data point (e.g., `Pledge_Pct`).
- **Sector-Aware?:** If this says **"Yes"**, the tool ignores the "Default Fail Value" and instead looks at the **Sector Matrix** (Knob 2).

### Knob 2: The Sector Boundary Matrix (`Sector_Boundary_Matrix.xlsx`)
This is where the real power lies. This is where you define "Quality" for different types of businesses.

**How to read this sheet:**
Each row is a combination of a **Sector Profile** and a **Metric**.
- **Pass Threshold:** If the company hits this number, it gets a green light (`PASS`).
- **Fail Threshold:** If the company falls below this number, it gets a red light (`FAIL`).
- **The "Middle" (Concern):** If a company is between these two numbers, the tool marks it as a `CONCERN`.

**Example: Adjusting the RoCE Floor**
Imagine you decide that in the current economy, you only want to own "Standard" manufacturing companies if they earn at least 18% RoCE.
- **Action:** Go to the `Sector_Boundary_Matrix` $\to$ find `Standard` $\to$ `RoCE` $\to$ change `Pass_Threshold` from `15%` to `18%`.
- **Result:** The tool will now be stricter. Companies earning 16% will move from `PASS` to `CONCERN`.

### Knob 3: The Sector Map (`Company_Sector_Map.xlsx`)
The tool isn't a mind-reader; it doesn't automatically know that "TCS" is "Asset-Light." It looks for keywords.

- **Industry Keyword:** Words found in the company's description (e.g., "Chemicals", "Retail", "Software").
- **Sector Profile:** The category the tool should use for thresholds.

**Action:** If you find a company is being judged by the "Wrong" rules (e.g., a specialized tech firm being judged as "Standard Manufacturing"), simply add its keyword to this sheet and map it to "Asset-Light."

---

## 3. Layman's Glossary: What am I actually checking?

If you are reviewing the definition file and see a technical term, here is what it means in plain English:

| Term | What it actually means | Why we care |
| :-- | :-- | :-- |
| **RoCE** | For every ₹100 put into the business, how much profit does it make? | The ultimate measure of efficiency. |
| **Promoter Pledge** | Has the owner borrowed money using their shares as collateral? | High pledge = risk of the owner losing control or a share price crash. |
| **RPT Leakage** | Is the company doing too much business with the owner's other private firms? | Potential for "siphoning" money out of the public company. |
| **Contingent Liab.** | "What-if" debts (lawsuits, guarantees) that might become real. | Hidden landmines that could blow up the balance sheet. |
| **CFO / PAT** | Is the reported profit actually arriving as cash in the bank? | "Paper profits" are easy to fake; cash is hard to fake. |
| **Net Debt / EBITDA** | How many years of profit would it take to pay off all debt? | High number = the company is "over-leveraged" and risky. |
| **CCC** | How many days does it take to turn a purchase into cash from a sale? | A lengthening cycle means the business is getting "clogged." |

---

## 4. Quick Start Guide: My First Tweak

**Scenario:** You want to be more aggressive. You're okay with companies having a bit more debt if they are in the "Cap-Intensive" sector.

1. Open `Sector_Boundary_Matrix.xlsx`.
2. Find the row: `Cap-Intensive` $\to$ `NetDebt_EBITDA`.
3. Change the `Fail_Threshold` from `4.5x` to `5.5x`.
4. Save and upload the file to the tool.
5. Run your analysis. Companies that were previously `REJECTED` for leverage may now be `CLEARED` or `HOLD`.

---

## 5. Pro-Tips for the Analyst

- **Start Broad, Then Tighten:** When starting with a new sector, use the "Standard" defaults. Once you see a few companies, adjust the thresholds to fit the reality of that specific industry.
- **Watch the "Concern" Count:** Remember that while one `FAIL` is an instant reject, three `CONCERN`s also lead to a reject. If you find too many good companies are getting rejected, consider widening the gap between `Pass` and `Fail` in the Matrix.
- **Symmetry:** If you raise the `Pass` threshold, consider if you should also raise the `Fail` threshold to keep the "Concern" zone meaningful.

