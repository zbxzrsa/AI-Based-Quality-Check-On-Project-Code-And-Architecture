"""
Role-Based Access Control (RBAC) dependencies and decorators
"""
from typing import List, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgresql import get_db
from app.models import User, UserRole
from app.utils.jwt import verify_token


# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Handle case where credentials might be None (shouldn't happen with HTTPBearer)
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Verify token
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if token is blacklisted
    # stmt = select(TokenBlacklist).where(TokenBlacklist.token == token)
    # result = await db.execute(stmt)
    # if result.scalar_one_or_none():
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Token has been revoked",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    
    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current active user"""
    return current_user


class RoleChecker:
    """
    Dependency class for checking user roles
    """
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in self.allowed_roles]}"
            )
        return user


# Common role checkers
_all_roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.REVIEWER, UserRole.PROGRAMMER, UserRole.DEVELOPER, UserRole.COMPLIANCE_OFFICER, UserRole.VISITOR]
require_admin = RoleChecker([UserRole.ADMIN])
require_reviewer = RoleChecker(_all_roles)
require_compliance = RoleChecker(_all_roles)
require_manager = RoleChecker([UserRole.ADMIN, UserRole.MANAGER])


async def check_project_access(
    project_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> bool:
    """
    Check if user has access to a project
    
    Args:
        project_id: Project ID
        user: Current user
        db: Database session
        
    Returns:
        bool: True if user has access, False otherwise
        
    Raises:
        HTTPException: If user doesn't have access to the project
    """
    from app.models import Project, ProjectAccess
    
    # Admin users have access to all projects
    if user.role == UserRole.ADMIN:
        return True
        
    # Check if user has explicit access to the project
    result = await db.execute(
        select(ProjectAccess)
        .where(ProjectAccess.project_id == project_id)
        .where(ProjectAccess.user_id == user.id)
        .where(ProjectAccess.revoked_at.is_(None))
    )
    if result.scalars().first() is not None:
        return True
    
    # Check if user owns the project
    stmt = select(Project).where(
        Project.id == project_id,
        Project.owner_id == user.id
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project"
        )
    
    return True
