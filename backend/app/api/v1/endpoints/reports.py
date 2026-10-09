"""
Report generation endpoints for clinical PDF exports.
"""

import logging
import json
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, Diagnosis
from app.core.deps import get_current_active_user
from app.services.pdf.report_generator import report_generator

router = APIRouter(prefix="/reports", tags=["Reports"])
logger = logging.getLogger(__name__)

# Modern Dependency Aliases (2026 Best Practice)
DBDep = Annotated[AsyncSession, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]

@router.get("/diagnosis/{diagnosis_id}/pdf")
async def download_diagnosis_pdf(
    diagnosis_id: int,
    current_user: ActiveUser,
    db: DBDep
):
    """
    Retrieves a specific diagnosis and generates a downloadable PDF report.
    Uses asynchronous SQLAlchemy 2.0 execution and non-blocking PDF generation.
    """
    # Modern SQLAlchemy 2.0 select with ownership validation
    query = (
        select(Diagnosis)
        .where(Diagnosis.id == diagnosis_id, Diagnosis.user_id == current_user.id)
    )
    result = await db.execute(query)
    diagnosis = result.scalar_one_or_none()
    
    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Diagnosis record not found"
        )
    
    try:
        treatment_plan = diagnosis.treatment_plan
        if isinstance(treatment_plan, str):
            try:
                treatment_plan = json.loads(treatment_plan)
            except json.JSONDecodeError:
                treatment_plan = {}
        elif not isinstance(treatment_plan, dict):
            treatment_plan = {}

        lung_sound_result = diagnosis.lung_sound_result_json
        if isinstance(lung_sound_result, str):
            try:
                lung_sound_result = json.loads(lung_sound_result)
            except json.JSONDecodeError:
                lung_sound_result = None
        elif not isinstance(lung_sound_result, dict):
            lung_sound_result = None

        # Structured data preparation for the generator
        diagnosis_data = {
            'id': diagnosis.id,
            'symptoms': diagnosis.symptoms,
            'diagnosis': diagnosis.diagnosis,
            'confidence': diagnosis.confidence or 0,
            'severity': diagnosis.severity or 'Unknown',
            'urgency_level': diagnosis.urgency_level or 'ROUTINE',
            'treatment_plan': treatment_plan,
            'lung_sound_result': lung_sound_result,
        }
        
        patient_data = {
            'name': current_user.full_name or 'Patient',
            'age': getattr(current_user, 'age', None),  # Robust attribute access
            'gender': current_user.gender
        }
        
        user_data = {
            'email': current_user.email
        }
        
        # Await the async PDF generation process
        pdf_bytes = await report_generator.generate_diagnosis_report(
            diagnosis_data,
            patient_data,
            user_data
        )
        
        # Stream the PDF directly from memory to the client
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=medical_report_{diagnosis_id}.pdf",
                "Cache-Control": "no-cache"
            }
        )
    
    except Exception as e:
        logger.error(f"Failed to generate clinical report ID {diagnosis_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while generating the clinical report"
        )