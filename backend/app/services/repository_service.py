"""
Compatibility service for legacy repository management imports.

The canonical implementation now lives in `refactored_repository_service`.
This wrapper preserves the historical interface while delegating behavior to
the refactored service to avoid maintaining two diverging implementations.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.repository import (
    AddRepositoryRequest,
    DependencyInfo,
    RepositoryInfo,
    RepositoryResponse,
    RepositoryValidationResult,
)
from app.services.refactored_repository_service import create_repository_service


class RepositoryService:
    """Legacy-compatible wrapper around the refactored repository service."""

    def __init__(self, db: AsyncSession, github_token: Optional[str] = None):
        self._service = create_repository_service(db, github_token)

    def parse_repository_url(self, url: str) -> RepositoryInfo:
        return self._service.parse_repository_url(url)

    async def validate_repository(
        self,
        repo_info: RepositoryInfo,
        branch: Optional[str] = None,
    ) -> RepositoryValidationResult:
        result = await self._service.validate_repository_access(repo_info, branch)
        return RepositoryValidationResult(**result)

    async def fetch_dependencies(
        self,
        repo_info: RepositoryInfo,
        branch: str = "main",
    ) -> Optional[DependencyInfo]:
        return await self._service.fetch_dependencies(repo_info, branch)

    async def add_repository(
        self,
        request: AddRepositoryRequest,
        user_id: str,
    ) -> RepositoryResponse:
        result = await self._service.create_entity(request, user_id)
        if isinstance(result, RepositoryResponse):
            return result
        return RepositoryResponse(**result)
