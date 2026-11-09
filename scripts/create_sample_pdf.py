from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from pathlib import Path

def generate_pdf():
    output_path = Path(__file__).resolve().parent.parent / "financial_earnings_report.pdf"
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=12,
    )
    
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=14,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8,
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("NovaTech Enterprises - Q3 2026 Financial & Operational Report", title_style))
    story.append(Paragraph("<b>Reporting Period:</b> July 1, 2026 - September 30, 2026 | <b>Ticker:</b> NVTE (NASDAQ)", body_style))
    story.append(Spacer(1, 10))

    # Executive Summary
    story.append(Paragraph("1. Executive Financial Summary", h2_style))
    story.append(Paragraph(
        "NovaTech Enterprises delivered record operational performance in the third quarter of 2026, driven by rapid customer expansion in our Enterprise AI and Hybrid Cloud divisions. Consolidated quarterly revenue reached <b>$428.5 million</b>, representing a <b>24.8% year-over-year increase</b> compared to Q3 2025 ($343.3 million). Operating income expanded to <b>$94.2 million</b>, delivering an operating margin of <b>22.0%</b>.",
        body_style
    ))

    # Financial Data Table
    table_data = [
        ["Financial Metric", "Q3 2025", "Q3 2026", "YoY Change (%)"],
        ["Total Revenue", "$343.3M", "$428.5M", "+24.8%"],
        ["Cloud Platform Revenue", "$182.1M", "$254.6M", "+39.8%"],
        ["Gross Profit Margin", "68.4%", "72.1%", "+370 bps"],
        ["Operating Income", "$65.2M", "$94.2M", "+44.5%"],
        ["Free Cash Flow", "$51.0M", "$78.4M", "+53.7%"],
        ["Net Cash & Equivalents", "$612.0M", "$845.2M", "+38.1%"],
    ]

    t = Table(table_data, colWidths=[180, 100, 100, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # Segment Breakdown
    story.append(Paragraph("2. Divisional Segment Analysis", h2_style))
    story.append(Paragraph(
        "<b>Cloud & AI Infrastructure:</b> Revenue rose to $254.6 million, accounting for 59.4% of total net sales. Annual recurring revenue (ARR) concluded at $1.02 billion. Customer Net Retention Rate (NRR) remained high at 128%.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Cybersecurity & Compliance:</b> Delivered $112.4 million in net revenue, up 11.2% year-over-year. The new Zero-Trust Identity Guard product onboarded 142 Fortune 500 customers.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Professional Services:</b> Recorded $61.5 million with an intentional transition toward certified third-party system integrator partnerships.",
        body_style
    ))

    # SLA and Operational Metrics
    story.append(Paragraph("3. SLA Compliance & Reliability Standards", h2_style))
    story.append(Paragraph(
        "During the third quarter, the NovaTech Cloud maintained a global uptime availability of <b>99.994%</b> across all 18 multi-tenant regions, exceeding the contractual SLA threshold of 99.99%. Mean Time to Detect (MTTD) decreased from 4.2 minutes to <b>1.8 minutes</b>, and Mean Time to Recovery (MTTR) averaged <b>11.4 minutes</b>.",
        body_style
    ))

    # Forward Guidance
    story.append(Paragraph("4. Fiscal Year 2026 Full-Year Guidance", h2_style))
    story.append(Paragraph(
        "For the full fiscal year ending December 31, 2026, NovaTech leadership projects:<br/>"
        "• Total consolidated revenue between <b>$1.72 billion and $1.76 billion</b> (previously $1.68B - $1.71B).<br/>"
        "• Non-GAAP Operating Margin between <b>22.5% and 23.5%</b>.<br/>"
        "• Capital expenditures (CapEx) allocated at approximately <b>$110 million</b> dedicated to data center expansion and GPU clusters.",
        body_style
    ))

    doc.build(story)
    print(f"Successfully generated: {output_path}")

if __name__ == "__main__":
    generate_pdf()
