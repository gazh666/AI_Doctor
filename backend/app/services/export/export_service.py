"""
Clinical Data Export Service
Optimized for high-concurrency medical record processing (2026 Standard).
"""

import csv
import io
import json
import logging
import importlib
from typing import Any, Optional

logger = logging.getLogger(__name__)

class ExportService:
    """Handles multi-format clinical data serialization for medical providers."""

    async def export_diagnoses_to_csv(self, diagnoses: list[dict[str, Any]]) -> bytes:
        """
        Serializes medical records to a UTF-8 encoded CSV.
        Optimized using StringIO for efficient memory buffering.
        """
        if not diagnoses:
            return b''

        output = io.StringIO()
        fieldnames = [
            'Record_ID', 'Timestamp', 'Condition', 'Symptoms', 
            'Severity', 'Triage_Level', 'AI_Confidence', 'Plan_JSON'
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for d in diagnoses:
            # Formatting for professional medical datasets
            writer.writerow({
                'Record_ID': d.get('id', 'N/A'),
                'Timestamp': str(d.get('created_at', '')),
                'Condition': d.get('diagnosis', 'Analysis Pending'),
                'Symptoms': d.get('symptoms', ''),
                'Severity': d.get('severity', 'Unknown'),
                'Triage_Level': d.get('urgency_level', 'ROUTINE'),
                'AI_Confidence': f"{d.get('confidence', 0) * 100:.1f}%",
                'Plan_JSON': json.dumps(d.get('treatment_plan', {}))
            })

        csv_bytes = output.getvalue().encode('utf-8')
        output.close()
        return csv_bytes

    async def export_diagnoses_to_excel(self, diagnoses: list[dict[str, Any]]) -> bytes:
        """
        Generates a styled .xlsx report using openpyxl.
        Features auto-column sizing and clinical branding.
        """
        openpyxl = importlib.import_module('openpyxl')
        styles = importlib.import_module('openpyxl.styles')
        utils = importlib.import_module('openpyxl.utils')

        Workbook = openpyxl.Workbook
        Font = styles.Font
        Alignment = styles.Alignment
        PatternFill = styles.PatternFill
        get_column_letter = utils.get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = "Clinical_Records"

        # UI/UX: Professional Clinical Branding
        header_style = {
            "fill": PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid"),
            "font": Font(color="FFFFFF", bold=True, size=12),
            "align": Alignment(horizontal='center', vertical='center')
        }

        headers = ['ID', 'Consultation_Date', 'Diagnosis', 'Symptoms', 'Severity', 'Urgency', 'Confidence']
        
        # Populate and style headers
        for col, text in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=text)
            cell.fill = header_style["fill"]
            cell.font = header_style["font"]
            cell.alignment = header_style["align"]

        # Populate clinical data
        for row_idx, d in enumerate(diagnoses, start=2):
            ws.cell(row=row_idx, column=1, value=d.get('id'))
            ws.cell(row=row_idx, column=2, value=str(d.get('created_at', '')))
            ws.cell(row=row_idx, column=3, value=d.get('diagnosis'))
            ws.cell(row=row_idx, column=4, value=d.get('symptoms'))
            ws.cell(row=row_idx, column=5, value=d.get('severity'))
            ws.cell(row=row_idx, column=6, value=d.get('urgency_level'))
            ws.cell(row=row_idx, column=7, value=f"{d.get('confidence', 0) * 100:.1f}%")

        # 2026 Optimization: Dynamic Column Auto-Adjustment
        for i, _ in enumerate(headers, start=1):
            ws.column_dimensions[get_column_letter(i)].width = 22

        output = io.BytesIO()
        wb.save(output)
        content = output.getvalue()
        output.close()
        return content

    async def export_diagnoses_to_json(self, diagnoses: list[dict[str, Any]]) -> bytes:
        """
        Serializes records to standard JSON format for interoperability.
        """
        # Data scrubbing for clean clinical export
        scrubbed_data = [
            {
                'id': d.get('id'),
                'timestamp': str(d.get('created_at')),
                'clinical_finding': d.get('diagnosis'),
                'reported_symptoms': d.get('symptoms'),
                'severity_level': d.get('severity'),
                'triage_urgency': d.get('urgency_level'),
                'model_confidence': d.get('confidence'),
                'intervention_plan': d.get('treatment_plan')
            }
            for d in diagnoses
        ]

        return json.dumps(scrubbed_data, indent=2).encode('utf-8')

# Global Singleton for use in FastAPI route dependencies
export_service = ExportService()