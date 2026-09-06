"""
Investor-facing prose renderer following Docs/user.md.
Converts Phase1Result into plain-English storytelling, analogies,
and mobile-friendly sections with the mandatory SEBI disclaimer.
"""

from typing import Any, Dict, List
from backend.app.models.enums import CheckStatus, ReportingBasis, Verdict
from backend.app.models.schemas import CheckResult, Phase1Result

# Strictly locked verbatim constant from Docs/user.md §9 and Phase1-Algorithms.md §10
VERBATIM_SEBI_DISCLAIMER = (
    "This is educational analysis only, not personalised investment advice. "
    "Please consult a SEBI-registered investment adviser before making any investment decisions."
)

CHECK_METADATA = {
    1: {
        "title": "Check 1: The Auditor & Regulator Check",
        "analogy": "Think of this as checking if the accountant caught the company cooking the books, or if the police had to knock on their door.",
        "so_what_pass": "For you as an investor, this means independent watchdogs haven't found red flags in how the books are kept.",
        "so_what_fail": "For you as an investor, a failed audit or regulatory penalty is a massive red flag. We walk away immediately.",
        "so_what_inconclusive": "For you as an investor, we cannot yet confirm if the company's financial reporting is completely trustworthy.",
    },
    2: {
        "title": "Check 2: The Owner's Pledge Check",
        "analogy": "Pledging shares is like taking a home loan using your house deed as security. If the company's promoters borrow heavily against their stock and stock prices drop, lenders can sell their shares, triggering a collapse.",
        "so_what_pass": "For you as an investor, the founders are not putting their ownership at risk to borrow personal funds.",
        "so_what_fail": "For you as an investor, high promoter pledge creates high risk of sudden stock price crash if loans default.",
        "so_what_inconclusive": "For you as an investor, we don't have enough clear shareholding data to verify if promoter shares are safe.",
    },
    3: {
        "title": "Check 3: The Related-Party 'Pocket-Transfer' Check",
        "analogy": "Imagine a shopkeeper selling goods to his brother's company at an artificial discount. Related-party transactions check if company cash is leaking into the promoters' private businesses.",
        "so_what_pass": "For you as an investor, money isn't quietly being routed out of the public company into private side-businesses.",
        "so_what_fail": "For you as an investor, excessive business with sister companies suggests profits could be artificially inflated or drained.",
        "so_what_inconclusive": "For you as an investor, we need to inspect the related-party disclosures before giving this an honest score.",
    },
    4: {
        "title": "Check 4: The Hidden Landmines (Contingent Liabilities) Check",
        "analogy": "A contingent liability is like a pending lawsuit or tax dispute: you haven't paid it yet, but if you lose in court, you have to write a huge cheque.",
        "so_what_pass": "For you as an investor, possible future legal or tax bills are small enough that they won't blow a hole in the company.",
        "so_what_fail": "For you as an investor, pending claims are dangerously high compared to the company's total net worth.",
        "so_what_inconclusive": "For you as an investor, we couldn't match or locate the contingent liabilities vs net worth statements.",
    },
    5: {
        "title": "Check 5: Show Me the Real Cash Check",
        "analogy": "Net profit on paper is just accounting. Operating cash flow (CFO) is real money arriving in the bank account. If profit is high but bank balance never rises, the profit is imaginary.",
        "so_what_pass": "For you as an investor, the company turns its accounting profits into real cold hard cash in the bank.",
        "so_what_fail": "For you as an investor, paper profits are not turning into real bank balances. This is a classic hallmark of aggressive accounting.",
        "so_what_inconclusive": "For you as an investor, we need full 5-year cash records to verify consistent cash generation.",
    },
    6: {
        "title": "Check 6: The Captain & Crew Stability Check",
        "analogy": "If a ship replaces its Chief Financial Officer (the person who guards the money) multiple times in three years, or rewrites past logbooks, something is wrong inside the engine room.",
        "so_what_pass": "For you as an investor, leadership is steady and past financial accounts haven't needed retroactive corrections.",
        "so_what_fail": "For you as an investor, frequent CFO departures or restated accounts usually precede deeper accounting scandals.",
        "so_what_inconclusive": "For you as an investor, executive transition records for the full 3-year window are missing or incomplete.",
    },
}


def render_investor_report(result: Phase1Result) -> Dict[str, Any]:
    """
    Renders an investor-friendly view following Docs/user.md principles.
    """
    # 1. Plain English headline verdict
    if result.verdict == Verdict.CLEARED_TO_PHASE_2:
        badge_label = "CLEARED TO PHASE 2"
        badge_color = "success"
        headline = (
            f"{result.ticker} passed the honesty check — safe to look deeper."
        )
        lead_story = (
            f"Before investing a single rupee, we checked if {result.ticker} plays by the rules. "
            f"All six Phase 1 integrity checks were cleared. The owners are not heavily mortgaging their stock, "
            f"profits are turning into actual bank cash, and independent auditors have given a clean report."
        )
    elif result.verdict == Verdict.REJECT:
        badge_label = "REJECT (PHASE 1)"
        badge_color = "danger"
        headline = (
            f"{result.ticker} failed the honesty check — stop here, do not invest."
        )
        lead_story = (
            f"Our Phase 1 background check detected serious integrity or financial red flags with {result.ticker}. "
            f"When a company fails these basic safety gates, we do not try to guess whether the stock is cheap or expensive — "
            f"the framework rejects it immediately to protect your hard-earned capital."
        )
    else:
        badge_label = "HOLD — INCONCLUSIVE"
        badge_color = "warning"
        headline = (
            f"{result.ticker} analysis is inconclusive — missing or unverified data, do not invest yet."
        )
        lead_story = (
            f"We could not verify all six required checks for {result.ticker} with complete certainty. "
            f"Per our golden rule, when critical numbers are missing or span mismatched reporting periods, "
            f"we never guess or assume safety. This stock is held until complete information is verified."
        )

    # 2. Check cards with plain English translation
    check_cards = []
    for c in result.checks:
        meta = CHECK_METADATA.get(c.check_id, {})
        status_label = {
            CheckStatus.PASS: "PASSED",
            CheckStatus.FAIL: "FAILED",
            CheckStatus.INCONCLUSIVE: "INCONCLUSIVE",
        }[c.status]

        if c.status == CheckStatus.PASS:
            so_what = meta.get("so_what_pass", "")
            status_badge = "success"
        elif c.status == CheckStatus.FAIL:
            so_what = meta.get("so_what_fail", "")
            status_badge = "danger"
        else:
            so_what = meta.get("so_what_inconclusive", "")
            status_badge = "warning"

        check_cards.append(
            {
                "check_id": c.check_id,
                "title": meta.get("title", f"Check {c.check_id}"),
                "status": c.status.value,
                "status_label": status_label,
                "status_badge": status_badge,
                "finding": c.finding,
                "analogy": meta.get("analogy", ""),
                "so_what": so_what,
                "missing_data": c.missing_data,
                "citation": c.citation,
            }
        )

    # 3. Basis explanation
    basis_str = (
        "consolidated (combining parent and all subsidiaries)"
        if result.data_basis == ReportingBasis.CONSOLIDATED
        else "standalone (parent company only)"
        if result.data_basis == ReportingBasis.STANDALONE
        else "not applicable"
    )

    return {
        "ticker": result.ticker,
        "as_of_date": result.as_of_date,
        "revision": result.revision,
        "supersedes": result.supersedes,
        "generated_at": result.generated_at,
        "data_basis_label": basis_str,
        "verdict": result.verdict.value,
        "badge_label": badge_label,
        "badge_color": badge_color,
        "headline": headline,
        "lead_story": lead_story,
        "checks": check_cards,
        "citation_gaps": result.citation_gaps,
        "sebi_disclaimer": VERBATIM_SEBI_DISCLAIMER,
    }
