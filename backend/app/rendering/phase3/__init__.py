"""
Phase 3 Rendering Package (Analyst Working Table and Investor Plain English Report).
"""

from .analyst_table import render_phase3_analyst_table
from .investor_prose import render_phase3_investor_report

__all__ = [
    "render_phase3_analyst_table",
    "render_phase3_investor_report",
]
