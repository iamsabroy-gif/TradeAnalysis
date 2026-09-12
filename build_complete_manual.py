from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUT = Path("output/pdf/Master_Rule_Definitions_Complete_User_Manual.pdf")


def p(text, style):
    return Paragraph(text, style)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#C8D4E3"))
    canvas.line(doc.leftMargin, 0.55 * inch, letter[0] - doc.rightMargin, 0.55 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#526579"))
    canvas.drawString(doc.leftMargin, 0.36 * inch, "Master Rule Definition Sheet - User Manual")
    canvas.drawRightString(letter[0] - doc.rightMargin, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def make_table(rows, widths, styles, font_size=7.4, header=True):
    converted = []
    for idx, row in enumerate(rows):
        converted.append([
            p(str(value), styles["table_header"] if header and idx == 0 else styles["table_cell"])
            for value in row
        ])
    table = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C6D6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ]
    for row in range(1 if header else 0, len(rows)):
        if row % 2 == 0:
            commands.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor("#F4F7FA")))
    table.setStyle(TableStyle(commands))
    return table


def bullets(items, styles):
    return [p(f"<bullet>&bull;</bullet>{item}", styles["body"]) for item in items]


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=0.55 * inch, rightMargin=0.55 * inch,
        topMargin=0.58 * inch, bottomMargin=0.72 * inch,
        title="Master Rule Definition Sheet - Complete User Manual",
        author="Codex",
    )
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=23,
                                leading=28, textColor=colors.HexColor("#17365D"), alignment=TA_CENTER,
                                spaceAfter=10),
        "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontSize=10.5, leading=14,
                                   alignment=TA_CENTER, textColor=colors.HexColor("#526579"), spaceAfter=20),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=16,
                             leading=19, textColor=colors.HexColor("#17365D"), spaceBefore=6, spaceAfter=8),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12,
                             leading=15, textColor=colors.HexColor("#1F4E79"), spaceBefore=8, spaceAfter=5),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontSize=9.2, leading=12.3,
                               spaceAfter=5, textColor=colors.HexColor("#27364A")),
        "callout": ParagraphStyle("Callout", parent=base["BodyText"], fontSize=9, leading=12,
                                  leftIndent=8, rightIndent=8, borderColor=colors.HexColor("#8FAADC"),
                                  borderWidth=0.8, borderPadding=8, backColor=colors.HexColor("#EAF2F8"),
                                  spaceBefore=4, spaceAfter=8),
        "table_header": ParagraphStyle("TableHeader", parent=base["BodyText"], fontName="Helvetica-Bold",
                                       fontSize=7.4, leading=9.1, textColor=colors.white),
        "table_cell": ParagraphStyle("TableCell", parent=base["BodyText"], fontSize=7.2, leading=8.8,
                                     textColor=colors.HexColor("#27364A")),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontSize=8, leading=10.2,
                                 textColor=colors.HexColor("#526579")),
    }

    story = []
    story += [
        Spacer(1, 0.35 * inch),
        p("Master Rule Definition Sheet", styles["title"]),
        p("Complete user manual for Rule Engine Evaluation configuration", styles["subtitle"]),
        p("Purpose", styles["h1"]),
        p("This workbook supplies the rule engine with the screening logic, sector classification, and thresholds used to assess a company. It is a configuration file: change it only when you intend to change how the engine evaluates companies.", styles["body"]),
        p("This guide follows the workbook tab by tab. It explains what each sheet controls, what its fields mean, how it interacts with the other tabs, and what to check before upload.", styles["body"]),
        Spacer(1, 10),
        p("How the rule engine uses the workbook", styles["h1"]),
        make_table([
            ["Step", "What happens", "Workbook tab used"],
            ["1. Identify", "A company industry keyword is matched to a sector profile.", "Company_Sector_Map or Sector_Mapping"],
            ["2. Screen", "Phase 1 governance and accounting checks are run.", "Master_Rule_Definitions and Phase1_Thresholds"],
            ["3. Benchmark", "Operating and balance-sheet measures are compared against the matching sector thresholds.", "Sector_Boundary_Matrix or Phase2_Matrix"],
            ["4. Decide", "Valuation, return path, and contradiction logic produce the final decision.", "Master_Rule_Definitions and Phase3_Thresholds"],
        ], [0.6*inch, 3.7*inch, 2.6*inch], styles),
        Spacer(1, 10),
        p("Important workbook observation", styles["h2"]),
        p("The supplied workbook currently has two identical sector-threshold tabs (Sector_Boundary_Matrix and Phase2_Matrix) and two identical industry-mapping tabs (Company_Sector_Map and Sector_Mapping). Do not rename, remove, or assume either duplicate is unused. Confirm the upload specification with the tool owner. Until then, keep each pair synchronized when you make an approved change.", styles["callout"]),
        p("Before editing", styles["h2"]),
    ]
    story += bullets([
        "Keep every sheet name and every header exactly as supplied.",
        "Use the exact metric and parameter names shown. These act as system identifiers, not display labels.",
        "Use the existing format for thresholds such as 10.0%, 3.0x, 60 days, True, and N/A.",
        "Test an upload with a known company after any rule change, especially a sector-aware rule.",
    ], styles)

    # Tab 1
    story += [PageBreak(), p("Tab 1: Master_Rule_Definitions", styles["h1"]),
              p("This is the rule catalogue and primary control sheet. Each row declares a check that the engine can run. It links a named business check to the input metric, evaluation logic, default failure condition, and a plain-language description.", styles["body"]),
              p("Column guide", styles["h2"])]
    story.append(make_table([
        ["Column", "Meaning", "Editing guidance"],
        ["Phase", "Evaluation stage: 1 = initial integrity screen, 2 = business/financial quality, 3 = final decision.", "Use only the intended phase number."],
        ["Check #", "Unique check identifier. It connects rows to threshold detail on other tabs.", "Do not renumber existing checks."],
        ["Check Name", "Human-readable label shown in rule reporting.", "Keep concise; verify downstream display impacts before changing."],
        ["Input Metric", "Exact data field expected from the company data set.", "Treat as a fixed identifier; match case and underscores exactly."],
        ["Logic Type", "Kind of evaluation: Numeric, Categorical, Ratio, Count, Relative, Trend, or Boolean.", "Use a type supported by the engine."],
        ["Default Op", "Comparison method, such as >, <, !=, Deteriorate, Decline, or Lookup.", "Must suit both the input type and the fail value."],
        ["Default Fail Value", "Value or condition that triggers a fail when no sector-specific rule overrides it.", "Keep percentage, multiple, date/day, and Boolean formats consistent."],
        ["Sector-Aware?", "Yes tells the engine to use sector-specific thresholds where available; No uses the default setting.", "Set Yes only when a corresponding sector table entry exists."],
        ["Description", "Business explanation of the check.", "Update when logic changes so users can audit the intent."],
    ], [1.25*inch, 3.25*inch, 2.4*inch], styles))
    story += [PageBreak(), p("Master rule catalogue", styles["h1"]),
              p("The complete catalogue below is a reference view of the currently configured rules. The engine uses the exact metric key and the stated failure condition; the check name is the human-readable label.", styles["body"])]
    master_rules = [
        ["Phase", "#", "Check", "Metric", "Failure condition"],
        ["1", "1", "Auditor Integrity", "Audit_Opinion", "Not Clean"],
        ["1", "2", "Promoter Pledge", "Pledge_Pct", "> 10%, subject to detailed Phase 1 pledge rules"],
        ["1", "3", "RPT Leakage", "RPT_Revenue_Pct", "> 10%"],
        ["1", "4", "Contingent Liab", "Cont_Liab_NW_Pct", "> 15%; sector aware"],
        ["1", "5", "Cash Conversion", "CFO_PAT_Ratio", "< 0.80"],
        ["1", "6", "Exec Stability", "CFO_Changes", "> 1"],
        ["2", "7", "RoCE", "Median_RoCE", "< 10%; sector aware"],
        ["2", "8", "Margin Trend", "EBITDA_Margin_Var", "< -25%"],
        ["2", "9", "Seg Economics", "Seg_Rev_Margin_Trend", "Deteriorate"],
        ["2", "10", "Leverage", "NetDebt_EBITDA", "> 3.0x; sector aware"],
        ["2", "11", "Int Coverage", "Interest_Coverage", "< 2.0x; sector aware"],
        ["2", "12", "Maturity", "ST_Debt_Coverage", "Not True"],
        ["2", "13", "Credit Rating", "Credit_Rating", "Below BBB-"],
        ["2", "14", "Loans Given", "Loan_NW_Pct", "> 25%"],
        ["2", "15", "Guarantees", "Guar_NW_Pct", "> 50%"],
        ["2", "16", "WC Cycle", "CCC_Deterioration", "> 60 days; sector aware"],
        ["2", "17", "Moat Corrob", "Moat_Evidence_Count", "< 2"],
        ["2", "18", "Comp Position", "Market_Share_Trend", "Decline"],
        ["3", "19", "Valuation Gap", "PE_EV_EBITDA", "> 10%"],
        ["3", "20", "Return Path", "Required_EPS_Growth", "> 1.5x"],
        ["3", "21", "Story Scan", "Contradiction_Count", "Not False"],
        ["3", "22", "Decision Matrix", "Verdict_Lookup", "Lookup"],
    ]
    story.append(make_table(master_rules, [0.45*inch, 0.34*inch, 1.25*inch, 1.55*inch, 3.0*inch], styles))

    # Tab 2
    story += [PageBreak(), p("Tab 2: Sector_Boundary_Matrix", styles["h1"]),
              p("This tab defines sector-specific boundaries for metrics that vary by capital intensity or regulated business model. The engine uses it for rules marked Sector-Aware? = Yes in the master catalogue.", styles["body"]),
              p("Column guide", styles["h2"])]
    story.append(make_table([
        ["Column", "Meaning"],
        ["Sector Profile", "The sector class assigned by the industry-mapping sheet."],
        ["Metric", "Metric key used by the engine. It must match the relevant lookup logic."],
        ["Pass_Threshold", "Boundary for a pass or a stronger result. For range metrics, read the Note to determine direction."],
        ["Fail_Threshold", "Boundary at which the rule fails. It may be above or below the pass value depending on the metric."],
        ["Critical_Cap", "A hard concern boundary. N/A means no separate critical cap is supplied."],
        ["Operator", "Range means compare against pass/fail bands. > flags values above the threshold."],
        ["Unit", "Expected unit: %, x, or days."],
        ["Note", "Plain-language interpretation of the metric and threshold direction."],
    ], [1.4*inch, 5.5*inch], styles))
    story += [p("How to read the thresholds", styles["h2"]),
              p("For RoCE and Interest Coverage, stronger values are generally higher. For Net Debt/EBITDA, Cash Conversion Cycle deterioration, and receivable days, lower values are generally stronger. Always use the Note and Operator together; do not infer meaning solely from the relative size of the Pass and Fail cells.", styles["callout"]),
              p("Configured sector profiles", styles["h2"])]
    sector_rows = [
        ["Profile", "RoCE pass/fail", "Net debt/EBITDA pass/fail", "Interest coverage pass/fail", "CCC det. pass/fail/critical", "Receivable days"],
        ["ASSET_LIGHT", "20.0% / 15.0%", "1.0x / 2.0x", "6.0x / 3.0x", "30 / 30 / 60", "60 days"],
        ["STANDARD", "15.0% / 10.0%", "2.0x / 3.0x", "4.0x / 2.0x", "60 / 60 / 90", "90 days"],
        ["CAP_INTENSIVE", "12.0% / 8.0%", "3.0x / 4.5x", "3.0x / 1.5x", "90 / 90 / 120", "120 days"],
        ["REGULATED_INFRA", "10.0% / 6.0%", "4.0x / 6.0x", "2.0x / 1.0x", "120 / 120 / 150", "150 days"],
    ]
    story.append(make_table(sector_rows, [1.05*inch, 1.0*inch, 1.45*inch, 1.35*inch, 1.5*inch, 1.0*inch], styles))
    story += [Spacer(1, 8), p("Short-term debt thresholds", styles["h2"]),
              make_table([
                  ["Profile", "Max_ST_Debt_Pct", "Interpretation"],
                  ["ASSET_LIGHT", "15.0%", "A value above 15.0% is a concern."],
                  ["STANDARD", "20.0%", "A value above 20.0% is a concern."],
                  ["CAP_INTENSIVE", "15.0%", "A value above 15.0% is a concern."],
                  ["REGULATED_INFRA", "10.0%", "A value above 10.0% is a concern."],
              ], [1.5*inch, 1.4*inch, 4.45*inch], styles),
              p("Editing rule: when adding a sector-aware metric, add a row for every supported sector profile so the engine does not fall back unpredictably.", styles["small"])]

    # Tab 3
    story += [PageBreak(), p("Tab 3: Company_Sector_Map", styles["h1"]),
              p("This is the company-classification lookup. It maps an industry keyword to the sector profile that controls sector-aware benchmarks. The matching behavior - for example, exact match versus contains match and the tie-break rule - must follow the Rule Engine's upload specification.", styles["body"]),
              p("Column guide", styles["h2"])]
    story.append(make_table([
        ["Column", "Meaning", "Use it correctly"],
        ["Industry Keyword", "Industry label or phrase used to identify the company.", "Use a clear, specific phrase and avoid ambiguous overlaps where possible."],
        ["Sector Profile", "Profile the engine should assign when the keyword matches.", "Must be one of the profiles defined in the sector threshold sheet."],
        ["Notes", "Human-readable rationale or example.", "Keep this aligned with the keyword and profile."],
    ], [1.5*inch, 2.65*inch, 3.2*inch], styles))
    mapping_rows = [
        ["Sector profile", "Current industry keywords"],
        ["ASSET_LIGHT", "SaaS; IT Services; Software; FMCG Asset-Light; Platform"],
        ["STANDARD", "Auto; Auto Ancillary; General Manufacturing; Consumer Durables; Retail; Pharma Formulations; Textiles"],
        ["CAP_INTENSIVE", "Cement; Steel; Metals; Chemicals; Real Estate; Infrastructure EPC; Mining; Paper"],
        ["REGULATED_INFRA", "Power Transmission; Power Distribution; Gas Pipeline; Toll Road; Port Concession; Airport Concession"],
    ]
    story += [p("Current mapping", styles["h2"]), make_table(mapping_rows, [1.5*inch, 5.85*inch], styles),
              Spacer(1, 8), p("Safe editing practice", styles["h2"])]
    story += bullets([
        "Add a keyword only if it belongs clearly to one sector profile under the intended methodology.",
        "Do not map the same keyword to more than one profile unless the engine documents how conflicts are resolved.",
        "When adding a new sector profile here, first add its complete threshold rows in both sector-matrix tabs.",
        "Use Notes to record the intended coverage of a generic term, particularly if it could be mistaken for a different business model.",
    ], styles)

    # Tab 4
    story += [PageBreak(), p("Tab 4: Phase1_Thresholds", styles["h1"]),
              p("This tab holds the detailed Phase 1 threshold settings. It refines the initial screening checks in the master catalogue. Several rows can belong to one Check # when that check needs conditional sub-rules.", styles["body"]),
              p("Column guide", styles["h2"])]
    story.append(make_table([
        ["Column", "Meaning"],
        ["Check #", "Links the setting to the matching rule in Master_Rule_Definitions."],
        ["Metric", "Specific threshold key that the Phase 1 logic reads."],
        ["Fail_Threshold", "The point or condition that makes that sub-rule fail."],
        ["Operator", "How the input is compared to the threshold."],
        ["Sector_Aware?", "Yes means the sub-rule can use sector-specific handling; No means one common rule."],
        ["Note", "Explains the purpose of the setting."],
    ], [1.45*inch, 5.45*inch], styles))
    story += [p("Configured Phase 1 settings", styles["h2"])]
    phase1 = [
        ["Check #", "Metric", "Fail threshold", "Op", "Purpose"],
        ["2", "Promoter_Pledge", "10.0%", ">", "Pledged shares as % of promoter holding"],
        ["2", "Promoter_Pledge_Low_Holding_Floor", "35.0%", "<", "Holding floor that activates a stricter pledge rule"],
        ["2", "Promoter_Pledge_Low_Holding_Fail", "5.0%", ">", "Pledge ceiling when holding is below 35%"],
        ["2", "Promoter_Pledge_Total_Shares", "5.0%", ">", "Pledged shares as % of total shares"],
        ["3", "RPT_Sales_Purchases", "10.0%", ">", "Related-party sales and purchases as % of revenue"],
        ["4", "Contingent_Liabilities", "15.0%", ">", "Contingent liabilities as % of net worth"],
        ["4", "Litigation_Claims", "10.0%", ">", "Tax and litigation claims as % of net worth"],
        ["5", "CFO_PAT_Ratio", "0.80", "<", "5-year cumulative cash-flow to profit conversion"],
        ["6", "Legal_Fee_Surge", "100.0%", ">", "Year-on-year unexplained legal-fee increase"],
        ["6", "Legal_Audit_Fee_Multiplier", "3.0x", ">", "Legal fees relative to audit fees"],
    ]
    story.append(make_table(phase1, [0.6*inch, 2.15*inch, 1.0*inch, 0.35*inch, 3.15*inch], styles))
    story += [Spacer(1, 8), p("Example: how the pledge condition works", styles["h2"]),
              p("For Check #2, the base pledge threshold is 10.0%. The detailed rows add a stricter 5.0% ceiling when promoter holding is below 35.0%, plus a 5.0% test based on total shares. Treat the three detailed rows as a linked set; changing one alone can change the intended condition.", styles["callout"])]

    # Tabs 5 and 6
    story += [PageBreak(), p("Tab 5: Phase2_Matrix", styles["h1"]),
              p("This tab contains the same 24 sector-metric settings currently found in Sector_Boundary_Matrix. It is the Phase 2 operating and financial-quality configuration used for sector-aware benchmarks such as RoCE, Net Debt/EBITDA, Interest Coverage, working-capital deterioration, and receivable days.", styles["body"]),
              p("How to maintain it", styles["h2"])]
    story += bullets([
        "Keep the tab name, headers, sector profiles, metric keys, units, and threshold formats unchanged unless the engine specification changes.",
        "For any approved change, mirror the same value in Sector_Boundary_Matrix because the two tabs are currently identical.",
        "For Range rows, confirm the intended handling of the middle band between pass and fail before changing either threshold.",
        "For CCC_Det and Receivable_Days, review the Critical_Cap too. It represents the hard upper boundary documented in the sheet.",
    ], styles)
    story += [p("Current content relationship", styles["h2"]),
              p("Phase2_Matrix duplicates Sector_Boundary_Matrix as supplied. The duplicate may be required for compatibility with different engine components or for a future migration. Do not remove it from the upload file.", styles["callout"]),
              p("Tab 6: Sector_Mapping", styles["h1"]),
              p("This tab is currently identical to Company_Sector_Map. It maps the same 26 industry keywords to the same four sector profiles.", styles["body"]),
              p("How to maintain it", styles["h2"])]
    story += bullets([
        "For any approved mapping change, make the identical change in Company_Sector_Map.",
        "Do not introduce unmatched sector-profile names; each mapping needs a complete set of thresholds in the sector matrices.",
        "Preserve a clean, one-profile assignment per keyword unless conflict handling is formally documented.",
    ], styles)
    story += [p("Why both tabs matter", styles["h2"]),
              p("The workbook is structured with both a generic name and a phase-specific name for the mapping and matrix tabs. The safest upload practice is to preserve both tabs and keep paired entries aligned. Ask the tool owner which tab is authoritative only if you are planning a structural simplification; do not make that change in an upload file without approval.", styles["callout"])]

    # Tab 7
    story += [PageBreak(), p("Tab 7: Phase3_Thresholds", styles["h1"]),
              p("This tab provides the global parameters for the final evaluation phase. Phase 3 considers the valuation gap, required return path, contradictions, and final decision logic declared in Master_Rule_Definitions checks 19 to 22.", styles["body"]),
              p("Column guide", styles["h2"])]
    story.append(make_table([
        ["Column", "Meaning"],
        ["Parameter", "System key used by Phase 3 logic. Keep the name exactly as supplied."],
        ["Value", "The current numeric, text, or list setting."],
        ["Type", "Expected data type: float, int, or list."],
        ["Description", "Business meaning of the parameter."],
    ], [1.35*inch, 1.35*inch, 0.7*inch, 3.6*inch], styles))
    story += [p("Configured parameters", styles["h2"])]
    phase3 = [
        ["Parameter", "Value", "Type", "What it controls"],
        ["target_cagr", "20", "float", "Target annualised return hurdle (%)"],
        ["growth_prob_multiplier", "1.5", "float", "Multiplier of historical EPS growth for Miraculous classification"],
        ["growth_probable_margin", "2", "float", "Buffer above historical growth (percentage points) for Probable classification"],
        ["pe_rerate_miraculous_ceiling", "20", "float", "Annual P/E re-rating (%) classified as Miraculous"],
        ["valuation_fair_variance_pct", "10", "float", "Premium allowed above 5-year average while still FAIR"],
        ["guidance_miss_fatal_years", "3", "int", "Consecutive guidance misses that trigger a fatal contradiction"],
        ["single_source_dependency_ceiling_pct", "50", "float", "Vendor concentration ceiling for Vendor Risk"],
        ["outsourcing_ceiling_pct", "70", "float", "Product outsourcing ceiling for Vendor Risk"],
        ["contradiction_fatal_list", "EXPANSION_LIE, VENDOR_RISK, GUIDANCE_GAP, TONE_SHIFT", "list", "Contradiction types treated as fatal"],
    ]
    story.append(make_table(phase3, [1.8*inch, 1.35*inch, 0.55*inch, 3.3*inch], styles))
    story += [Spacer(1, 8), p("Parameter handling", styles["h2"]),
              p("Use a decimal or whole number only where the Type says float or int. For contradiction_fatal_list, retain the comma-separated list format. Do not add spaces before an item unless the rule engine's parser is documented to trim whitespace.", styles["callout"])]

    # Upload
    story += [PageBreak(), p("Editing and Upload Checklist", styles["h1"]),
              p("Use this checklist whenever you prepare a new rule-definition upload.", styles["body"]),
              p("1. Decide the intended rule change", styles["h2"])]
    story += bullets([
        "Write down the business rationale, affected phase, check number, and expected outcome.",
        "Identify whether the change is global, Phase 1 specific, or sector specific.",
        "For sector-specific changes, identify every sector profile that needs a value.",
    ], styles)
    story += [p("2. Make the workbook change", styles["h2"])]
    story += bullets([
        "Edit values only in the relevant rows; preserve sheet names, headers, and metric keys.",
        "Maintain matched duplicate tabs: Sector_Boundary_Matrix with Phase2_Matrix, and Company_Sector_Map with Sector_Mapping.",
        "Keep units and formats consistent: percentages, x multiples, days, Booleans, N/A, and list syntax.",
        "Update the Description or Note where a logic change would otherwise leave the workbook misleading.",
    ], styles)
    story += [p("3. Validate before upload", styles["h2"])]
    story += bullets([
        "Confirm each Check # still has the intended detailed thresholds, where applicable.",
        "Confirm every sector-aware check has a matching metric for all active sector profiles.",
        "Check that every industry keyword maps to a sector profile that exists in the matrices.",
        "Confirm no supported data type has been replaced by a free-text variant, such as 10 percent instead of 10.0%.",
        "Save as an .xlsx workbook without changing its tab names.",
    ], styles)
    story += [p("4. Test after upload", styles["h2"])]
    story += bullets([
        "Run a known Asset-Light company to test sector mapping and stricter leverage/coverage expectations.",
        "Run a known Capital-Intensive or Regulated-Infrastructure company to test the different Phase 2 boundaries.",
        "Run an example that should trigger a Phase 1 threshold and compare the engine outcome to the relevant sheet row.",
        "If the result is unexpected, first check the exact Input Metric/Parameter name, operator, threshold format, and sector mapping.",
    ], styles)
    story += [p("Quick troubleshooting", styles["h2"])]
    story.append(make_table([
        ["Symptom", "Likely first check"],
        ["A sector-aware rule is not using the expected threshold.", "Confirm the company keyword maps to the expected sector and that the same metric exists for that profile."],
        ["A rule fails when it should pass.", "Confirm the operator direction and the threshold unit, especially % versus decimal and x multiples."],
        ["A Phase 1 condition is ignored.", "Confirm the detailed row uses the correct Check # and exact Metric key."],
        ["The upload rejects the workbook.", "Restore sheet names/headers; check for changed data types, missing tabs, or unsupported text in numeric fields."],
        ["Paired tabs disagree.", "Reconcile the duplicate mapping or matrix entries before upload."],
    ], [2.4*inch, 4.85*inch], styles))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()
