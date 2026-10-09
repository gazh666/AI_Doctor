"""
Rate limiting middleware for the Rural AI Doctor backend.
Protects the diagnostic API from abuse and controls Google API costs.
"""

import logging
from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings

# Structured logger
logger = logging.getLogger(__name__)

storage_uri = getattr(settings, "REDIS_URL", "memory://")

# Create the global limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri=storage_uri,
   
    storage_options={"socket_connect_timeout": 1} if storage_uri.startswith("redis") else {}
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:

    client_ip = request.client.host if request.client else "unknown"
    
    logger.warning(
        f"Rate limit exceeded: {client_ip} requested {request.url.path}",
        extra={
            "ip": client_ip,
            "path": request.url.path,
            "limit": exc.detail
        }
    )
    
    return _rate_limit_exceeded_handler(request, exc)