"""
Section-anchor library for Phase 1 Gatekeeper Annual Report PDFs.
Maps strictly to Phase1-WebApp-Implementation-Plan.md §5.5.
Provides section header patterns and fuzzy text matching for Annual Report notes and reports.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple


SECTION_PATTERNS: Dict[str, List[str]] = {
    "auditor_opinion": [
        "INDEPENDENT AUDITOR'S REPORT",
        "INDEPENDENT AUDITORS' REPORT",
        "INDEPENDENT AUDITOR’S REPORT",
        "REPORT ON THE AUDIT OF THE CONSOLIDATED FINANCIAL STATEMENTS",
        "REPORT ON THE AUDIT OF THE STANDALONE FINANCIAL STATEMENTS",
        "Opinion",
        "Basis for Opinion",
    ],
    "emphasis_of_matter": [
        "Emphasis of Matter",
        "Emphasis of Matters",
        "Material Uncertainty Related to Going Concern",
    ],
    "related_party": [
        "Related Party Transactions",
        "Related Party Disclosures",
        "Related Parties",
    ],
    "contingent_liabilities": [
        "Contingent Liabilities",
        "Contingent Liabilities and Commitments",
        "Contingent Liabilities & Commitments",
        "Contingent liabilities not provided for",
    ],
    "auditor_remuneration": [
        "Payment to Auditors",
        "Payment to Auditor",
        "Auditor's Remuneration",
        "Auditors' Remuneration",
        "Remuneration to Auditors",
        "Remuneration to Auditor",
    ],
    "legal_professional_charges": [
        "Legal and Professional",
        "Legal & Professional",
        "Legal and Professional Charges",
        "Legal and Professional Fees",
        "Legal expenses",
    ],
    "kmp_changes": [
        "Key Managerial Personnel",
        "Changes in Key Managerial Personnel",
        "Directors and Key Managerial Personnel",
    ],
    "balance_sheet_equity": [
        "Balance Sheet",
        "Consolidated Balance Sheet",
        "Standalone Balance Sheet",
        "Total Equity",
        "Shareholders' Funds",
        "Equity and Liabilities",
        "Total equity attributable to owners",
    ],
    "revenue_from_operations": [
        "Statement of Profit and Loss",
        "Consolidated Statement of Profit and Loss",
        "Standalone Statement of Profit and Loss",
        "Revenue from Operations",
        "Revenue from operations",
        "Total Income",
    ],
    "restatement": [
        "Restatement",
        "Prior Period Errors",
        "Restated",
        "Correction of Prior Period",
        "Restatement of financial statements",
    ],
    "report_fiscal_year": [
        r"Annual Report 20(\d{2})",
        r"for the year ended (?:31st |31 )?March,? 20(\d{2})",
        r"Financial Year 20(\d{2})",
        r"20(\d{2})–20\d{2}",
    ],
}


def fuzzy_similarity(a: str, b: str) -> float:
    """Computes similarity ratio between two normalized strings."""
    norm_a = re.sub(r"\s+", " ", a.strip().lower())
    norm_b = re.sub(r"\s+", " ", b.strip().lower())
    return SequenceMatcher(None, norm_a, norm_b).ratio()


def matches_anchor(text: str, patterns: List[str], threshold: float = 0.8) -> Tuple[bool, float, Optional[str]]:
    """
    Checks if text matches any anchor pattern exactly (case-insensitive substring)
    or via fuzzy ratio above threshold.
    Returns (matched, score, pattern_matched).
    """
    clean_text = re.sub(r"\s+", " ", text.strip().lower())
    for pat in patterns:
        clean_pat = re.sub(r"\s+", " ", pat.strip().lower())
        if clean_pat in clean_text:
            return True, 1.0, pat
        score = fuzzy_similarity(clean_text, clean_pat)
        if score >= threshold:
            return True, score, pat
    return False, 0.0, None


def detect_fiscal_year_from_text(text: str) -> Optional[str]:
    """
    Detects fiscal year (e.g. 'FY24') from title/cover text.
    """
    # e.g. "Annual Report 2023-24" or "Annual Report 2024" or "for the year ended March 31, 2024"
    m = re.search(r"Annual Report\s+20\d{2}[-–](20)?(\d{2})", text, re.IGNORECASE)
    if m:
        return f"FY{m.group(2)}"

    m = re.search(r"Annual Report\s+20(\d{2})", text, re.IGNORECASE)
    if m:
        return f"FY{m.group(1)}"

    m = re.search(r"(?:year ended|31st March|31 March)[,\s]+20(\d{2})", text, re.IGNORECASE)
    if m:
        return f"FY{m.group(1)}"

    m = re.search(r"FY\s*20?(\d{2})", text, re.IGNORECASE)
    if m:
        return f"FY{m.group(1)}"

    return None
