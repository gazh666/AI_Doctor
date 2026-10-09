"""
Authentication endpoints for Rural AI Doctor.
Refactored for FastAPI 0.115+ and SQLAlchemy 2.0+ standards.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User
from app.schemas.auth import (
    UserCreate,
    UserInDB,
    Token,
    PasswordReset,
    PasswordResetConfirm,
    PasswordChange,
    UserUpdate
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_password_reset_token,
    verify_password_reset_token
)
from app.core.deps import CurrentUser, get_current_active_user
from app.core.config import settings
from app.services.email.email_service import email_service

router = APIRouter()
logger = logging.getLogger(__name__)

# Reusable dependency types
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: DBDep, background_tasks: BackgroundTasks) -> Any:
    """Register a new patient account using async SQLAlchemy 2.0."""
    # Check for existing user using modern select()
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered in our system."
        )
    
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role="patient",
        is_active=True,
        is_verified=False
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send welcome notification without delaying API response.
    background_tasks.add_task(
        email_service.send_welcome_email,
        user.email,
        user.full_name or user.email,
    )
    
    logger.info(f"Account created: {user.email}")
    return user


@router.post("/login", response_model=Token)
async def login(
    db: DBDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Any:
    """Authenticate user and return a timezone-aware JWT."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is disabled")
    
    # Update last login using timezone-aware UTC (2026 standard)
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    
    access_token = create_access_token(
        data={"sub": str(user.id)}, 
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: CurrentUser) -> Any:
    """Return the authenticated user's profile information."""
    return current_user


@router.put("/me", response_model=UserInDB)
async def update_user_me(
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: DBDep
) -> Any:
    """Perform a partial update on the current user's profile."""
    update_data = user_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: CurrentUser,
    db: DBDep
) -> Any:
    """Update password after verifying the existing one."""
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid existing password")
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    return {"message": "Password updated successfully"}


@router.post("/forgot-password")
async def forgot_password(password_reset: PasswordReset, db: DBDep, background_tasks: BackgroundTasks) -> Any:
    """Initiate the password recovery process."""
    result = await db.execute(select(User).where(User.email == password_reset.email))
    user = result.scalar_one_or_none()
    
    if user:
        reset_token = create_password_reset_token(user.email)
        background_tasks.add_task(
            email_service.send_password_reset_email,
            user.email,
            reset_token,
        )
        logger.info(f"Recovery token generated for: {user.email}")
    
    # Always return a success message to prevent account enumeration
    return {"message": "If the account exists, recovery instructions have been sent."}