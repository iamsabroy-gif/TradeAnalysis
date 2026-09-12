# Phase 3 Gatekeeper Rules — The Valuation & Story Confirmation

*Operating instructions for the final stage of analysis: determining if a "good business" is available at a "fair price" and if the management's story holds up under scrutiny. Phase 1 asked "is it honest?", Phase 2 asked "is it good?", Phase 3 asks "is it a bargain and is the story believable?"*

**Entry condition:** a stock may only enter Phase 3 with a Phase 2 verdict of `CLEARED TO PHASE 3`.

**Source checklist:** this screen operationalises the final remaining pieces of the `Stock - Analysis - Question - Set.md`:
- **The Hard Numbers:** Section E (Q21) and Section I (Q40).
- **The Story Confirmation:** Sections B (Q7–10), C (Q11–14), D (Q15–17), H (Q32–39), and J (Q41–42).

**Communication rules:** every investor-facing verdict must be written through `user.md` — plain English, analogies for technical terms, and the final "So what does this mean for me" summary.

---

## 0. Core principle

Phase 3 is the **Reality Check**. It prevents the two most common investor mistakes:
1. **Buying a great company at a terrible price** (The "Quality Trap").
2. **Believing a beautiful story that the numbers don't support** (The "Story Trap").

We don't just look at a P/E ratio; we calculate exactly what has to happen in the real world for the investor to make money. If the requirements for a 20% return are "miraculous" rather than "probable," we walk away regardless of how "good" the business is.

---

## 1. Inputs (what to gather)

| Section | Focus | Data to pull | Preferred source |
| :-- | :-- | :-- | :-- |
| **Section E** | Valuation | Current P/E, P/B, EV/EBITDA vs. 5-yr average and vs. 3-5 key peers. | Screener.in / Peer filings |
| **Section I** | Return Path | Required EPS growth, P/E change, and Dividend yield to hit 20% CAGR. | Calculated based on current price |
| **Section B** | Evolution | 3-yr revenue mix shift, capex actually spent vs. planned, major wins/losses. | Annual Reports (MD&A) |
| **Section C** | Expansion | Specific capacity dates, funding source, quantified targets (revenue/margin). | Annual Reports / Investor Presentations |
| **Section D** | Management | Concall priorities, tone shifts, capital allocation (dividends/buybacks). | Concall transcripts / MD&A |
| **Section H** | Vendors | % in-house vs. outsourced, single-source dependencies, related-party vendors. | AR Notes (Expenditure/RPT) |
| **Section J** | Track Record | Past 3 years of management guidance vs. actual results. | Prior ARs vs. Current ARs |

---

## 2. The Reality Checks (Logic)

Unlike Phase 1 and 2, Phase 3 uses a **Confirmation Model**. We look for "Contradictions."

### Check A — The Valuation Gap (Section E, Q21)
- **FAIR:** Trading at or below its 5-yr average P/E **AND** at or below the peer average.
- **EXPENSIVE:** Trading significantly above both its own history and peers without a massive jump in growth.
- **CONCERN:** Cheap relative to peers but expensive relative to its own history (potential value trap).

### Check B — The 20% Return Path (Section I, Q40)
We calculate: *What must be true for me to make 20% a year for the next 3 years?*
- **PROBABLE:** Requires growth rates slightly above or equal to the company's 5-yr average.
- **AGGRESSIVE:** Requires growth rates 1.5x–2x higher than historical averages, or a significant P/E re-rating (price increase).
- **MIRACULOUS:** Requires growth that is impossible given the market size, or a P/E re-rating that hasn't happened in the sector for decades.

### Check C — The Story Confirmation (Sections B, C, D, H, J)
We look for **The Great Contradiction**. A contradiction occurs if:
1. **The Expansion Lie:** Management guides huge growth (Section C) but capex spending has stalled (Section B).
2. **The Vendor Risk:** Management claims a "deep moat" (Section G) but 80% of the product is outsourced to a single vendor (Section H).
3. **The Guidance Gap:** Management consistently promises "next year is the year" but has missed targets for 3 straight years (Section J).
4. **The Tone Shift:** The tone in concalls has moved from "confident" to "defensive" while margins are falling (Section D).

---

## 3. Decision Rule (The Final Verdict)

1. **BUY - HIGH CONVICTION:** Valuation is Fair/Cheap $\to$ Return Path is Probable $\to$ No Story Contradictions.
2. **BUY - SPECULATIVE:** Valuation is Fair/Expensive $\to$ Return Path is Aggressive but possible $\to$ No Story Contradictions.
3. **HOLD - FAIR VALUE:** Business is great, but the price is exactly what it's worth. No room for a 20% return without a miracle.
4. **AVOID - OVERVALUED:** Return Path is Miraculous. The "Quality Trap."
5. **AVOID - STORY CONTRADICTION:** Even if the price is cheap, a major contradiction (e.g., guidance gap or vendor risk) makes the business untrustworthy.

---

## 4. Internal Working Table

```
# Phase 3 — <Company Name> (<TICKER>)
**Current Price:** <Price>   **Market Cap:** <Cap>

## FINAL VERDICT: <BUY-HIGH | BUY-SPEC | HOLD | AVOID-PRICE | AVOID-STORY>

### 1. The Numbers (Valuation & Returns)
| Metric | Current | Peer Avg | 5-Yr Avg | Status (Fair/Exp) |
| :-- | :-- | :-- | :-- | :-- |
| P/E | | | | |
| EV/EBITDA | | | | |

**The 20% Return Path:**
- Required Earnings Growth: <X>% (Historical: <Y>%) $\to$ <Probable/Aggressive/Miraculous>
- Required P/E Change: <X>% $\to$ <Probable/Aggressive/Miraculous>
- Verdict: <The math is reasonable / The math is a fantasy>

### 2. The Story (Confirmation)
| Section | Finding | Verdict (Confirmed/Contradicted) |
| :-- | :-- | :-- |
| Evolution (B) | | |
| Expansion (C) | | |
| Management (D) | | |
| Vendors (H) | | |
| Guidance (J) | | |

## Why the verdict
- <Explain the link between the price and the required growth>
- <Highlight the specific story confirmation or contradiction>
```

---

## 5. Investor-Facing Output (via `user.md`)

**The lead:** A simple "Yes/No/Wait" answer.
- *Example:* "The business is fantastic, but the price is currently a 'fantasy.' To make a 20% return from here, the company would need to grow faster than the entire industry combined. We avoid it for now."

**The Layman's Breakdown:**
- **The Price Tag:** Use the "Apartment" analogy. "The apartment is beautiful, but the seller is asking for a price that only makes sense if the neighborhood becomes the most expensive in the city overnight."
- **The Return Path:** "For you to make your target profit, this company needs to earn <X> amount. Looking at the last 5 years, they usually earn <Y>. Is it possible? Yes. Is it likely? <Answer>."
- **The Story Check:** "We checked if the management's promises match their actions. We found that while they say they are expanding, they haven't actually spent any money on new factories in two years. This is a red flag."

**Closing:** The standard SEBI disclaimer from `user.md`.

---

## 6. Guardrails

1. **No "Average" Returns:** We don't settle for "maybe it goes up." We test specifically for the 20% CAGR goal.
2. **Narrative doesn't override Math:** A "great story" cannot fix a "miraculous" return requirement.
3. **Contradictions are Fatal:** A single major story contradiction (e.g., Guidance Gap) can trigger an AVOID even if the P/E is low.
4. **Price is the final filter:** Remember, a great company is a bad investment if you pay too much.

---

## 7. Definition of Done

- [ ] Current valuation compared to peers and history.
- [ ] Return-requirement math completed (Growth vs. History).
- [ ] All narrative sections (B, C, D, H, J) screened for contradictions.
- [ ] Final Verdict reached (High Conviction / Speculative / Hold / Avoid).
- [ ] Output translated via `user.md` into plain English.
