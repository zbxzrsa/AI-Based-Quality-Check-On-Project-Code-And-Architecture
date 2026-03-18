"""
Domain Layer - Repository Interfaces

These interfaces define the contracts for data access.
Infrastructure layer implements these interfaces.
Domain and Application layers depend on these abstractions (DIP).
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from datetime import datetime
from uuid import UUID


class IUserRepository(ABC):
    """User repository interface - defines contract for user data access"""
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[Any]:
        """Get user by ID"""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[Any]:
        """Get user by email"""
        pass
    
    @abstractmethod
    async def create(self, user_data: Dict[str, Any]) -> Any:
        """Create new user"""
        pass
    
    @abstractmethod
    async def update(self, user_id: UUID, user_data: Dict[str, Any]) -> Optional[Any]:
        """Update user"""
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete user"""
        pass
    
    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Any]:
        """List all users"""
        pass


class IProjectRepository(ABC):
    """Project repository interface"""
    
    @abstractmethod
    async def get_by_id(self, project_id: UUID) -> Optional[Any]:
        """Get project by ID"""
        pass
    
    @abstractmethod
    async def get_by_owner(self, owner_id: UUID) -> List[Any]:
        """Get projects by owner"""
        pass
    
    @abstractmethod
    async def create(self, project_data: Dict[str, Any]) -> Any:
        """Create new project"""
        pass
    
    @abstractmethod
    async def update(self, project_id: UUID, project_data: Dict[str, Any]) -> Optional[Any]:
        """Update project"""
        pass
    
    @abstractmethod
    async def delete(self, project_id: UUID) -> bool:
        """Delete project"""
        pass


class IPullRequestRepository(ABC):
    """Pull Request repository interface"""
    
    @abstractmethod
    async def get_by_id(self, pr_id: UUID) -> Optional[Any]:
        """Get PR by ID"""
        pass
    
    @abstractmethod
    async def get_by_project(self, project_id: UUID) -> List[Any]:
        """Get PRs by project"""
        pass
    
    @abstractmethod
    async def create(self, pr_data: Dict[str, Any]) -> Any:
        """Create new PR"""
        pass
    
    @abstractmethod
    async def update(self, pr_id: UUID, pr_data: Dict[str, Any]) -> Optional[Any]:
        """Update PR"""
        pass


class ICodeReviewRepository(ABC):
    """Code Review repository interface"""
    
    @abstractmethod
    async def get_by_id(self, review_id: UUID) -> Optional[Any]:
        """Get review by ID"""
        pass
    
    @abstractmethod
    async def get_by_pull_request(self, pr_id: UUID) -> List[Any]:
        """Get reviews by PR"""
        pass
    
    @abstractmethod
    async def create(self, review_data: Dict[str, Any]) -> Any:
        """Create new review"""
        pass
    
    @abstractmethod
    async def update(self, review_id: UUID, review_data: Dict[str, Any]) -> Optional[Any]:
        """Update review"""
        pass
