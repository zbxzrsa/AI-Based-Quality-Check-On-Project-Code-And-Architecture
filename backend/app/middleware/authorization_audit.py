"""
Authorization audit middleware for logging 403 errors.

Validates Requirement 8.8: Log all authorization failure attempts
"""
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.audit_service import UnifiedAuditService as AuditService
from app.database.postgresql import get_db

logger = logging.getLogger(__name__)


class AuthorizationAuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log authorization failures (403 errors).
    
    Captures all 403 responses and logs them to the audit system
    with user information, resource details, and client information.
    
    Validates Requirement 8.8
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log authorization failures.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response
        """
        # Process the request
        response = await call_next(request)
        
        # Check if this is an authorization failure (403)
        if response.status_code == 403:
            # Extract user information from request state (set by auth middleware)
            user = getattr(request.state, 'user', None)
            
            if user:
                # Get client information
                ip_address = request.client.host if request.client else "0.0.0.0"
                user_agent = request.headers.get("User-Agent")
                
                # Extract resource information from request
                resource_type = self._extract_resource_type(request.url.path)
                resource_id = self._extract_resource_id(request.url.path)
                
                # Log authorization failure asynchronously
                try:
                    # Get database session
                    async for db in get_db():
                        await AuditService.log_authz_failure(
                            db=db,
                            user_id=user.id,
                            email=user.email,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            required_permission=None  # Could be extracted from exception if available
                        )
                        break  # Only need one iteration
                except Exception as e:
                    # Graceful degradation - log error but don't fail the request
                    logger.error(
                        f"Failed to log authorization failure: {e}",
                        extra={
                            "user_id": str(user.id),
                            "email": user.email,
                            "path": request.url.path,
                            "error": str(e)
                        }
                    )
        
        return response
    
    @staticmethod
    def _extract_resource_type(path: str) -> str:
        """
        Extract resource type from URL path.
        
        Examples:
            /api/v1/projects/123 -> projects
            /api/v1/users/456/settings -> users
            
        Args:
            path: URL path
            
        Returns:
            Resource type string
        """
        parts = path.strip('/').split('/')
        
        # Look for resource type after 'api/v1' or similar
        for i, part in enumerate(parts):
            if part in ['api', 'v1', 'v2']:
                continue
            # First non-version part is likely the resource type
            if not part.isdigit() and '-' not in part:
                return part
        
        return "unknown"
    
    @staticmethod
    def _extract_resource_id(path: str) -> str:
        """
        Extract resource ID from URL path.
        
        Examples:
            /api/v1/projects/123 -> 123
            /api/v1/users/456/settings -> 456
            
        Args:
            path: URL path
            
        Returns:
            Resource ID string or None
        """
        parts = path.strip('/').split('/')
        
        # Look for UUID or numeric ID in path
        for part in parts:
            # Check if it looks like a UUID or ID
            if len(part) == 36 and '-' in part:  # UUID format
                return part
            if part.isdigit():  # Numeric ID
                return part
        
        return None
