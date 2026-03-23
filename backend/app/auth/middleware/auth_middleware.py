"""
Authorization middleware for FastAPI endpoints.
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services import TokenPayload
from app.auth.services.rbac_service import RBACService
from app.auth.models import Role, Permission
from app.database.postgresql import get_db


# HTTP Bearer token security scheme
security = HTTPBearer()


class AuthMiddleware:
    """Middleware for authentication and authorization."""
    
    @staticmethod
    async def authenticate_token(request: Request, credentials: HTTPAuthorizationCredentials) -> TokenPayload:
        """
        Middleware to validate JWT token from Authorization header.
        Checks token signature, expiration, and Redis blacklist.
        
        Args:
            request: FastAPI request object
            credentials: HTTP Bearer credentials
            
        Returns:
            TokenPayload if token is valid and not revoked
            
        Raises:
            HTTPException: 401 if token is invalid, expired, or revoked
        """
        from app.utils.jwt import verify_token_with_revocation
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = credentials.credentials
        
        # Validate token and check if it's been revoked
        payload_dict = await verify_token_with_revocation(token, token_type="access")
        
        if not payload_dict:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Convert dict to TokenPayload
        payload = TokenPayload.from_dict(payload_dict)
        
        # Store user info in request state for downstream handlers
        request.state.user = payload
        
        return payload
    
    @staticmethod
    def check_role(required_role: Role):
        """
        Middleware factory to check if user has required role.
        
        Args:
            required_role: Role required to access the endpoint
            
        Returns:
            Middleware function that checks role
        """
        async def role_checker(request: Request, credentials: HTTPAuthorizationCredentials) -> TokenPayload:
            # First authenticate the token
            payload = await AuthMiddleware.authenticate_token(request, credentials)
            
            # Check if user's role matches required role
            user_role = Role(payload.role)
            
            if user_role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This action requires {required_role.value} role"
                )
            
            return payload
        
        return role_checker
    
    @staticmethod
    def check_permission(required_permission: Permission):
        """
        Middleware factory to check if user has required permission.
        
        Args:
            required_permission: Permission required to access the endpoint
            
        Returns:
            Middleware function that checks permission
        """
        async def permission_checker(
            request: Request, 
            credentials: HTTPAuthorizationCredentials,
            db: AsyncSession = Depends(get_db)
        ) -> TokenPayload:
            # First authenticate the token
            payload = await AuthMiddleware.authenticate_token(request, credentials)
            
            # Check if user has the required permission
            has_perm = await RBACService.has_permission(db, payload.user_id, required_permission)
            
            if not has_perm:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to perform this action"
                )
            
            return payload
        
        return permission_checker
    
    @staticmethod
    def check_project_access(required_permission: Permission):
        """
        Middleware factory to check if user can access a specific project.
        
        Args:
            required_permission: Permission required for the project operation
            
        Returns:
            Middleware function that checks project access
        """
        async def project_access_checker(
            request: Request, 
            credentials: HTTPAuthorizationCredentials,
            db: AsyncSession
        ) -> TokenPayload:
            # First authenticate the token
            payload = await AuthMiddleware.authenticate_token(request, credentials)
            
            # Extract project_id from path parameters
            project_id = request.path_params.get("project_id")
            
            if not project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project ID is required"
                )
            
            # Check if user can access the project
            can_access = await RBACService.can_access_project(
                db, 
                payload.user_id, 
                project_id, 
                required_permission
            )
            
            if not can_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this project"
                )
            
            return payload
        
        return project_access_checker


# Convenience functions for dependency injection
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenPayload:
    """Dependency to get current authenticated user."""
    return await AuthMiddleware.authenticate_token(request, credentials)


def require_role(role: Role):
    """Dependency to require specific role."""
    checker = AuthMiddleware.check_role(role)
    
    async def _require_role(
        request: Request, 
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> TokenPayload:
        return await checker(request, credentials)
    
    return _require_role


def require_permission(permission: Permission):
    """Dependency to require specific permission."""
    
    async def _require_permission(
        request: Request, 
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
    ) -> TokenPayload:
        # First authenticate the token
        payload = await AuthMiddleware.authenticate_token(request, credentials)
        
        # Check if user has the required permission
        has_perm = await RBACService.has_permission(db, payload.user_id, permission)
        
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )
        
        return payload
    
    return _require_permission


def require_project_access(permission: Permission):
    """Dependency to require project access with specific permission."""
    checker = AuthMiddleware.check_project_access(permission)
    
    async def _require_project_access(
        request: Request, 
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
    ) -> TokenPayload:
        return await checker(request, credentials, db)
    
    return _require_project_access
