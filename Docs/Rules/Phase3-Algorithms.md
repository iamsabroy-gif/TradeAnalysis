# Phase 3 Algorithm — Valuation & Story Confirmation

This document translates the verbose Phase 3 rules into a logical execution flow for agent-level implementation. It converts narrative guidelines into data-driven steps, calculations, and decision branches.

---

## 1. Execution Flow Overview

The algorithm operates as a sequential pipeline. If a "Fatal Contradiction" is found in the Story Scan, the algorithm can short-circuit to a final verdict of `AVOID-STORY`.

**Pipeline:**
`Data Acquisition` $\to$ `Valuation Analysis` $\to$ `Return Path Calculation` $\to$ `Story Contradiction Scan` $\to$ `Final Decision Matrix`

---

## 2. Step-by-Step Logic

### Step 1: Data Acquisition
**Inputs required:**
- Current Price ($P_0$)
- Current P/E, EV/EBITDA
- 5-Year Average P/E, EV/EBITDA
- Peer Average P/E, EV/EBITDA
- 5-Year Average EPS Growth Rate ($G_{hist}$)
- Current Dividend Yield ($DY$)
- Narrative data from Sections B, C, D, H, and J (Annual Reports/Concalls)

### Step 2: Valuation Analysis (`calc_valuation`)
**Logic:**
1. Compare Current P/E to 5-Yr Avg P/E and Peer Avg P/E.
2. **Assign status:**
    - `FAIR`: Current P/E $\le$ 5-Yr Avg **AND** Current P/E $\le$ Peer Avg.
    - `EXPENSIVE`: Current P/E $>$ 5-Yr Avg **AND** Current P/E $>$ Peer Avg.
    - `CONCERN`: Current P/E is cheap vs. Peers but expensive vs. History (or vice versa).

### Step 3: Return Path Calculation (`calc_return_path`)
**Goal:** Determine the required earnings growth to achieve a 20% Annualized Return over 3 years.

**Formula (Simplified):**
$Required\ Growth \approx Target\ Return\ (20\%) - Dividend\ Yield - \Delta P/E\ (Annualized)$

**Probability Mapping:**
- **PROBABLE:** Required Growth $\le$ ($G_{hist} + 2\%$).
- **AGGRESSIVE:** ($G_{hist} + 2\%$) $<$ Required Growth $\le$ ($1.5 \times G_{hist}$).
- **MIRACULOUS:** Required Growth $>$ ($1.5 \times G_{hist}$) OR requires a P/E re-rating $\ge 20\%$ per year.

### Step 4: Story Contradiction Scan (`scan_contradictions`)
**Logic:** Execute boolean checks for "The Great Contradictions."

- **Contradiction 1 (Expansion):** `(Section C: High Growth Guidance) AND (Section B: Capex Spending $\le$ Maintenance Level) = TRUE`
- **Contradiction 2 (Moat):** `(Section G: Claimed High Moat) AND (Section H: Single-Source Dependency > 50% OR Outsourcing > 70%) = TRUE`
- **Contradiction 3 (Guidance):** `(Section J: Guidance Missed $\ge$ 3 Consecutive Years) = TRUE`
- **Contradiction 4 (Management):** `(Section D: Defensive Tone/Margin Fall) AND (Section C: Aggressive Guidance) = TRUE`

**Result:** 
- If any of the above are `TRUE` $\to$ `StoryContradiction = TRUE`.
- Else $\to$ `StoryContradiction = FALSE`.

---

## 3. Final Decision Matrix

The agent shall apply the following priority-based logic to reach the final verdict:

| Story Contradiction? | Return Path Probability | Valuation Status | FINAL VERDICT |
| :--- | :--- | :--- | :--- |
| **TRUE** | Any | Any | **AVOID - STORY** |
| **FALSE** | Miraculous | Any | **AVOID - PRICE** |
| **FALSE** | Probable | Fair | **BUY - HIGH CONVICTION** |
| **FALSE** | Probable/Aggressive | Expensive | **BUY - SPECULATIVE** |
| **FALSE** | Aggressive | Fair | **HOLD - FAIR VALUE** |
| **FALSE** | Miraculous | Fair | **AVOID - PRICE** |

---

## 4. Agent Output Mapping (for `user.md`)

When the algorithm reaches a verdict, the agent must map the technical result to the following plain-English narratives:

- `AVOID-STORY` $\to$ "The story doesn't match the actions. We found a contradiction in [Section X], making the business untrustworthy."
- `AVOID-PRICE` $\to$ "The business is great, but the price is a 'fantasy.' The growth required to make a profit from here is unrealistic."
- `BUY-HIGH` $\to$ "The numbers and the story align perfectly. It's a quality business at a fair price."
- `BUY-SPEC` $\to$ "The business is quality and the story is solid, but we are paying a premium. Returns depend on aggressive growth."
- `HOLD` $\to$ "A great business, but it's currently priced exactly at its value. We wait for a better entry point."

