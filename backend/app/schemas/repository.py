"""
Repository management schemas for GitHub dependency integration
"""

import re
from datetime import datetime

# Import consolidated enums from common library
from common.shared.enums import RepositoryStatus, RepositoryURLFormat
from pydantic import BaseModel, Field, field_validator


class AddRepositoryRequest(BaseModel):
    """Request schema for adding a new repository dependency"""

    repository_url: str = Field(
        ...,
        description="GitHub repository URL (HTTPS or SSH format)",
        examples=["https://github.com/owner/repo.git", "git@github.com:owner/repo.git"],
    )
    branch: str | None = Field(default="main", description="Branch or tag to track", max_length=255)
    version: str | None = Field(default=None, description="Specific version/tag to use", max_length=100)
    auto_update: bool = Field(default=False, description="Automatically update to latest version")
    description: str | None = Field(default=None, description="Optional description of the dependency", max_length=500)

    @field_validator("repository_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """Validate GitHub repository URL format"""
        # HTTPS format: https://github.com/{owner}/{repo}.git
        https_pattern = r"^https://github\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?$"

        # SSH format: git@github.com:{owner}/{repo}.git
        ssh_pattern = r"^git@github\.com:[\w\-\.]+/[\w\-\.]+(?:\.git)?$"

        if not (re.match(https_pattern, v) or re.match(ssh_pattern, v)):
            raise ValueError(
                "Invalid GitHub URL format. Expected formats:\n"
                "  - HTTPS: https://github.com/owner/repo.git\n"
                "  - SSH: git@github.com:owner/repo.git"
            )

        return v

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str | None) -> str | None:
        """Validate branch name"""
        if v and not re.match(r"^[\w\-\.\/]+$", v):
            raise ValueError("Invalid branch name format")
        return v


class RepositoryInfo(BaseModel):
    """Parsed repository information"""

    owner: str = Field(..., description="Repository owner/organization")
    name: str = Field(..., description="Repository name")
    url_format: RepositoryURLFormat = Field(..., description="URL format used")
    full_url: str = Field(..., description="Complete repository URL")
    clone_url: str = Field(..., description="URL for cloning")


class RepositoryResponse(BaseModel):
    """Response schema for repository operations"""

    id: str = Field(..., description="Unique repository identifier")
    repository_url: str
    owner: str
    name: str
    branch: str
    version: str | None
    status: RepositoryStatus
    description: str | None
    auto_update: bool
    last_synced: datetime | None
    created_at: datetime
    updated_at: datetime
    metadata: dict = Field(default_factory=dict)


class RepositoryListResponse(BaseModel):
    """Response schema for listing repositories"""

    repositories: list[RepositoryResponse]
    total: int
    page: int
    page_size: int


class RepositoryValidationResult(BaseModel):
    """Result of repository validation"""

    is_valid: bool
    is_accessible: bool
    exists: bool
    default_branch: str | None
    available_branches: list[str] = Field(default_factory=list)
    available_tags: list[str] = Field(default_factory=list)
    error_message: str | None = None


class DependencyInfo(BaseModel):
    """Dependency information extracted from repository"""

    package_manager: str = Field(..., description="Package manager type (npm, pip, maven, etc.)")
    dependencies: dict = Field(default_factory=dict, description="Direct dependencies")
    dev_dependencies: dict = Field(default_factory=dict, description="Development dependencies")
    peer_dependencies: dict = Field(default_factory=dict, description="Peer dependencies")


class RepositoryUpdateRequest(BaseModel):
    """Request schema for updating repository settings"""

    branch: str | None = None
    version: str | None = None
    auto_update: bool | None = None
    description: str | None = Field(None, max_length=500)
    status: RepositoryStatus | None = None
