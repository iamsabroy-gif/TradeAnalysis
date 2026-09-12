import os
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def parse_markdown(text):
    lines = text.split('\n')
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    h1_style = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=18, spaceAfter=12, spaceBefore=12)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, spaceAfter=10, spaceBefore=10)
    h3_style = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=12, spaceAfter=8, spaceBefore=8)
    body_style = styles['Normal']
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            elements.append(Spacer(12, 12))
            i += 1
            continue
            
        if line.startswith('# '):
            elements.append(Paragraph(line[2:], h1_style))
        elif line.startswith('## '):
            elements.append(Paragraph(line[3:], h2_style))
        elif line.startswith('### '):
            elements.append(Paragraph(line[4:], h3_style))
        elif line.startswith('- ') or line.startswith('* '):
            # Basic list item
            elements.append(Paragraph(f"&bull; {line[2:]}", body_style))
        elif line.startswith('|'):
            # Table processing
            table_data = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row = [cell.strip() for cell in lines[i].split('|') if cell.strip()]
                if not all(char == '-' for char in row[0]) and not all(char == ':' for char in row[0]):
                    table_data.append(row)
                i += 1
            
            if table_data:
                t = Table(table_data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(t)
                i -= 1 # Offset the loop increment
        else:
            # Handle basic bolding **text**
            processed_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            elements.append(Paragraph(processed_text, body_style))
        
        i += 1
    return elements

def create_pdf(input_md, output_pdf):
    with open(input_md, 'r', encoding='utf-8') as f:
        text = f.read()
    
    doc = SimpleDocTemplate(output_pdf, pagesize=LETTER)
    elements = parse_markdown(text)
    doc.build(elements)

if __name__ == "__main__":
    create_pdf('Rule_Engine_User_Manual.md', 'Rule_Engine_User_Manual.pdf')
