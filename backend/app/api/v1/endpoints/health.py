"""
Health check and monitoring endpoints.
Integrated with Prometheus metrics and asynchronous database probes.
"""

import psutil
import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.db.session import get_db
from app.core.config import settings
from app.core.metrics import metrics

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health", tags=["System"])
async def health_check():
    """Basic service health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@router.get("/health/detailed", tags=["System"])
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check including database and AI service connectivity."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "checks": {}
    }
    
    # Database connectivity check
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "type": "PostgreSQL with pgvector"
        }
    except Exception as e:
        logger.error(f"Health Check Failure - Database: {str(e)}")
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": "Database unreachable"
        }
    
    # AI Service configuration check
    health_status["checks"]["gemini_api"] = {
        "status": "configured" if settings.GOOGLE_API_KEY else "not_configured",
        "model": settings.GEMINI_MODEL
    }
    
    return health_status

@router.get("/metrics", tags=["Monitoring"])
async def get_prometheus_metrics():
    """
    Exposes application metrics in Prometheus format.
    Includes system resource utilization and clinical feature usage.
    """
    # Capture system resource snapshots
    cpu_usage = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    
    # Note: Custom clinical metrics are automatically included 
    # when generate_latest() is called if they are registered globally.
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@router.get("/stats", tags=["Monitoring"])
async def get_system_stats():
    """Provides a JSON snapshot of system resources for dashboarding."""
    memory = psutil.virtual_memory()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            }
        },
        "version": settings.VERSION
    }

@router.get("/ready", tags=["System"])
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe for orchestration (Railway/K8s)."""
    try:
        await db.execute(text("SELECT 1"))
        if not settings.GOOGLE_API_KEY:
            return Response(status_code=503, content="AI Service Not Configured")
        return {"status": "ready"}
    except Exception as e:
        return Response(status_code=503, content=f"Service Not Ready: {str(e)}")

@router.get("/live", tags=["System"])
async def liveness_check():
    """Liveness probe for orchestration."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}