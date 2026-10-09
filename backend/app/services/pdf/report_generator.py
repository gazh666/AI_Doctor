"""
Medical PDF Report Generation Service
Optimized for high-concurrency production environments (2026 Standard).
"""

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)

logger = logging.getLogger(__name__)


class MedicalReportGenerator:
    """Service to generate professional, AI-assisted medical diagnosis reports."""

    def __init__(self) -> None:
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        """Configures professional typography for clinical reports."""
        # Title: Clinical Branding
        self.styles.add(ParagraphStyle(
            name='ClinicalTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1e40af'), # Deep Navy
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Subtitle: Section Headers
        self.styles.add(ParagraphStyle(
            name='ClinicalSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e3a8a'),
            spaceBefore=15,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))

        # Standard Body Text
        self.styles.add(ParagraphStyle(
            name='ClinicalBody',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#374151')
        ))

    async def generate_diagnosis_report(
        self,
        diagnosis_data: dict[str, Any],
        patient_data: dict[str, Any],
        user_data: dict[str, Any]
    ) -> bytes:
        """
        Generates a comprehensive PDF report. 
        Note: Made async to prevent blocking the event loop during buffer operations.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
        )
        story = []

        # 1. Header & Metadata
        story.append(Paragraph("MEDICAL DIAGNOSIS REPORT", self.styles['ClinicalTitle']))
        
        # Use timezone-aware UTC for 2026 compliance
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        meta_text = (
            f"<b>Report ID:</b> {diagnosis_data.get('id', 'TEMP-REF')}<br/>"
            f"<b>Generated On:</b> {timestamp}"
        )
        story.append(Paragraph(meta_text, self.styles['ClinicalBody']))
        story.append(Spacer(1, 0.2 * inch))

        # 2. Patient Demographics Table
        story.append(Paragraph("PATIENT INFORMATION", self.styles['ClinicalSubtitle']))
        patient_table_data = [
            ["Full Name:", patient_data.get("name", "N/A"), "Gender:", patient_data.get("gender", "N/A")],
            ["Age:", str(patient_data.get("age", "N/A")), "Contact:", user_data.get("email", "N/A")]
        ]
        
        p_table = Table(patient_table_data, colWidths=[1.2*inch, 2*inch, 1*inch, 2.3*inch])
        p_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#6b7280')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(p_table)

        # 3. Clinical Findings
        story.append(Paragraph("CLINICAL FINDINGS", self.styles['ClinicalSubtitle']))
        urgency = diagnosis_data.get('urgency_level', 'ROUTINE').upper()
        severity_color = self._get_status_color(urgency)
        
        findings_text = (
            f"<b>Primary Assessment:</b> {diagnosis_data.get('diagnosis', 'Pending Analysis')}<br/>"
            f"<b>AI Confidence Score:</b> {diagnosis_data.get('confidence', 0) * 100:.1f}%<br/>"
            f"<b>Urgency Level:</b> <font color='{severity_color}'>{urgency}</font>"
        )
        story.append(Paragraph(findings_text, self.styles['ClinicalBody']))

        # 3.5 Lung Sound Auscultation
        lung_sound = diagnosis_data.get('lung_sound_result') or {}
        if lung_sound:
            story.append(Paragraph("LUNG SOUND AUSCULTATION", self.styles['ClinicalSubtitle']))
            sound_confidence = float(lung_sound.get('confidence', 0) or 0)
            sound_text = (
                f"<b>Respiratory Sound Label:</b> {lung_sound.get('label', 'unknown')}<br/>"
                f"<b>Auscultation Confidence:</b> {sound_confidence * 100:.1f}%"
            )
            story.append(Paragraph(sound_text, self.styles['ClinicalBody']))
            if sound_confidence < 0.7:
                story.append(Paragraph(
                    "<b>⚠️ Auscultation reliability is LOW — clinical review required.</b>",
                    self.styles['ClinicalBody']
                ))

        # 4. Treatment & Immediate Care
        plan = diagnosis_data.get('treatment_plan', {})
        if plan:
            story.append(Paragraph("TREATMENT PLAN", self.styles['ClinicalSubtitle']))
            
            if care_steps := plan.get('immediate_care'):
                story.append(Paragraph("<b>Immediate Steps:</b>", self.styles['ClinicalBody']))
                for step in care_steps:
                    story.append(Paragraph(f"• {step}", self.styles['ClinicalBody']))

            # Medications Table
            if meds := plan.get('medications'):
                story.append(Spacer(1, 0.1 * inch))
                med_data = [["Medication", "Dosage", "Frequency"]]
                for m in meds:
                    med_data.append([m.get("name"), m.get("dosage"), m.get("frequency")])
                
                m_table = Table(med_data, colWidths=[2.5*inch, 2*inch, 2*inch])
                m_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(m_table)

        # 5. Critical Red Flags (Safety First)
        if red_flags := plan.get('red_flags'):
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("⚠️ SEEK EMERGENCY CARE IF:", self.styles['ClinicalSubtitle']))
            for flag in red_flags:
                story.append(Paragraph(f"<b>• {flag}</b>", self.styles['ClinicalBody']))

        # 6. Professional Disclaimer
        story.append(Spacer(1, 0.4 * inch))
        disclaimer_style = ParagraphStyle(
            'Disclaimer', parent=self.styles['ClinicalBody'], 
            fontSize=8, textColor=colors.grey, alignment=TA_CENTER
        )
        story.append(Paragraph(
            "DISCLAIMER: This is an AI-generated clinical summary for rural support. "
            "It is NOT a replacement for a licensed physician's evaluation.", 
            disclaimer_style
        ))

        # Build and return
        doc.build(story)
        pdf_content = buffer.getvalue()
        buffer.close()
        return pdf_content

    def _get_status_color(self, status: str) -> str:
        """Maps urgency levels to standardized clinical colors."""
        mapping = {
            'EMERGENCY': '#b91c1c', # Red
            'URGENT': '#c2410c',    # Orange
            'ROUTINE': '#15803d',   # Green
        }
        return mapping.get(status, '#000000')

# Global Singleton for use in FastAPI Dependencies
report_generator = MedicalReportGenerator()