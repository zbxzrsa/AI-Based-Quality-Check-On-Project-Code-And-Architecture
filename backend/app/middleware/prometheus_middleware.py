"""
Prometheus middleware for automatic HTTP metrics collection.

This middleware automatically collects metrics for all HTTP requests:
- Request duration
- Request count
- Requests in progress
- Error rates

Implements Requirement 7.3: Collect metrics for API response times, error rates, and throughput.
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.prometheus_metrics import (
    http_requests_in_progress,
    record_http_request,
    record_exception
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect Prometheus metrics for HTTP requests.
    
    Automatically tracks:
    - Request duration (histogram)
    - Request count (counter)
    - Requests in progress (gauge)
    - Error rates (counter)
    """
    
    def __init__(self, app: ASGIApp):
        """
        Initialize the middleware.
        
        Args:
            app: ASGI application
        """
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and collect metrics.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
        """
        # Extract request info
        method = request.method
        path = request.url.path
        
        # Normalize endpoint path (remove IDs and query params)
        endpoint = self._normalize_path(path)
        
        # Track requests in progress
        http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint
        ).inc()
        
        # Start timing
        start_time = time.time()
        status_code = 500  # Default to server error
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            return response
            
        except Exception as exc:
            # Record exception
            exception_type = type(exc).__name__
            record_exception(exception_type, endpoint)
            raise
            
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration
            )
            
            # Decrement in-progress counter
            http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize URL path to reduce cardinality of metrics.
        
        Replaces dynamic segments (IDs, UUIDs) with placeholders.
        
        Args:
            path: Original URL path
            
        Returns:
            str: Normalized path
            
        Examples:
            /api/v1/users/123 -> /api/v1/users/{id}
            /api/v1/projects/abc-def-123/analysis -> /api/v1/projects/{id}/analysis
        """
        import re
        
        # Replace UUIDs (must come first to avoid partial matches)
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs (pure numbers)
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        # Replace alphanumeric IDs (8+ chars containing both letters AND digits)
        # This matches: abc123def456, test123, user_456, but NOT: projects, analysis, users
        path = re.sub(r'/(?=[a-zA-Z0-9_-]*\d)(?=[a-zA-Z0-9_-]*[a-zA-Z])[a-zA-Z0-9_-]{8,}(?=/|$)', '/{id}', path)
        
        return path


def configure_prometheus_middleware(app):
    """
    Configure Prometheus middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(PrometheusMiddleware)
