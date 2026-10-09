
import logging
import traceback
from typing import Any, Dict

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.monitoring import monitoring


logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
  
    logger.warning(
        f"HTTP {exc.status_code} error at {request.url.path}: {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path,
                "type": "http_exception"
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:

    error_details = exc.errors()
    logger.warning(
        f"Validation error at {request.url.path}",
        extra={
            "path": request.url.path,
            "errors": error_details
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Input validation failed",
                "details": error_details,
                "path": request.url.path,
                "type": "validation_error"
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:

    tb = traceback.format_exc()
    
    #  Structured Logging
    logger.error(
        f"Unhandled server error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "traceback": tb
        }
    )
    
    #  LangSmith Monitoring
    monitoring.log_error(exc, {
        "path": request.url.path,
        "method": request.method,
        "traceback_summary": tb.splitlines()[-1] if tb else "No traceback"
    })
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "An unexpected server error occurred",
                "path": request.url.path,
                "type": "internal_server_error"
            }
        }
    )