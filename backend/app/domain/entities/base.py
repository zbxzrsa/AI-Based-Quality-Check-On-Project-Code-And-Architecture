"""
Domain Layer - Base Entity

Base class for all domain entities.
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional


@dataclass
class Entity:
    """
    Base class for all domain entities.
    
    Provides common fields and methods for entity identity and tracking.
    """
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class User(Entity):
    """User entity"""
    email: str = ""
    username: str = ""
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    hashed_password: Optional[str] = None


@dataclass
class Project(Entity):
    """Project entity"""
    name: str = ""
    description: Optional[str] = None
    owner_id: UUID = field(default_factory=uuid4)
    repository_url: Optional[str] = None
    is_active: bool = True


@dataclass
class PullRequest(Entity):
    """Pull Request entity"""
    project_id: UUID = field(default_factory=uuid4)
    pr_number: int = 0
    title: str = ""
    description: Optional[str] = None
    status: str = "open"
    author: str = ""
    branch: str = ""


@dataclass
class CodeReview(Entity):
    """Code Review entity"""
    pull_request_id: UUID = field(default_factory=uuid4)
    reviewer_id: UUID = field(default_factory=uuid4)
    status: str = "pending"
    comments: str = ""
    verdict: Optional[str] = None
