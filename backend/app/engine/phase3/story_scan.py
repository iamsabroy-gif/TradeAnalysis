"""
Story Contradiction Scan for Phase 3 Gatekeeper (Check C / Sections B, C, D, H, J).
Strictly maps to Docs/Rules/Phase3-Rules.md §2 Check C and Docs/Rules/Phase3-Algorithms.md §2 Step 4.
All thresholds are now driven by Phase3RuleConfig from the central Rule Engine.
"""

from typing import List, Optional

from backend.app.models.enums import StoryContradictionType
from backend.app.models.phase3_schemas import (
    CompanyPhase3Input,
    StoryContradictionItem,
    StoryScanAnalysis,
)
from backend.app.engine.rules.config import Phase3RuleConfig


def scan_contradictions(
    input_data: CompanyPhase3Input,
    config: Optional[Phase3RuleConfig] = None,
) -> StoryScanAnalysis:
    """
    Executes boolean tests for the Four Great Contradictions across narrative sections:
    1. Expansion Lie: High growth guidance without supporting growth capex.
    2. Vendor Risk: Claimed high moat, but heavy single-source or outsourced dependency.
    3. Guidance Gap: Guidance missed for N or more consecutive years (configurable).
    4. Tone Shift: Defensive management tone and/or falling margins despite aggressive guidance.

    All numeric thresholds are sourced from `config` (Phase3RuleConfig).
    If no config is provided, uses the active registry config.
    """
    if config is None:
        from backend.app.engine.rules.registry import get_active_rules_config
        config = get_active_rules_config().phase3

    items: List[StoryContradictionItem] = []

    # ----------------------------------------------------
    # Contradiction 1: The Expansion Lie (Sections B & C)
    # ----------------------------------------------------
    c1_triggered = False
    c1_detail = "Capex spending is consistent with stated growth targets."
    if input_data.section_c_high_growth_guidance:
        spent = input_data.section_b_capex_spent_cr
        maint = input_data.section_b_maintenance_capex_cr
        if spent is not None and maint is not None and spent <= maint:
            c1_triggered = True
            c1_detail = (
                f"Management guides aggressive expansion, but actual capex spent (₹{spent:.1f} Cr) "
                f"is at or below maintenance capex level (₹{maint:.1f} Cr). Stalled growth investment."
            )
        elif spent is None and maint is None:
            c1_detail = "Capex breakdown not fully reported; growth guidance noted."

    items.append(
        StoryContradictionItem(
            contradiction_type=StoryContradictionType.EXPANSION_LIE,
            title="The Expansion Lie",
            section_source="Sections B & C (Evolution & Expansion)",
            triggered=c1_triggered,
            detail=c1_detail,
        )
    )

    # ----------------------------------------------------
    # Contradiction 2: The Vendor Risk (Sections G & H)
    # Thresholds from config: single_source_dependency_ceiling_pct, outsourcing_ceiling_pct
    # ----------------------------------------------------
    c2_triggered = False
    c2_detail = "Moat corroborated with balanced supply chain and in-house control."
    if input_data.section_g_claimed_high_moat:
        single_source = input_data.section_h_single_source_dependency_pct or 0.0
        outsourcing = input_data.section_h_outsourcing_pct or 0.0
        ss_ceiling = config.single_source_dependency_ceiling_pct
        os_ceiling = config.outsourcing_ceiling_pct
        if single_source > ss_ceiling or outsourcing > os_ceiling:
            c2_triggered = True
            c2_detail = (
                f"Management claims proprietary moat, but vendor dependency is acute: "
                f"single-source dependency is {single_source:.1f}% (>{ss_ceiling:.0f}% ceiling) "
                f"or product outsourcing is {outsourcing:.1f}% (>{os_ceiling:.0f}% ceiling)."
            )

    items.append(
        StoryContradictionItem(
            contradiction_type=StoryContradictionType.VENDOR_RISK,
            title="The Vendor Risk",
            section_source="Sections G & H (Moat & Supply Chain)",
            triggered=c2_triggered,
            detail=c2_detail,
        )
    )

    # ----------------------------------------------------
    # Contradiction 3: The Guidance Gap (Section J)
    # Threshold from config: guidance_miss_fatal_years
    # ----------------------------------------------------
    missed_years = input_data.section_j_guidance_missed_consecutive_years
    fatal_years = config.guidance_miss_fatal_years
    c3_triggered = missed_years >= fatal_years
    if c3_triggered:
        c3_detail = (
            f"Management has missed stated revenue/margin guidance for {missed_years} consecutive years. "
            f"Promises of 'next year is the inflection year' are discredited by actual execution."
        )
    else:
        c3_detail = (
            f"Guidance track record within acceptable limits "
            f"({missed_years} consecutive misses < {fatal_years}-year fatal cap)."
        )

    items.append(
        StoryContradictionItem(
            contradiction_type=StoryContradictionType.GUIDANCE_GAP,
            title="The Guidance Gap",
            section_source="Section J (Guidance & Track Record)",
            triggered=c3_triggered,
            detail=c3_detail,
        )
    )

    # ----------------------------------------------------
    # Contradiction 4: The Tone Shift (Sections D & C)
    # ----------------------------------------------------
    c4_triggered = False
    c4_detail = "Concall tone, margins, and guidance are mutually corroborating."
    if input_data.section_c_high_growth_guidance and (
        input_data.section_d_management_tone_defensive or input_data.section_d_margin_falling
    ):
        c4_triggered = True
        c4_detail = (
            "Tone mismatch: management projects aggressive optimism in public guidance, "
            "while concalls show a defensive tone and operational margins are actively compressing."
        )

    items.append(
        StoryContradictionItem(
            contradiction_type=StoryContradictionType.TONE_SHIFT,
            title="The Tone Shift",
            section_source="Sections D & C (Management Conduct & Guidance)",
            triggered=c4_triggered,
            detail=c4_detail,
        )
    )

    # Aggregate result — use config's contradiction_fatal_list to determine fatality
    fatal_list = [s.upper() for s in config.contradiction_fatal_list]
    has_fatal = any(
        item.triggered and item.contradiction_type.value in fatal_list
        for item in items
    )

    if has_fatal:
        triggered_names = [
            item.title for item in items
            if item.triggered and item.contradiction_type.value in fatal_list
        ]
        summary = f"Fatal story contradiction detected: {', '.join(triggered_names)}."
    else:
        triggered_warnings = [item.title for item in items if item.triggered]
        if triggered_warnings:
            summary = (
                f"Non-fatal story warnings detected: {', '.join(triggered_warnings)}. "
                f"These are not in the fatal list and do not block the verdict."
            )
        else:
            summary = "Story confirmed: No fatal narrative contradictions detected across B, C, D, H, and J."

    return StoryScanAnalysis(
        contradictions=items,
        has_fatal_contradiction=has_fatal,
        summary=summary,
    )

