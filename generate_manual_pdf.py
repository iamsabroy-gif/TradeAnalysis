from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

def create_pdf(output_path):
    doc = SimpleDocTemplate(output_path, pagesize=LETTER)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=15,
        spaceAfter=10,
        color=colors.HexColor('#2E5A88')
    )
    
    body_style = styles['BodyText']
    body_style.fontSize = 11
    body_style.leading = 14

    content = []

    # Title
    content.append(Paragraph("User Manual: Master Rule Definition Sheet", title_style))
    content.append(Paragraph("Configuration Guide for the Rule Engine Evaluation Tool", styles['Normal']))
    content.append(Paragraph("", styles['Normal'])) # Spacer effect
    content.append(Spacer(1, 20))

    # Introduction
    content.append(Paragraph("1. Introduction", heading_style))
    content.append(Paragraph(
        "This manual explains how to use the Master Rule Definition spreadsheet. This file serves as the configuration layer for the Rule Engine Evaluation tool, defining the logic and thresholds used to screen companies across three evaluation phases.",
        body_style
    ))
    content.append(Spacer(1, 12))

    # Sheet-by-Sheet Guide
    content.append(Paragraph("2. Sheet-by-Sheet Guide", heading_style))
    
    sheets = [
        ("Master_Rule_Definitions", 
         "The central index of all rules. It defines which metric to check, the logic type (Numeric or Categorical), the operator (e.g., >, <, !=), and the default fail value. If 'Sector-Aware?' is set to 'Yes', the tool will look for thresholds in the Sector Boundary Matrix."),
        ("Sector_Boundary_Matrix & Phase 2 Matrix", 
         "Defines thresholds that vary by business model. For example, an 'Asset-Light' company will have different healthy RoCE or Debt thresholds than an 'Asset-Heavy' one. It uses Pass, Fail, and Critical caps to categorize results."),
        ("Company_Sector_Map & Sector Mapping", 
         "Tells the tool how to categorize a company based on industry keywords (e.g., 'SaaS' maps to 'ASSET_LIGHT'). This ensures the correct sector-specific thresholds are applied."),
        ("Phase 1 Thresholds", 
         "Contains the specific numeric 'trip-wire' values for initial screening rules. These override defaults for high-priority checks."),
        ("Phase 3 Thresholds", 
         "Sets global parameters used for final scoring and classifications, such as Target CAGR or P/E re-rating ceilings.")
    ]

    for sheet, desc in sheets:
        content.append(Paragraph(f"<b>{sheet}</b>", body_style))
        content.append(Paragraph(desc, body_style))
        content.append(Spacer(1, 8))

    # Key Data Guidelines
    content.append(Paragraph("3. Key Data Guidelines", heading_style))
    
    guidelines = [
        ("Metric Names", "Input Metrics must match the data source exactly (case-sensitive)."),
        ("Operators", "Use only supported symbols: '>' (Greater than), '<' (Less than), '!=' (Not equal to), '=' (Equal to), or 'Range'."),
        ("Logic Types", "Use 'Categorical' for text-based checks and 'Numeric' for number-based checks."),
        ("Structural Integrity", "Do not rename, move, or delete column headers, as the upload tool relies on a fixed structure.")
    ]
    
    data = [["Field", "Requirement"]]
    for field, req in guidelines:
        data.append([field, req])
    
    t = Table(data, colWidths=[120, 350])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEEEEE')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    content.append(t)
    content.append(Spacer(1, 12))

    # Upload Process
    content.append(Paragraph("4. Upload & Deployment", heading_style))
    content.append(Paragraph(
        "1. Update rules/thresholds in the .xlsx file.<br/>"
        "2. Save the workbook (ensure no active filters or broken formulas).<br/>"
        "3. Upload the file via the tool's configuration interface.<br/>"
        "4. Validate the upload by running a test evaluation on a known sample company.",
        body_style
    ))

    doc.build(content)

if __name__ == "__main__":
    create_pdf("Master_Rule_Definitions_User_Manual.pdf")
