"""
Role-Based Access Control (RBAC) dependencies and decorators
"""

from functools import wraps
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgresql import get_db
from app.domain.services import ICacheService, IGitHubService, IGraphService, ILLMService
from app.infrastructure.container import DIContainer, get_container
from app.models import User, UserRole
from app.utils.jwt import verify_token

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Get current active user"""
    return current_user


class RoleChecker:
    """
    Dependency class for checking user roles
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in self.allowed_roles]}",
            )
        return user


# Common role checkers - simplified to single user role
require_admin = RoleChecker([UserRole.user])
require_reviewer = RoleChecker([UserRole.user])
require_compliance = RoleChecker([UserRole.user])
require_manager = RoleChecker([UserRole.user])


async def check_project_access(
    project_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]
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

    # All users have access to all projects
    if user.role == UserRole.user:
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
    stmt = select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this project")

    return True


# =============================================================================
# Dependency Injection Dependencies
# =============================================================================


def get_github_service(container: DIContainer = Depends(get_container)) -> IGitHubService:
    """Dependency to get GitHub service"""
    try:
        return container.resolve(IGitHubService)
    except KeyError:
        raise HTTPException(status_code=500, detail="GitHub service not configured")


def get_llm_service(container: DIContainer = Depends(get_container)) -> ILLMService:
    """Dependency to get LLM service"""
    try:
        return container.resolve(ILLMService)
    except KeyError:
        raise HTTPException(status_code=500, detail="LLM service not configured")


def get_cache_service(container: DIContainer = Depends(get_container)) -> ICacheService:
    """Dependency to get cache service"""
    try:
        return container.resolve(ICacheService)
    except KeyError:
        raise HTTPException(status_code=500, detail="Cache service not configured")


def get_graph_service(container: DIContainer = Depends(get_container)) -> IGraphService:
    """Dependency to get graph service"""
    try:
        return container.resolve(IGraphService)
    except KeyError:
        raise HTTPException(status_code=500, detail="Graph service not configured")


def require_services(*service_types):
    """Decorator to require multiple services"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            container = get_container()
            for service_type in service_types:
                if service_type not in kwargs:
                    try:
                        kwargs[service_type.__name__] = container.resolve(service_type)
                    except KeyError:
                        raise HTTPException(status_code=500, detail=f"Service {service_type.__name__} not configured")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class ServiceLocator:
    """Service locator pattern for complex dependency resolution"""

    def __init__(self, container: DIContainer = Depends(get_container)):
        self._container = container

    def get(self, service_type: type):
        try:
            return self._container.resolve(service_type)
        except KeyError:
            raise HTTPException(status_code=500, detail=f"Service {service_type.__name__} not configured")


async def setup_container(container: DIContainer) -> None:
    """Setup and configure the DI container during startup"""
    from app.infrastructure.external import (
        GitHubService,
        LLMServiceImpl,
        RedisCacheService,
    )

    container.register(IGitHubService, GitHubService, singleton=True)
    container.register(ICacheService, RedisCacheService, singleton=True)
    container.register(ILLMService, LLMServiceImpl, singleton=True)
