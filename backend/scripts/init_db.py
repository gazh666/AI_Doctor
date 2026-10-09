"""
Database initialization script for Rural AI Doctor.
Synchronizes schema, enables vector extensions, and seeds initial admin data.
"""

import asyncio
import logging
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports from your existing project structure
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
from app.db.models import (
    User,
    Patient,
    Diagnosis,
    MedicalDocument,
    MedicalEvidenceSource,
    ChatHistory,
    ImageAnalysis,
    VoiceInteraction,
    Appointment,
    UserActivity,
    UsageMetrics
)
from app.services.rag.source_catalog import default_trusted_sources, embed_text

# Professional logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db() -> None:
    """
    Main entry point for database initialization.
    Handles extension setup, schema creation, and admin seeding.
    """
    logger.info(f"🚀 Initializing database for {settings.PROJECT_NAME}...")

    try:
        # 1. Enable pgvector extension (Required for RAG features)
        async with engine.begin() as conn:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                logger.info("✅ pgvector extension enabled")
            except Exception as ext_e:
                logger.warning(f"Note: Vector extension setup skipped or failed: {ext_e}")

            # 2. Synchronize all tables defined in Base
            # run_sync is required to map synchronous DDL commands to an async engine
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database schema synchronized successfully")

        # 3. Seed initial administrative user
        async with AsyncSessionLocal() as session:
            await seed_admin_user(session)
            await seed_trusted_sources(session)

        logger.info("🎉 Database initialization complete!")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

async def seed_admin_user(session: AsyncSession) -> None:
    """
    Ensures a default administrative user exists for initial system access.
    """
    admin_email = "admin@rural-ai.doc"
    
    # Modern SQLAlchemy 2.0 select statement
    query = select(User).where(User.email == admin_email)
    result = await session.execute(query)
    admin_exists = result.scalar_one_or_none()

    if not admin_exists:
        logger.info(f"Creating default admin: {admin_email}...")
        new_admin = User(
            email=admin_email,
            hashed_password=get_password_hash("AdminSecurePassword2026"),
            full_name="System Administrator",
            role="admin",
            is_active=True,
            is_verified=True
        )
        session.add(new_admin)
        await session.commit()
        logger.info("✅ Admin user created successfully")
    else:
        logger.info("ℹ️ Admin user already exists; skipping seed")


async def seed_trusted_sources(session: AsyncSession) -> None:
    """Seed a baseline set of trusted clinical references for grounded retrieval."""
    defaults = default_trusted_sources()
    inserted = 0

    for item in defaults:
        existing = await session.execute(
            select(MedicalEvidenceSource.id).where(
                MedicalEvidenceSource.provider == item["provider"],
                MedicalEvidenceSource.title == item["title"],
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        source_text = f"{item['title']}\n{item['excerpt']}\nTags: {', '.join(item.get('condition_tags', []))}"
        embedding = await embed_text(source_text, task_type="retrieval_document")
        session.add(
            MedicalEvidenceSource(
                provider=item["provider"],
                title=item["title"],
                url=item["url"],
                excerpt=item["excerpt"],
                condition_tags=item.get("condition_tags", []),
                evidence_level=item.get("evidence_level"),
                published_at=item.get("published_at"),
                last_verified_at=item.get("last_verified_at") or item.get("published_at"),
                embedding=embedding,
                metadata_json={"seeded": True},
                is_active=True,
            )
        )
        inserted += 1

    if inserted:
        await session.commit()
        logger.info(f"✅ Seeded {inserted} trusted medical reference sources")
    else:
        logger.info("ℹ️ Trusted medical references already present; skipping seed")

if __name__ == "__main__":
    # Running the initialization in the async event loop
    asyncio.run(init_db())