"""
ThyroScan — Medical PDF Screening Report Generator
Generates clinical-grade downloadable PDF reports using ReportLab.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY


def generate_pdf_report(assessment_data: dict, patient_info: dict = None) -> io.BytesIO:
    """
    Generates a PDF document for an assessment.
    Returns an in-memory BytesIO stream containing the PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        alignment=TA_LEFT
    )

    subtitle_style = ParagraphStyle(
        'BrandSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_LEFT
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_text = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    badge_text = ParagraphStyle(
        'BadgeText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_JUSTIFY
    )

    story = []

    # 1. Header Bar
    header_table_data = [
        [
            Paragraph("<b>THYROSCAN AI</b><br/><font size=9 color='#64748b'>AI-Assisted Thyroid Risk Screening Report</font>", brand_style),
            Paragraph(f"<b>Report Date:</b> {datetime.now().strftime('%d %b %Y, %H:%M')}<br/><b>Model:</b> v1.0-gb-calibrated<br/><b>Report ID:</b> #{assessment_data.get('id', 'TS-PREVIEW')}", subtitle_style)
        ]
    ]
    header_table = Table(header_table_data, colWidths=[3.2 * inch, 4.0 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0ea5e9'), spaceBefore=4, spaceAfter=12))

    # 2. Patient Demographics & Assessment Overview
    pat = patient_info or {}
    inputs = assessment_data.get('inputs', {})
    age_val = pat.get('age') or inputs.get('age', 'N/A')
    sex_val = 'Female' if str(pat.get('sex') or inputs.get('sex')) == '0' else ('Male' if str(pat.get('sex') or inputs.get('sex')) == '1' else 'Not Specified')
    height_val = f"{pat.get('height_cm')} cm" if pat.get('height_cm') else 'N/A'
    weight_val = f"{pat.get('weight_kg')} kg" if pat.get('weight_kg') else 'N/A'
    bmi_val = f"{round(float(pat.get('bmi')), 1)}" if pat.get('bmi') else (f"{round(float(inputs.get('bmi')), 1)}" if inputs.get('bmi') else 'N/A')

    patient_table_data = [
        [
            Paragraph("<b>Patient Demographics & Vitals</b>", section_heading),
            ""
        ],
        [
            Paragraph(f"<b>Name:</b> {pat.get('name', 'Anonymous Patient')}", body_text),
            Paragraph(f"<b>Age:</b> {age_val} yrs | <b>Sex:</b> {sex_val}", body_text)
        ],
        [
            Paragraph(f"<b>Height:</b> {height_val} | <b>Weight:</b> {weight_val}", body_text),
            Paragraph(f"<b>BMI:</b> {bmi_val}", body_text)
        ]
    ]
    patient_table = Table(patient_table_data, colWidths=[3.6 * inch, 3.6 * inch])
    patient_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 1), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 10))

    # 3. Screening Result & Risk Stratification
    res_label = assessment_data.get('badge', assessment_data.get('screening_result', 'Negative').title())
    prob_val = assessment_data.get('model_probability', 0)
    risk_level = assessment_data.get('risk_level', 'low')

    badge_bg = colors.HexColor('#10b981') if risk_level == 'low' else (colors.HexColor('#f59e0b') if risk_level == 'moderate' else colors.HexColor('#ef4444'))

    result_box_data = [
        [
            Paragraph(f"<b>SCREENING RESULT: {res_label.upper()}</b>", badge_text),
            Paragraph(f"<b>Model Probability Estimate:</b> {prob_val}%<br/><font size=8 color='#64748b'>Pattern match confidence based on submitted clinical inputs</font>", body_text)
        ]
    ]
    result_box = Table(result_box_data, colWidths=[3.6 * inch, 3.6 * inch])
    result_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), badge_bg),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f8fafc')),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, badge_bg),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(result_box)
    story.append(Spacer(1, 8))

    summary_p = Paragraph(f"<b>Clinical Observation Summary:</b> {assessment_data.get('summary', '')}", body_text)
    story.append(summary_p)
    story.append(Spacer(1, 10))

    # 4. Biomarkers Table
    biomarkers = assessment_data.get('biomarker_analysis', [])
    if biomarkers:
        story.append(Paragraph("<b>Laboratory Biomarker Analysis & Reference Ranges</b>", section_heading))
        bio_table_data = [
            [
                Paragraph("<b>Biomarker Parameter</b>", body_text),
                Paragraph("<b>Measured Value</b>", body_text),
                Paragraph("<b>Typical Reference Range</b>", body_text),
                Paragraph("<b>Status</b>", body_text)
            ]
        ]
        for bio in biomarkers:
            status_color = '#10b981' if bio['status'] == 'normal' else ('#f59e0b' if 'low' in bio['status'] else '#ef4444')
            status_badge = f"<font color='{status_color}'><b>{bio['status_label']}</b></font>"
            bio_table_data.append([
                Paragraph(f"{bio['name']} ({bio['code']})", body_text),
                Paragraph(f"<b>{bio['value']}</b> {bio['unit']}", body_text),
                Paragraph(f"{bio['ref_min']} – {bio['ref_max']} {bio['unit']}", body_text),
                Paragraph(status_badge, body_text)
            ])

        bio_table = Table(bio_table_data, colWidths=[2.6 * inch, 1.4 * inch, 1.8 * inch, 1.4 * inch])
        bio_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ]))
        story.append(bio_table)
        story.append(Spacer(1, 10))

    # 5. Model Probability Breakdown Table
    class_probs = assessment_data.get('class_probabilities', {})
    if class_probs:
        story.append(Paragraph("<b>Multiclass Model Probability Distribution</b>", section_heading))
        prob_table_data = [
            [
                Paragraph("<b>Diagnostic Category</b>", body_text),
                Paragraph("<b>Calculated Probability</b>", body_text)
            ]
        ]
        name_map = {
            'negative': 'Low Risk / Normal Baseline',
            'hypothyroid': 'Hypothyroidism (Underactive)',
            'hyperthyroid': 'Hyperthyroidism (Overactive)',
            'subclinical_hypothyroid': 'Subclinical Hypothyroidism',
            'subclinical_hyperthyroid': 'Subclinical Hyperthyroidism'
        }
        for cls, pct in class_probs.items():
            prob_table_data.append([
                Paragraph(name_map.get(cls, cls.title()), body_text),
                Paragraph(f"<b>{pct}%</b>", body_text)
            ])

        prob_table = Table(prob_table_data, colWidths=[4.2 * inch, 3.0 * inch])
        prob_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ]))
        story.append(prob_table)
        story.append(Spacer(1, 10))

    # 6. Action Plan & What to do next
    action_plan = assessment_data.get('action_plan', [])
    if action_plan:
        story.append(Paragraph("<b>Recommended Next Steps & Clinical Action Plan</b>", section_heading))
        for idx, item in enumerate(action_plan, 1):
            story.append(Paragraph(f"• {item}", body_text))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 8))

    # 7. Medical Disclaimer
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#cbd5e1'), spaceBefore=6, spaceAfter=6))
    story.append(Paragraph("<b>IMPORTANT MEDICAL DISCLAIMER & LIMITATIONS:</b>", section_heading))
    disclaimer_full = (
        "This report is an AI-assisted screening assessment generated using statistical machine learning models trained on "
        "historical clinical biomarker datasets. It is provided strictly for educational and preliminary risk stratification purposes "
        "and DOES NOT constitute a medical diagnosis, medical advice, or physician consultation. Reference ranges are laboratory-specific "
        "and may vary by age, pregnancy, and testing assay. Never begin, discontinue, or adjust prescription medication (such as Levothyroxine "
        "or Antithyroid drugs) without consulting a licensed physician or endocrinologist."
    )
    story.append(Paragraph(disclaimer_full, disclaimer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
