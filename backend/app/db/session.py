from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings

# 1. Create the Async Engine
# Using NullPool is critical when connecting to an external pooler like Supavisor
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,  # Let Supabase handle the pooling logic
    connect_args={
        # Required when using PgBouncer in transaction/statement pool mode.
        "statement_cache_size": 0,
    }
)

# 2. Setup the Async Session Factory
# expire_on_commit=False prevents issues when accessing objects after a commit
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# 3. Asynchronous Dependency for FastAPI
async def get_db():
    """Dependency for providing a database session to FastAPI routes."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()

# Alias for compatibility with other parts of the app
SessionLocal = AsyncSessionLocal