"""
Dependency injection for FastAPI authentication and authorization.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User
from app.core.security import decode_access_token
from app.core.config import settings

# OAuth2 scheme definition
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# Type Aliases for cleaner Dependency Injection (2026 Best Practice)
DBDep = Annotated[AsyncSession, Depends(get_db)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]

async def get_current_user(
    db: DBDep,
    token: TokenDep
) -> User:
    """
    Retrieves and validates the current authenticated user from the JWT.
    Updated to use SQLAlchemy 2.0 select statements.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    
    # Extract subject (user_id) from payload
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Modern SQLAlchemy 2.0 execution style
    query = select(User).where(User.id == int(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user account"
        )
    
    return user

# Annotated types for use in route endpoints
CurrentUser = Annotated[User, Depends(get_current_user)]

async def get_current_active_user(
    current_user: CurrentUser
) -> User:
    """Requirement check for active status."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

async def get_current_admin_user(
    current_user: CurrentUser
) -> User:
    """Requirement check for administrative privileges."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    return current_user