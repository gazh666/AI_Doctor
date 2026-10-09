"""
Security utilities for authentication and password management.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing configuration using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a secure hash from a plain text password."""
    return pwd_context.hash(password)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    Uses timezone-aware UTC objects (2026 standard) instead of deprecated utcnow().
    """
    to_encode = data.copy()
    
    # Calculate expiration using timezone-aware UTC
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) #
    
    to_encode.update({"exp": expire})
    
    return jwt.encode(
        to_encode, 
        settings.SECRET_KEY, # 
        algorithm=settings.ALGORITHM #
    )


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT token; returns the payload if valid."""
    try:
        return jwt.decode(
            token, 
            settings.SECRET_KEY, #
            algorithms=[settings.ALGORITHM] #
        )
    except (JWTError, ValueError):
        return None


def create_password_reset_token(email: str) -> str:
    """Generate a specialized short-lived token for password resets."""
    expires_delta = timedelta(hours=24)
    data = {"sub": email, "type": "password_reset"}
    return create_access_token(data, expires_delta)


def verify_password_reset_token(token: str) -> Optional[str]:
    """Validate a reset token and return the associated email address."""
    payload = decode_access_token(token)
    if payload and payload.get("type") == "password_reset":
        return str(payload.get("sub"))
    return None