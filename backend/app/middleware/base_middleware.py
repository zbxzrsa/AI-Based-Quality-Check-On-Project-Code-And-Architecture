"""
Base middleware class with common patterns.

This module provides a base class for middleware following the DRY principle.
"""
from typing import Callable, Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)


class BaseConfigurableMiddleware(BaseHTTPMiddleware):
    """
    Base middleware with configuration support.
    
    Provides:
    - Configuration management
    - Logging setup
    - Common initialization patterns
    """
    
    def __init__(
        self,
        app,
        config: Optional[Dict[str, Any]] = None,
        middleware_name: str = "Middleware"
    ):
        """
        Initialize middleware with configuration.
        
        Args:
            app: ASGI application
            config: Optional configuration dictionary
            middleware_name: Name for logging purposes
        """
        super().__init__(app)
        self.config = config or {}
        self.middleware_name = middleware_name
        
        logger.info(f"{self.middleware_name} initialized with config: {self.config}")
    
    def should_skip_path(self, path: str, skip_paths: list[str]) -> bool:
        """
        Check if path should be skipped.
        
        Args:
            path: Request path
            skip_paths: List of paths to skip
            
        Returns:
            True if path should be skipped
        """
        return path in skip_paths
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Override in subclass to implement middleware logic.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response
        """
        return await call_next(request)


class BaseMetricsMiddleware(BaseHTTPMiddleware):
    """
    Base middleware for metrics collection.
    
    Provides:
    - Path normalization
    - Common metrics patterns
    """
    
    def __init__(self, app):
        """
        Initialize metrics middleware.
        
        Args:
            app: ASGI application
        """
        super().__init__(app)
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize endpoint path for metrics.
        
        Removes IDs and query parameters to group similar endpoints.
        
        Args:
            path: Original request path
            
        Returns:
            Normalized path
        """
        # Remove query parameters
        if '?' in path:
            path = path.split('?')[0]
        
        # Replace UUIDs with placeholder
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        path = re.sub(uuid_pattern, '{id}', path, flags=re.IGNORECASE)
        
        # Replace numeric IDs with placeholder
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Override in subclass to implement metrics logic.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response
        """
        return await call_next(request)
