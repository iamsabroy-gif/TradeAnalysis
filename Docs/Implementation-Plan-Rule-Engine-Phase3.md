# Implementation Plan: Rule Engine Expansion for Phase 3

This document outlines the technical roadmap for migrating the Phase 3 (Valuation & Story Confirmation) logic from hardcoded execution files into the central, user-configurable Rule Engine.

## 1. Objective
To decouple Phase 3 decisioning logic from the codebase, allowing users to modify valuation benchmarks, return-path probabilities, and story contradiction weights via configuration (Excel/API) without requiring code changes.

---

## 2. Technical Architecture Changes

### 2.1 Configuration Schema (`backend/app/engine/rules/config.py`)
The central configuration must be expanded to include the specific variables that drive Phase 3 decisions.

**New Data Models to implement:**

- **`Phase3RuleConfig`**:
    - `target_cagr`: float (Default: 20.0)
    - `growth_prob_multiplier`: float (Default: 1.5) — *The threshold for "Miraculous" growth vs historical average.*
    - `valuation_fair_variance_pct`: float (Default: 10.0) — *Allowed variance from 5-yr avg to be considered "Fair".*
    - `contradiction_fatal_list`: List[str] — *Which story contradictions (e.g., "Guidance Gap") trigger an immediate `AVOID`.*

- **`Phase3DecisionMatrix`**:
    - A lookup table mapping `(StoryContradiction: bool, ReturnPath: Probable|Aggressive|Miraculous, Valuation: Fair|Expensive)` $\to$ `Verdict`.

- **`RulesConfiguration` Update**:
    - Add `phase3: Phase3RuleConfig` to the master container.

### 2.2 Logic Decoupling (The Engine)
Move logic from "fixed code" to "config-referenced code."

| Module | Hardcoded Logic (Current) | Config-Driven Logic (Target) |
| :--- | :--- | :--- |
| **`valuation.py`** | Fixed comparison vs Peer/History. | Use `valuation_fair_variance_pct` from config to determine `Fair` vs `Expensive`. |
| **`return_path.py`** | Fixed $1.5\times$ growth for "Miraculous". | Use `growth_prob_multiplier` to map historical growth $\to$ probability. |
| **`story_scan.py`** | Fixed boolean "The Great Contradictions". | Reference `contradiction_fatal_list` to decide if a contradiction is a `Warning` or a `Fatal Fail`. |
| **`orchestrator.py`** | Hardcoded `if/else` verdict matrix. | Implement a lookup function using the `Phase3DecisionMatrix` config. |

---

## 3. Execution Roadmap

### Step 1: Schema Update (Infrastructure)
- [ ] Define `Phase3RuleConfig` and `Phase3DecisionMatrix` in `config.py`.
- [ ] Update `create_default_rules_configuration()` to include standard Phase 3 defaults.
- [ ] Expand `MasterRuleDefinition` list to include Phase 3 checks (Valuation, Return Path, Narrative Sections B, C, D, H, J).

### Step 2: Engine Refactoring (Logic)
- [ ] **Refactor `return_path.py`**: Replace hardcoded probability thresholds with config variables.
- [ ] **Refactor `valuation.py`**: Implement the variance-based "Fair/Expensive" logic via config.
- [ ] **Refactor `story_scan.py`**: Map contradiction results to the `contradiction_fatal_list`.
- [ ] **Refactor `orchestrator.py`**: Replace the final decision `if/else` block with a matrix lookup.

### Step 3: User Control Interface (IO)
- [ ] **Update `excel_io.py`**: Add support for reading/writing Phase 3 thresholds in the configuration spreadsheet.
- [ ] **API Validation**: Verify that updating the `RulesConfiguration` via API correctly changes the final verdict of a processed stock.

### Step 4: Validation & Testing
- [ ] **Regression Testing**: Ensure Phase 1 and 2 verdicts remain unchanged.
- [ ] **Edge Case Testing**: Verify that a "Story Contradiction" correctly overrides a "Fair Price" as per the algorithm.
- [ ] **Config Testing**: Change a threshold in the config and verify the verdict changes for the same stock.

---

## 4. Success Criteria
1. **Zero Hardcoded Thresholds**: No numeric limits (like "20%" or "1.5x") exist in the Phase 3 `.py` files.
2. **User Modifiability**: A user can change the Target CAGR from 20% to 15% in a config file and see the "Return Path" update from "Miraculous" to "Probable."
3. **Matrix Flexibility**: The user can redefine that a "Miraculous" return path is acceptable if the "Story" is perfectly confirmed.
