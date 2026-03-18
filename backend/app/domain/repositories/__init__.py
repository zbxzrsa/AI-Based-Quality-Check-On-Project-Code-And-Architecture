"""
Domain Layer - Repository Interfaces

These interfaces define the contracts for data access.
Infrastructure layer implements these interfaces.
Domain and Application layers depend on these abstractions (DIP).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from uuid import UUID


class IUserRepository(ABC):
    """User repository interface - defines contract for user data access"""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Any | None:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Any | None:
        """Get user by email"""
        pass

    @abstractmethod
    async def create(self, user_data: dict[str, Any]) -> Any:
        """Create new user"""
        pass

    @abstractmethod
    async def update(self, user_id: UUID, user_data: dict[str, Any]) -> Any | None:
        """Update user"""
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete user"""
        pass

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Any]:
        """List all users"""
        pass


class IProjectRepository(ABC):
    """Project repository interface"""

    @abstractmethod
    async def get_by_id(self, project_id: UUID) -> Any | None:
        """Get project by ID"""
        pass

    @abstractmethod
    async def get_by_owner(self, owner_id: UUID) -> list[Any]:
        """Get projects by owner"""
        pass

    @abstractmethod
    async def create(self, project_data: dict[str, Any]) -> Any:
        """Create new project"""
        pass

    @abstractmethod
    async def update(self, project_id: UUID, project_data: dict[str, Any]) -> Any | None:
        """Update project"""
        pass

    @abstractmethod
    async def delete(self, project_id: UUID) -> bool:
        """Delete project"""
        pass


class IPullRequestRepository(ABC):
    """Pull Request repository interface"""

    @abstractmethod
    async def get_by_id(self, pr_id: UUID) -> Any | None:
        """Get PR by ID"""
        pass

    @abstractmethod
    async def get_by_project(self, project_id: UUID) -> list[Any]:
        """Get PRs by project"""
        pass

    @abstractmethod
    async def create(self, pr_data: dict[str, Any]) -> Any:
        """Create new PR"""
        pass

    @abstractmethod
    async def update(self, pr_id: UUID, pr_data: dict[str, Any]) -> Any | None:
        """Update PR"""
        pass


class ICodeReviewRepository(ABC):
    """Code Review repository interface"""

    @abstractmethod
    async def get_by_id(self, review_id: UUID) -> Any | None:
        """Get review by ID"""
        pass

    @abstractmethod
    async def get_by_pull_request(self, pr_id: UUID) -> list[Any]:
        """Get reviews by PR"""
        pass

    @abstractmethod
    async def create(self, review_data: dict[str, Any]) -> Any:
        """Create new review"""
        pass

    @abstractmethod
    async def update(self, review_id: UUID, review_data: dict[str, Any]) -> Any | None:
        """Update review"""
        pass
