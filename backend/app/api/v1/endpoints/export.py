"""
Data export endpoints for clinical record portability.
Supports CSV, Excel, and JSON formats.
"""

from datetime import datetime, timezone
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, Diagnosis
from app.core.deps import get_current_active_user
from app.services.export.export_service import export_service

router = APIRouter(prefix="/exports", tags=["Clinical Data Portability"])

# Modern Dependency Aliases (2026 Best Practice)
DBDep = Annotated[AsyncSession, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]

@router.get("/diagnoses/csv")
async def export_diagnoses_csv(current_user: ActiveUser, db: DBDep):
    """Generates and streams a CSV export of the user's medical history."""
    
    # Modern SQLAlchemy 2.0 select statement
    query = select(Diagnosis).where(Diagnosis.user_id == current_user.id)
    result = await db.execute(query)
    diagnoses = result.scalars().all()
    
    # Structured data preparation for the asynchronous export service
    diagnoses_data = [
        {
            'id': d.id,
            'created_at': d.created_at.isoformat(),
            'diagnosis': d.diagnosis,
            'symptoms': d.symptoms,
            'severity': d.severity,
            'urgency_level': d.urgency_level,
            'confidence': d.confidence,
            'treatment_plan': d.treatment_plan
        }
        for d in diagnoses
    ]
    
    csv_bytes = await export_service.export_diagnoses_to_csv(diagnoses_data)
    
    # Timezone-aware timestamp for the filename (2026 Standard)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f"clinical_history_{timestamp}.csv"
    
    return StreamingResponse(
        BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/diagnoses/excel")
async def export_diagnoses_excel(current_user: ActiveUser, db: DBDep):
    """Generates and streams a styled Excel report of the user's medical history."""
    
    query = select(Diagnosis).where(Diagnosis.user_id == current_user.id)
    result = await db.execute(query)
    diagnoses = result.scalars().all()
    
    diagnoses_data = [
        {
            'id': d.id,
            'created_at': d.created_at.isoformat(),
            'diagnosis': d.diagnosis,
            'symptoms': d.symptoms,
            'severity': d.severity,
            'urgency_level': d.urgency_level,
            'confidence': d.confidence
        }
        for d in diagnoses
    ]
    
    excel_bytes = await export_service.export_diagnoses_to_excel(diagnoses_data)
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f"clinical_history_{timestamp}.xlsx"
    
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/diagnoses/json")
async def export_diagnoses_json(current_user: ActiveUser, db: DBDep):
    """Generates and streams a JSON dump for interoperability with other health systems."""
    
    query = select(Diagnosis).where(Diagnosis.user_id == current_user.id)
    result = await db.execute(query)
    diagnoses = result.scalars().all()
    
    diagnoses_data = [
        {
            'id': d.id,
            'created_at': d.created_at.isoformat(),
            'diagnosis': d.diagnosis,
            'symptoms': d.symptoms,
            'severity': d.severity,
            'urgency_level': d.urgency_level,
            'confidence': d.confidence,
            'treatment_plan': d.treatment_plan
        }
        for d in diagnoses
    ]
    
    json_bytes = await export_service.export_diagnoses_to_json(diagnoses_data)
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f"clinical_history_{timestamp}.json"
    
    return StreamingResponse(
        BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )