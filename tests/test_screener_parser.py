"""
Unit and Layout-Drift tests for Screener HTML Parser.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §7.
Zero network I/O.
"""

from pathlib import Path
import pytest

from backend.app.acquisition.adapters.parsers.screener_tables import parse_screener_html
from backend.app.acquisition.types import LayoutChangedError
from backend.app.models.enums import ReportingBasis


@pytest.fixture
def fixture_html() -> str:
    path = Path(__file__).parent / "fixtures" / "screener" / "tatamotors.html"
    return path.read_text(encoding="utf-8")


def test_screener_html_parser_normal(fixture_html):
    res = parse_screener_html(
        html_content=fixture_html,
        source_url="https://www.screener.in/company/TATAMOTORS/consolidated/",
        basis=ReportingBasis.CONSOLIDATED,
    )

    assert res.adapter == "ScreenerAdapter"
    assert len(res.errors) == 0

    field_map = {f.field_name: f for f in res.fields}

    # 1. Cash Flow 5y
    assert "cfo_last_5y" in field_map
    assert field_map["cfo_last_5y"].value == [100.0, 110.0, 120.0, 130.0, 140.0]
    assert field_map["cfo_last_5y"].basis == ReportingBasis.CONSOLIDATED

    # 2. PAT 5y
    assert "pat_last_5y" in field_map
    assert field_map["pat_last_5y"].value == [90.0, 100.0, 110.0, 120.0, 130.0]

    # 3. Revenue
    assert "revenue" in field_map
    assert field_map["revenue"].value == 1000.0

    # 4. Net worth
    assert "net_worth" in field_map
    assert field_map["net_worth"].value == 1000.0  # 200 + 800

    # 5. Shareholding
    assert "promoter_holding_pct_of_company" in field_map
    assert field_map["promoter_holding_pct_of_company"].value == 60.0
    assert "govt_shareholding_pct" in field_map
    assert field_map["govt_shareholding_pct"].value == 0.0

    # 6. Pledge
    assert "pledged_pct_of_promoter_holding" in field_map
    assert field_map["pledged_pct_of_promoter_holding"].value == 2.0
    assert "pledged_pct_history_last_4q" in field_map
    assert field_map["pledged_pct_history_last_4q"].value == [2.0, 2.0, 2.0, 2.0]

    # 7. Track record
    assert "years_of_track_record_available" in field_map
    assert field_map["years_of_track_record_available"].value == 5

    # 8. Document references
    assert len(res.documents) >= 1
    assert any("TATAMOTORS_AR_2024.pdf" in d.url for d in res.documents)


def test_layout_drift_fewer_than_4_quarters(fixture_html):
    """Mutates HTML: only 2 quarter columns in pledge row -> must raise LayoutChangedError."""
    mutated = fixture_html.replace(
        "<td>2.0%</td>\n          <td>2.0%</td>\n          <td>2.0%</td>\n          <td>2.0%</td>",
        "<td>2.0%</td>\n          <td>2.0%</td>",
    )
    with pytest.raises(LayoutChangedError, match="Pledge row expected >= 4 quarters"):
        parse_screener_html(mutated, "https://example.com", ReportingBasis.CONSOLIDATED)


def test_layout_drift_fewer_than_5_years_cfo(fixture_html):
    """Mutates HTML: only 3 years in Cash Flow -> must raise LayoutChangedError."""
    mutated = fixture_html.replace(
        "<td>100</td>\n          <td>110</td>\n          <td>120</td>\n          <td>130</td>\n          <td>140</td>",
        "<td>120</td>\n          <td>130</td>\n          <td>140</td>",
    )
    with pytest.raises(LayoutChangedError, match="Expected >= 5 fiscal years"):
        parse_screener_html(mutated, "https://example.com", ReportingBasis.CONSOLIDATED)
