"""
One-time admin password reset utility.

Usage examples:
  python scripts/reset_admin_password.py --email admin@rural-ai.doc --password "NewStrongPass123!"
  python scripts/reset_admin_password.py --email admin@rural-ai.doc
"""

import argparse
import asyncio
import getpass
import logging
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure `app` package is importable when executing `python scripts/...`.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import get_password_hash
from app.db.models import User
from app.db.session import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reset_admin_password(email: str, password: str, create_if_missing: bool = True) -> None:
    """Reset password for an admin user; optionally create the user if not found."""
    async with AsyncSessionLocal() as session:
        await _reset_in_session(session, email=email, password=password, create_if_missing=create_if_missing)


async def _reset_in_session(
    session: AsyncSession,
    email: str,
    password: str,
    create_if_missing: bool,
) -> None:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        if not create_if_missing:
            raise ValueError(f"Admin user not found for email: {email}")

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name="System Administrator",
            role="admin",
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        logger.info("Admin user created and password initialized for %s", email)
        return

    user.hashed_password = get_password_hash(password)
    user.role = "admin"
    user.is_active = True
    await session.commit()
    logger.info("Admin password reset completed for %s", email)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset/create admin credentials")
    parser.add_argument(
        "--email",
        default="admin@rural-ai.doc",
        help="Admin email address (default: admin@rural-ai.doc)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="New admin password. If omitted, script will prompt securely.",
    )
    parser.add_argument(
        "--no-create",
        action="store_true",
        help="Do not create user if email is missing.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    password = args.password or getpass.getpass("Enter new admin password: ")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    asyncio.run(
        reset_admin_password(
            email=args.email,
            password=password,
            create_if_missing=not args.no_create,
        )
    )


if __name__ == "__main__":
    main()
