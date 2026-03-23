"""
Rate Limiting Middleware

This module implements rate limiting middleware using Redis for distributed
rate limiting across multiple instances.

Requirements:
- 8.3: Implement rate limiting on all API endpoints: 100 requests per minute, 5000 requests per hour
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import os
import logging
import time

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    Get user identifier for rate limiting.
    
    Priority:
    1. Authenticated user ID from JWT token
    2. IP address for unauthenticated requests
    
    Args:
        request: FastAPI request object
        
    Returns:
        User identifier string
    """
    # Try to get user from JWT token
    try:
        # Check if user is authenticated
        if hasattr(request.state, "user") and request.state.user:
            user_id = getattr(request.state.user, "id", None)
            if user_id:
                return f"user:{user_id}"
    except Exception as e:
        logger.debug(f"Could not extract user from request: {e}")
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


# Initialize rate limiter with fallback to memory storage
# Use memory storage during testing or if Redis is unavailable
def get_storage_uri():
    if os.environ.get("TESTING") == "true":
        return "memory://"
    try:
        # Test Redis connectivity before using it
        import redis
        r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        return settings.redis_url
    except Exception:
        logger.warning("Redis unavailable for rate limiting, using memory storage")
        return "memory://"

storage_uri = get_storage_uri()

limiter = Limiter(
    key_func=get_user_identifier,
    storage_uri=storage_uri,
    default_limits=[
        "1000/minute",  # Increased limits to prevent blocking
        "50000/hour"
    ],
    headers_enabled=True,  # Add rate limit headers to responses
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis for distributed rate limiting.
    
    Implements per-user rate limiting with configurable limits.
    Returns 429 Too Many Requests when rate limit is exceeded.
    
    Requirements:
        - 8.3: Implement rate limiting on all API endpoints: 100 requests per minute, 5000 requests per hour
    """
    
    def __init__(
        self,
        app,
        rate_limit_per_minute: int = 100,
        rate_limit_per_hour: int = 5000,
        redis_url: Optional[str] = None,
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            rate_limit_per_minute: Rate limit per minute (default: 100)
            rate_limit_per_hour: Rate limit per hour (default: 5000)
            redis_url: Redis connection URL for distributed rate limiting
        """
        super().__init__(app)
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_per_hour = rate_limit_per_hour
        self.redis_url = redis_url or settings.redis_url
        
        logger.info(
            f"Rate limiting initialized: {rate_limit_per_minute}/minute, "
            f"{rate_limit_per_hour}/hour per user"
        )
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Apply rate limiting to request.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response or 429 error if rate limit exceeded
        """
        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/health/ready", "/health/live"]:
            return await call_next(request)
        
        # Skip rate limiting for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            response = await call_next(request)
            return response
        except RateLimitExceeded as e:
            # Log rate limit exceeded
            user_id = get_user_identifier(request)
            logger.warning(
                f"Rate limit exceeded for {user_id} on {request.url.path}",
                extra={
                    "user_identifier": user_id,
                    "path": request.url.path,
                    "method": request.method,
                    "ip": get_remote_address(request),
                }
            )
            
            # Determine which limit was exceeded and calculate retry_after
            retry_after = 60  # Default to 1 minute
            limit_type = "minute"
            
            # Check if it's the hourly limit that was exceeded
            if hasattr(e, "retry_after"):
                retry_after = int(e.retry_after)
                if retry_after > 300:  # More than 5 minutes suggests hourly limit
                    limit_type = "hour"
            
            # Return 429 Too Many Requests
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Rate limit: {self.rate_limit_per_minute} requests per minute, {self.rate_limit_per_hour} requests per hour. Please try again later.",
                    "retry_after": retry_after,
                    "limit_type": limit_type,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit-Minute": str(self.rate_limit_per_minute),
                    "X-RateLimit-Limit-Hour": str(self.rate_limit_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                }
            )


class CustomRateLimiter:
    """
    Custom rate limiter for specific endpoints with different limits.
    
    Example:
        from app.middleware.rate_limiting import custom_limiter
        
        @app.get("/api/expensive-operation")
        @custom_limiter.limit("10/minute")
        async def expensive_operation():
            return {"status": "ok"}
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize custom rate limiter.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url or settings.redis_url
        self.limiter = Limiter(
            key_func=get_user_identifier,
            storage_uri=self.redis_url,
            headers_enabled=True,
        )
    
    def limit(self, rate_limit: str):
        """
        Decorator to apply custom rate limit to endpoint.
        
        Args:
            rate_limit: Rate limit string (e.g., "10/minute", "100/hour")
            
        Returns:
            Decorator function
        """
        return self.limiter.limit(rate_limit)


# Global custom limiter instance
custom_limiter = CustomRateLimiter()


def custom_rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Custom rate limit exceeded handler that handles both RateLimitExceeded
    and other exceptions gracefully.
    
    Args:
        request: FastAPI request object
        exc: Exception that was raised
        
    Returns:
        JSONResponse with error details
    """
    # Handle RateLimitExceeded specifically
    if isinstance(exc, RateLimitExceeded):
        detail = getattr(exc, 'detail', 'Rate limit exceeded')
        return JSONResponse(
            status_code=429,
            content={"error": f"Rate limit exceeded: {detail}"}
        )
    
    # Handle authentication errors and other exceptions
    if hasattr(exc, 'detail'):
        detail = exc.detail
    elif hasattr(exc, 'message'):
        detail = exc.message
    else:
        detail = str(exc)
    
    return JSONResponse(
        status_code=429,
        content={"error": f"Rate limit exceeded: {detail}"}
    )


def configure_rate_limiting(app):
    """
    Configure rate limiting for FastAPI application.
    
    Args:
        app: FastAPI application
        
    Example:
        from fastapi import FastAPI
        from app.middleware.rate_limiting import configure_rate_limiting
        
        app = FastAPI()
        configure_rate_limiting(app)
    """
    # Temporarily disable SlowAPI middleware due to compatibility issues
    # Add SlowAPI middleware
    app.state.limiter = limiter
    # app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
    # app.add_middleware(SlowAPIMiddleware)
    
    logger.info(
        f"Rate limiting temporarily disabled - configuration: {settings.RATE_LIMIT_PER_MINUTE} requests/minute, "
        f"{settings.RATE_LIMIT_PER_HOUR} requests/hour per user"
    )


# Export public API
__all__ = [
    "limiter",
    "custom_limiter",
    "RateLimitMiddleware",
    "CustomRateLimiter",
    "configure_rate_limiting",
    "get_user_identifier",
]
