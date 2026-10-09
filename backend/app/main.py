"""
Rural AI Doctor - FastAPI Main Application
Integrated with Structured Logging, Sentry, LangSmith, and Global Error Handling.
"""

import time
import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
import sentry_sdk
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.fastapi import FastApiIntegration
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded

# Core and Config
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.production import run_production_checks
from app.api.v1 import api_router

# Database Initialization
from app.db.base import Base 
from app.db.session import engine 
from sqlalchemy import text

# Middleware and Handlers
from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler

# Setup professional logging
setup_logging("DEBUG" if settings.DEBUG else "INFO")
logger = logging.getLogger(__name__)

async def init_models():
    """
    Asynchronously synchronize the database schema.
    Uses 'run_sync' to allow the AsyncEngine to execute synchronous DDL commands.
    """
    try:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as ext_e:
            logger.warning(f"Could not create vector extension automatically: {ext_e}")

        async with engine.begin() as conn:
            # run_sync is required to use metadata.create_all with an AsyncEngine
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database schema synchronized")
    except Exception as e:
        logger.error(f"❌ Failed to sync database schema: {e}")
        # We don't want to crash on sync failure, especially in Render where tables might exist or we just want the UI to be available
        logger.warning("Continuing startup: Tables may already exist or DB is offline but app should run.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle.
    Handles startup sequence: Readiness checks -> DB Sync -> App Start.
    """
    logger.info(
        f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}",
        extra={"environment": settings.ENVIRONMENT, "debug": settings.DEBUG}
    )
    
    async def _startup_warmup() -> None:
        """Run heavy startup tasks in background so Render can mark the service healthy quickly."""
        try:
            await asyncio.wait_for(run_production_checks(), timeout=20)
            await asyncio.wait_for(init_models(), timeout=20)
        except asyncio.TimeoutError:
            logger.warning("Startup warmup timed out. Continuing with a live API; background deps may still be initializing.")
        except Exception as e:
            logger.error(f"System readiness checks failed: {e}")
            logger.warning("Ignoring startup failures. The app will start but might malfunction.")

    warmup_task = asyncio.create_task(_startup_warmup())

    yield
    
    # Shutdown logic
    if not warmup_task.done():
        warmup_task.cancel()
        try:
            await warmup_task
        except asyncio.CancelledError:
            logger.info("Startup warmup task cancelled during shutdown")
    logger.info(f"Cleanup: Shutting down {settings.PROJECT_NAME}")

# Sentry Initialization 
if getattr(settings, 'SENTRY_DSN', None):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1 if not settings.DEBUG else 1.0,
        integrations=[FastApiIntegration()],
        send_default_pii=False, 
        attach_stacktrace=True
    )
    logger.info("✅ Sentry error tracking enabled")

# Create FastAPI instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    # Documentation is disabled in production for security
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Prometheus Monitoring
Instrumentator().instrument(app).expose(app)

# Rate Limiter State
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Infrastructure Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS Configuration
# Combines localhost defaults with production origins from settings
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
] + ([str(origin) for origin in settings.BACKEND_CORS_ORIGINS] if hasattr(settings, "BACKEND_CORS_ORIGINS") else [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=(
        r"^https://rural-ai-doctor.*\.vercel\.app$"
        r"|^http://(localhost|127\.0\.0\.1|\d+\.\d+\.\d+\.\d+):3000$"
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time-MS"],
    max_age=3600, 
)

# Global Exception Handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Request Logging & High-Precision Timing Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Logs every clinical API request and measures processing latency."""
    start_time = time.perf_counter()
    client_ip = request.client.host if request.client else "unknown"
    
    response = await call_next(request)
    
    process_time = (time.perf_counter() - start_time) * 1000
    formatted_time = f"{process_time:.2f}"
    
    logger.info(
        f"Request: {request.method} {request.url.path} | Status: {response.status_code} | {formatted_time}ms",
        extra={
            "ip": client_ip,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": formatted_time
        }
    )
    
    response.headers["X-Process-Time-MS"] = formatted_time
    return response

# Route Registration
app.include_router(api_router, prefix=settings.API_V1_STR)

# Status & Diagnostic Endpoints
@app.head("/", tags=["Status"])
@app.get("/", tags=["Status"])
async def root():
    return {
        "message": "Rural AI Doctor API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled"
    }

@app.head("/health", tags=["Status"])
@app.get("/health", tags=["Status"])
async def health_check():
    """Simple health check for load balancers."""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/health/detailed", tags=["Status"])
async def health_detailed():
    """Comprehensive readiness probe for monitoring."""
    return {
        "status": "ok",
        "database": "connected",
        "vector_db": "ready",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/sentry-debug", tags=["Debug"])
async def trigger_error():
    """Manual trigger to verify Sentry connection is working."""
    if not settings.DEBUG:
        raise StarletteHTTPException(status_code=403, detail="Debug routes disabled")
    logger.warning("Sentry debug route triggered. Simulating a crash...")
    division_by_zero = 1 / 0
    return {"message": "This will not be reached"}

if __name__ == "__main__":
    # In production, uvicorn is typically called via the Render start command:
    # uvicorn app.main:app --host 0.0.0.0 --port $PORT
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)