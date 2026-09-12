"""
Investor Plain English Report Renderer for Phase 3 Gatekeeper.
Strictly maps to Docs/Rules/Phase3-Rules.md §5 and user.md communication standards.
"""

from backend.app.models.enums import Phase3Verdict
from backend.app.models.phase3_schemas import Phase3Result

SEBI_DISCLAIMER = (
    "Disclaimer: This report is generated algorithmically for educational and analytical purposes only "
    "as part of an investment honesty, quality, and valuation screening framework. It does not constitute "
    "financial, investment, or legal advice under SEBI guidelines. Please consult an authorized financial "
    "advisor before committing capital."
)


def render_phase3_investor_report(result: Phase3Result) -> str:
    """
    Renders Phase 3 results in plain English, employing the 'Apartment' price tag analogy,
    plain-language return reality check, story verification, and standard disclaimers.
    """
    v = result.verdict
    val = result.valuation
    ret = result.return_path
    story = result.story_scan

    # 1. The Lead: A simple Yes / No / Wait answer
    if v == Phase3Verdict.BUY_HIGH_CONVICTION:
        lead_verdict = "YES — High Conviction Buy"
        lead_summary = (
            f"The business is proven, the price tag is honest, and management's words match their deeds. "
            f"At {val.pe_comparison.current:.1f}x earnings, you are not overpaying for quality."
        )
    elif v == Phase3Verdict.BUY_SPECULATIVE:
        lead_verdict = "YES (SPECULATIVE) — Quality Business at a Premium Price"
        lead_summary = (
            f"The company is excellent and the story is verified, but the stock trades at a premium "
            f"({val.pe_comparison.current:.1f}x earnings). Returns depend on flawless operational execution."
        )
    elif v == Phase3Verdict.HOLD_FAIR_VALUE:
        lead_verdict = "WAIT — Fairly Priced, No Margin of Safety"
        lead_summary = (
            f"This is a great company, but it is priced exactly at what it is worth today. "
            f"There is no bargain here to guarantee your 20% return hurdle without taking undue risk."
        )
    elif v == Phase3Verdict.AVOID_OVERVALUED:
        lead_verdict = "NO — The Quality Trap (Overvalued)"
        lead_summary = (
            f"The company is respectable, but the current price is a fantasy. To earn a 20% return from here, "
            f"the company would have to grow faster than practically any peer in its history. We avoid it."
        )
    else:  # AVOID_STORY_CONTRADICTION
        lead_verdict = "NO — The Story Trap (Contradictions Detected)"
        lead_summary = (
            f"Even if the stock looks cheap on paper, the management narrative contradicts reality. "
            f"We found critical contradictions between what leadership promises and what the balance sheet shows."
        )

    # 2. The Layman's Breakdown
    # The Price Tag: Apartment Analogy
    pe = val.pe_comparison.current
    pe_hist = val.pe_comparison.hist_5y_avg
    pe_peer = val.pe_comparison.peer_avg

    if pe <= pe_hist and pe <= pe_peer:
        price_analogy = (
            f"Imagine a beautiful flat in a prime locality where similar flats sell for ₹{pe_peer:.0f} Lakh "
            f"and has historically commanded ₹{pe_hist:.0f} Lakh. Today, the owner is offering it to you "
            f"for ₹{pe:.0f} Lakh. That is a fair, reasonable deal with built-in cushion."
        )
    elif pe > pe_hist and pe > pe_peer:
        price_analogy = (
            f"Imagine a flat where similar homes in the same building sell for ₹{pe_peer:.0f} Lakh, "
            f"but the seller is demanding ₹{pe:.0f} Lakh. The flat is wonderful, but the asking price only "
            f"makes sense if gold is discovered beneath the floorboards tomorrow. You are taking all the risk."
        )
    else:
        price_analogy = (
            f"Imagine a flat listed at ₹{pe:.0f} Lakh. That sounds cheaper than the neighbouring tower "
            f"(₹{pe_peer:.0f} Lakh), but it is much higher than what homes in this exact building have ever sold "
            f"for in the last 5 years (₹{pe_hist:.0f} Lakh). You need to be cautious of a potential value trap."
        )

    # The Return Path
    return_explanation = (
        f"For you to make a 20% yearly profit over the next 3 years, this company needs to grow its profits "
        f"by at least **{ret.required_eps_growth_pct:.1f}% each year**. "
        f"Over the last 5 years, it actually grew at **{ret.historical_eps_growth_pct:.1f}% per year**. "
        f"{ret.verdict_statement}"
    )

    # The Story Check
    if story.has_fatal_contradiction:
        triggered_items = [c for c in story.contradictions if c.triggered]
        story_details = " ".join(f"• **{item.title}**: {item.detail}" for item in triggered_items)
        story_explanation = (
            f"We cross-checked management's public statements against their financial statements: "
            f"\n\n{story_details}\n\n"
            f"When management promises aggressive expansion but refuses to spend capital, or claims a moat "
            f"while outsourcing everything, we do not partner with them."
        )
    else:
        story_explanation = (
            "We checked management's statements across Annual Reports and concalls. Stated capacity expansion "
            "matches their actual factory spending, guidance has been respected, and their supply chain is resilient. "
            "The story checks out."
        )

    sections = [
        f"# Investment Reality Check: {result.company_name} ({result.ticker})",
        "",
        f"## The Decision: **{lead_verdict}**",
        f"> {lead_summary}",
        "",
        "---",
        "",
        "### 1. The Price Tag (Are You Paying Too Much?)",
        price_analogy,
        "",
        "### 2. The Return Reality (Can You Actually Make 20% a Year?)",
        return_explanation,
        "",
        "### 3. The Story Check (Do Actions Match Words?)",
        story_explanation,
        "",
        "---",
        "",
        f"*{SEBI_DISCLAIMER}*",
    ]

    return "\n".join(sections)
