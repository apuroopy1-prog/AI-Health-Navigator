"""
Enhanced PDF report builder for AI Health Navigator.
Integrates charts and provides professional formatting.
"""

import io
from datetime import datetime
from typing import List, Dict, Optional, Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable

from .chart_generator import (
    generate_symptom_severity_chart,
    generate_risk_gauge,
    generate_treatment_timeline,
    generate_history_trend,
)


# Color constants
COLORS = {
    'primary': colors.HexColor('#0066cc'),
    'secondary': colors.HexColor('#0088ff'),
    'low_risk': colors.HexColor('#28a745'),
    'medium_risk': colors.HexColor('#ffc107'),
    'high_risk': colors.HexColor('#dc3545'),
    'background': colors.HexColor('#f8f9fa'),
    'light_blue': colors.HexColor('#e3f2fd'),
    'text': colors.black,
    'gray': colors.gray,
    'dark_gray': colors.HexColor('#333333'),
}


class PageNumCanvas:
    """Custom canvas to add page numbers."""

    def __init__(self, canvas, doc):
        self.canvas = canvas
        self.doc = doc

    def afterPage(self):
        """Add page number after each page."""
        page_num = self.canvas.getPageNumber()
        text = f"Page {page_num}"
        self.canvas.saveState()
        self.canvas.setFont('Helvetica', 8)
        self.canvas.setFillColor(colors.gray)
        self.canvas.drawCentredString(4.25 * inch, 0.5 * inch, text)
        self.canvas.restoreState()


class EnhancedPDFBuilder:
    """Builder class for creating enhanced PDF reports with charts."""

    def __init__(self):
        self.styles = self._create_styles()
        self.elements = []

    def _create_styles(self) -> dict:
        """Create custom paragraph styles."""
        base_styles = getSampleStyleSheet()

        custom_styles = {
            'title': ParagraphStyle(
                'CustomTitle',
                parent=base_styles['Heading1'],
                fontSize=28,
                textColor=COLORS['primary'],
                alignment=TA_CENTER,
                spaceAfter=5,
                fontName='Helvetica-Bold'
            ),
            'subtitle': ParagraphStyle(
                'Subtitle',
                parent=base_styles['Normal'],
                fontSize=14,
                alignment=TA_CENTER,
                textColor=COLORS['gray'],
                spaceAfter=20
            ),
            'heading1': ParagraphStyle(
                'CustomH1',
                parent=base_styles['Heading2'],
                fontSize=16,
                textColor=COLORS['primary'],
                spaceBefore=20,
                spaceAfter=12,
                fontName='Helvetica-Bold'
            ),
            'heading2': ParagraphStyle(
                'CustomH2',
                parent=base_styles['Heading3'],
                fontSize=12,
                textColor=COLORS['dark_gray'],
                spaceBefore=12,
                spaceAfter=8,
                fontName='Helvetica-Bold'
            ),
            'body': ParagraphStyle(
                'CustomBody',
                parent=base_styles['Normal'],
                fontSize=10,
                alignment=TA_JUSTIFY,
                spaceAfter=8,
                leading=14
            ),
            'bullet': ParagraphStyle(
                'Bullet',
                parent=base_styles['Normal'],
                fontSize=10,
                leftIndent=20,
                spaceAfter=6,
                leading=14
            ),
            'disclaimer': ParagraphStyle(
                'Disclaimer',
                parent=base_styles['Normal'],
                fontSize=8,
                textColor=COLORS['gray'],
                alignment=TA_CENTER,
                leading=10
            ),
            'cover_title': ParagraphStyle(
                'CoverTitle',
                parent=base_styles['Heading1'],
                fontSize=36,
                textColor=COLORS['primary'],
                alignment=TA_CENTER,
                spaceAfter=20,
                fontName='Helvetica-Bold'
            ),
            'cover_subtitle': ParagraphStyle(
                'CoverSubtitle',
                parent=base_styles['Normal'],
                fontSize=18,
                alignment=TA_CENTER,
                textColor=COLORS['gray'],
                spaceAfter=40
            ),
        }

        return custom_styles

    def add_cover_page(
        self,
        patient_name: str,
        patient_age: int,
        report_id: str,
        assessment_date: datetime
    ):
        """Add a professional cover page."""
        # Spacer to center content vertically
        self.elements.append(Spacer(1, 2 * inch))

        # Main title
        self.elements.append(Paragraph("AI Health Navigator", self.styles['cover_title']))
        self.elements.append(Paragraph("Patient Assessment Report", self.styles['cover_subtitle']))

        self.elements.append(Spacer(1, 0.5 * inch))

        # Decorative line
        self.elements.append(HRFlowable(
            width="60%", thickness=3, color=COLORS['primary'],
            spaceBefore=20, spaceAfter=20, hAlign='CENTER'
        ))

        self.elements.append(Spacer(1, 0.5 * inch))

        # Patient info box
        cover_data = [
            ["Patient Name", patient_name or "Not Provided"],
            ["Age", f"{patient_age} years" if patient_age else "Not Provided"],
            ["Report ID", report_id],
            ["Assessment Date", assessment_date.strftime('%B %d, %Y')],
            ["Report Generated", datetime.now().strftime('%B %d, %Y at %I:%M %p')],
        ]

        cover_table = Table(cover_data, colWidths=[2 * inch, 3 * inch])
        cover_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), COLORS['light_blue']),
            ('TEXTCOLOR', (0, 0), (-1, -1), COLORS['text']),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS['gray']),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        self.elements.append(cover_table)

        self.elements.append(Spacer(1, 1.5 * inch))

        # Footer note
        self.elements.append(Paragraph(
            "This report is confidential and intended for the patient and their healthcare providers.",
            self.styles['disclaimer']
        ))

        self.elements.append(PageBreak())

    def add_executive_summary(
        self,
        intake_summary: str,
        risk_level: str,
        care_level: str
    ):
        """Add executive summary section."""
        self.elements.append(Paragraph("Executive Summary", self.styles['heading1']))

        # Risk level box with color coding
        risk_color = {
            'Low': COLORS['low_risk'],
            'Medium': COLORS['medium_risk'],
            'High': COLORS['high_risk']
        }.get(risk_level, COLORS['gray'])

        summary_data = [
            ["Overall Risk Level", risk_level, "Recommended Care", care_level],
        ]

        summary_table = Table(summary_data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), COLORS['light_blue']),
            ('BACKGROUND', (2, 0), (2, 0), COLORS['light_blue']),
            ('TEXTCOLOR', (1, 0), (1, 0), risk_color),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS['gray']),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        self.elements.append(summary_table)
        self.elements.append(Spacer(1, 15))

        # Intake summary text
        if intake_summary:
            clean_text = self._clean_markdown(intake_summary)
            for line in clean_text.split('\n'):
                if line.strip():
                    self.elements.append(Paragraph(line.strip(), self.styles['body']))

        self.elements.append(Spacer(1, 10))

    def add_patient_info_section(
        self,
        patient_name: str,
        patient_age: int,
        primary_complaints: List[str],
        medical_history: List[str],
        medications: List[str],
        allergies: List[str]
    ):
        """Add detailed patient information section."""
        self.elements.append(Paragraph("Patient Information", self.styles['heading1']))

        # Basic info table
        basic_data = [
            ["Patient Name", patient_name or "Not Provided"],
            ["Age", f"{patient_age} years" if patient_age else "Not Provided"],
        ]

        basic_table = Table(basic_data, colWidths=[2 * inch, 4.5 * inch])
        basic_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), COLORS['light_blue']),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS['gray']),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        self.elements.append(basic_table)
        self.elements.append(Spacer(1, 10))

        # Primary complaints
        if primary_complaints:
            self.elements.append(Paragraph("Primary Complaints", self.styles['heading2']))
            for complaint in primary_complaints:
                self.elements.append(Paragraph(f"• {complaint}", self.styles['bullet']))

        # Medical history
        if medical_history:
            self.elements.append(Paragraph("Medical History", self.styles['heading2']))
            for item in medical_history:
                self.elements.append(Paragraph(f"• {item}", self.styles['bullet']))

        # Medications
        if medications:
            self.elements.append(Paragraph("Current Medications", self.styles['heading2']))
            for med in medications:
                self.elements.append(Paragraph(f"• {med}", self.styles['bullet']))

        # Allergies
        if allergies:
            self.elements.append(Paragraph("Known Allergies", self.styles['heading2']))
            for allergy in allergies:
                self.elements.append(Paragraph(f"• {allergy}", self.styles['bullet']))

        self.elements.append(Spacer(1, 10))

    def add_symptom_severity_chart(self, symptoms: List[Dict]):
        """Add symptom severity visualization chart."""
        if not symptoms:
            return

        self.elements.append(Paragraph("Symptom Severity Analysis", self.styles['heading1']))

        try:
            chart_bytes = generate_symptom_severity_chart(symptoms)
            chart_image = Image(io.BytesIO(chart_bytes), width=6 * inch, height=3 * inch)
            self.elements.append(chart_image)
        except Exception as e:
            self.elements.append(Paragraph(
                f"Chart generation unavailable: {str(e)}",
                self.styles['body']
            ))

        self.elements.append(Spacer(1, 15))

    def add_risk_gauge_chart(self, risk_level: str, risk_score: Optional[float] = None):
        """Add risk assessment gauge chart."""
        self.elements.append(Paragraph("Risk Assessment Visualization", self.styles['heading1']))

        try:
            chart_bytes = generate_risk_gauge(risk_level, risk_score)
            chart_image = Image(io.BytesIO(chart_bytes), width=4.5 * inch, height=3 * inch)
            # Center the image
            chart_table = Table([[chart_image]], colWidths=[6.5 * inch])
            chart_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            self.elements.append(chart_table)
        except Exception as e:
            self.elements.append(Paragraph(
                f"Chart generation unavailable: {str(e)}",
                self.styles['body']
            ))

        self.elements.append(Spacer(1, 15))

    def add_clinical_assessment(self, assessment_findings: str):
        """Add clinical assessment findings section."""
        self.elements.append(Paragraph("Clinical Assessment", self.styles['heading1']))

        if assessment_findings:
            clean_text = self._clean_markdown(assessment_findings)
            for line in clean_text.split('\n'):
                if line.strip():
                    # Check if it's a subheading (lines ending with colon or all caps)
                    if line.strip().endswith(':') or line.strip().isupper():
                        self.elements.append(Paragraph(line.strip(), self.styles['heading2']))
                    else:
                        self.elements.append(Paragraph(line.strip(), self.styles['body']))
        else:
            self.elements.append(Paragraph("No clinical assessment data available.", self.styles['body']))

        self.elements.append(Spacer(1, 10))

    def add_treatment_timeline_chart(self, recommendations: List[str], care_level: str):
        """Add treatment timeline visualization."""
        if not recommendations:
            return

        self.elements.append(Paragraph("Treatment Timeline", self.styles['heading1']))

        try:
            chart_bytes = generate_treatment_timeline(recommendations, care_level)
            chart_image = Image(io.BytesIO(chart_bytes), width=7 * inch, height=3.5 * inch)
            self.elements.append(chart_image)
        except Exception as e:
            self.elements.append(Paragraph(
                f"Timeline chart unavailable: {str(e)}",
                self.styles['body']
            ))

        self.elements.append(Spacer(1, 15))

    def add_treatment_recommendations(self, recommendations: List[str], care_level: str):
        """Add detailed treatment recommendations section."""
        self.elements.append(Paragraph("Treatment Recommendations", self.styles['heading1']))

        # Care level indicator
        care_colors = {
            'Self-Care': COLORS['low_risk'],
            'Primary Care': COLORS['medium_risk'],
            'Urgent Care': COLORS['high_risk'],
            'Emergency': colors.HexColor('#8B0000')
        }
        care_color = care_colors.get(care_level, COLORS['gray'])

        care_table = Table([["Recommended Care Level:", care_level]], colWidths=[2 * inch, 4.5 * inch])
        care_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), COLORS['light_blue']),
            ('TEXTCOLOR', (1, 0), (1, 0), care_color),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS['gray']),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        self.elements.append(care_table)
        self.elements.append(Spacer(1, 15))

        # Numbered recommendations
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                rec_clean = self._clean_markdown(rec)
                self.elements.append(Paragraph(f"{i}. {rec_clean}", self.styles['body']))
        else:
            self.elements.append(Paragraph("No specific recommendations at this time.", self.styles['body']))

        self.elements.append(Spacer(1, 15))

    def add_history_trend_chart(self, assessments: List[Dict]):
        """Add patient history trend chart if multiple assessments exist."""
        if not assessments or len(assessments) < 2:
            return

        self.elements.append(Paragraph("Health Trend Analysis", self.styles['heading1']))
        self.elements.append(Paragraph(
            "The following chart shows your risk level trend across recent assessments:",
            self.styles['body']
        ))

        try:
            chart_bytes = generate_history_trend(assessments)
            chart_image = Image(io.BytesIO(chart_bytes), width=6 * inch, height=3 * inch)
            self.elements.append(chart_image)
        except Exception as e:
            self.elements.append(Paragraph(
                f"Trend chart unavailable: {str(e)}",
                self.styles['body']
            ))

        self.elements.append(Spacer(1, 15))

    def add_disclaimer(self):
        """Add disclaimer and footer section."""
        self.elements.append(HRFlowable(
            width="100%", thickness=1, color=COLORS['gray'],
            spaceBefore=20, spaceAfter=10
        ))

        disclaimer_text = (
            "DISCLAIMER: This report is generated by an AI-assisted health navigation system "
            "and is intended for informational purposes only. It does not constitute medical advice, "
            "diagnosis, or treatment. Always consult with a qualified healthcare professional for "
            "medical concerns. In case of emergency, call emergency services (911) immediately."
        )
        self.elements.append(Paragraph(disclaimer_text, self.styles['disclaimer']))

        self.elements.append(Spacer(1, 10))
        self.elements.append(Paragraph(
            f"Generated by AI Health Navigator | {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            self.styles['disclaimer']
        ))

    def _clean_markdown(self, text: str) -> str:
        """Remove markdown formatting from text."""
        if not text:
            return ""
        return text.replace('**', '').replace('*', '').replace('`', '').replace('#', '')

    def build(self) -> bytes:
        """Build the PDF and return as bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch
        )

        doc.build(self.elements)
        buffer.seek(0)
        return buffer.getvalue()


def generate_enhanced_pdf_report(
    result: Dict[str, Any],
    patient_name: str,
    patient_age: int,
    include_charts: bool = True,
    symptoms_with_severity: Optional[List[Dict]] = None,
    assessment_history: Optional[List[Dict]] = None
) -> bytes:
    """
    Generate an enhanced PDF report with charts.

    Args:
        result: Assessment result dictionary
        patient_name: Patient's name
        patient_age: Patient's age
        include_charts: Whether to include visual charts
        symptoms_with_severity: List of symptoms with severity scores for chart
        assessment_history: List of past assessments for trend chart

    Returns:
        PDF as bytes
    """
    builder = EnhancedPDFBuilder()

    # Generate report ID
    report_id = f"AHN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    assessment_date = datetime.now()

    # Cover page
    builder.add_cover_page(patient_name, patient_age, report_id, assessment_date)

    # Executive Summary
    builder.add_executive_summary(
        intake_summary=result.get('intake_summary', ''),
        risk_level=result.get('initial_risk_level', result.get('clinical_risk_level', 'Medium')),
        care_level=result.get('care_level', 'Primary Care')
    )

    # Patient Information
    builder.add_patient_info_section(
        patient_name=patient_name,
        patient_age=patient_age,
        primary_complaints=result.get('primary_complaints', []),
        medical_history=result.get('medical_history', []),
        medications=result.get('current_medications', []),
        allergies=result.get('allergies', [])
    )

    if include_charts:
        # Symptom Severity Chart
        if symptoms_with_severity:
            builder.add_symptom_severity_chart(symptoms_with_severity)
        elif result.get('primary_complaints'):
            # Create default severity data from complaints
            default_symptoms = [
                {'name': complaint, 'severity': 5}
                for complaint in result.get('primary_complaints', [])[:6]
            ]
            builder.add_symptom_severity_chart(default_symptoms)

        # Risk Gauge
        builder.add_risk_gauge_chart(
            risk_level=result.get('clinical_risk_level', result.get('initial_risk_level', 'Medium')),
            risk_score=result.get('risk_score')
        )

    # Clinical Assessment
    builder.add_clinical_assessment(result.get('assessment_findings', ''))

    if include_charts:
        # Treatment Timeline
        builder.add_treatment_timeline_chart(
            recommendations=result.get('treatment_recommendations', []),
            care_level=result.get('care_level', 'Primary Care')
        )

    # Treatment Recommendations (detailed list)
    builder.add_treatment_recommendations(
        recommendations=result.get('treatment_recommendations', []),
        care_level=result.get('care_level', 'Primary Care')
    )

    if include_charts and assessment_history:
        # History Trend (if available)
        builder.add_history_trend_chart(assessment_history)

    # Disclaimer
    builder.add_disclaimer()

    return builder.build()
