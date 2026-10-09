"""
Appointment management endpoints for clinical scheduling.
Utilizes asynchronous SQLAlchemy 2.0 patterns for 2026 production standards.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, Appointment
from app.core.deps import get_current_active_user
from app.schemas.appointments import AppointmentCreate, AppointmentUpdate, AppointmentInDB

router = APIRouter(prefix="/appointments", tags=["Clinical Scheduling"])

# Modern Dependency Aliases
DBDep = Annotated[AsyncSession, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]

@router.post("/", response_model=AppointmentInDB, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: ActiveUser,
    db: DBDep
):
    """
    Schedules a new clinical appointment.
    Performs an availability check using non-blocking I/O.
    """
    # Check for existing active bookings at the same time
    query = select(Appointment).where(
        and_(
            Appointment.scheduled_date == appointment_data.scheduled_date,
            Appointment.status == 'scheduled'
        )
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The requested time slot is already reserved"
        )
    
    appointment = Appointment(
        user_id=current_user.id,
        patient_id=appointment_data.patient_id,
        appointment_type=appointment_data.appointment_type,
        scheduled_date=appointment_data.scheduled_date,
        duration_minutes=appointment_data.duration_minutes,
        notes=appointment_data.notes,
        status='scheduled'
    )
    
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment

@router.get("/", response_model=list[AppointmentInDB])
async def get_appointments(
    db: DBDep,
    current_user: ActiveUser,
    upcoming_only: bool = True
):
    """Retrieves appointments for the authenticated user."""
    query = select(Appointment).where(Appointment.user_id == current_user.id)
    
    if upcoming_only:
        # Use timezone-aware UTC for 2026 standards
        now = datetime.now(timezone.utc)
        query = query.filter(Appointment.scheduled_date >= now)
    
    result = await db.execute(query.order_by(Appointment.scheduled_date))
    return list(result.scalars().all())

@router.get("/{appointment_id}", response_model=AppointmentInDB)
async def get_appointment(
    appointment_id: int,
    current_user: ActiveUser,
    db: DBDep
):
    """Fetches detailed information for a specific appointment."""
    query = select(Appointment).where(
        Appointment.id == appointment_id,
        Appointment.user_id == current_user.id
    )
    result = await db.execute(query)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Appointment record not found"
        )
    
    return appointment

@router.put("/{appointment_id}", response_model=AppointmentInDB)
async def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    current_user: ActiveUser,
    db: DBDep
):
    """
    Updates appointment details. 
    Demonstrates partial updates with standard SQLAlchemy 2.0 object mapping.
    """
    query = select(Appointment).where(
        Appointment.id == appointment_id,
        Appointment.user_id == current_user.id
    )
    result = await db.execute(query)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    
    # Update fields dynamically
    update_data = appointment_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(appointment, key, value)
    
    appointment.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(appointment)
    return appointment

@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_appointment(
    appointment_id: int,
    current_user: ActiveUser,
    db: DBDep
):
    """Transitions an appointment status to 'cancelled'."""
    query = select(Appointment).where(
        Appointment.id == appointment_id,
        Appointment.user_id == current_user.id
    )
    result = await db.execute(query)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    
    appointment.status = 'cancelled'
    appointment.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    return None

@router.get("/slots/available", response_model=list[datetime])
async def get_available_slots(
    date: str,  # Format: YYYY-MM-DD
    db: DBDep
):
    """Calculates available 30-minute clinical windows for a given date."""
    try:
        target_date = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format")
    
    # Configuration for rural clinic working hours
    start_hour, end_hour = 9, 17
    slot_duration = 30 
    
    day_start = target_date.replace(hour=0, minute=0, second=0)
    day_end = target_date.replace(hour=23, minute=59, second=59)
    
    # Fetch all booked slots for the day
    query = select(Appointment.scheduled_date).where(
        and_(
            Appointment.scheduled_date >= day_start,
            Appointment.scheduled_date <= day_end,
            Appointment.status == 'scheduled'
        )
    )
    result = await db.execute(query)
    booked_times = {row[0] for row in result.all()}
    
    available_slots = []
    current_time = target_date.replace(hour=start_hour, minute=0)
    end_time = target_date.replace(hour=end_hour, minute=0)
    
    while current_time < end_time:
        if current_time not in booked_times:
            available_slots.append(current_time)
        current_time += timedelta(minutes=slot_duration)
    
    return available_slots