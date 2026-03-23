"""
Repository management schemas for GitHub dependency integration
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
# Import consolidated enums from common library
from common.shared.enums import RepositoryStatus, RepositoryURLFormat
import re


class AddRepositoryRequest(BaseModel):
    """Request schema for adding a new repository dependency"""
    repository_url: str = Field(
        ...,
        description="GitHub repository URL (HTTPS or SSH format)",
        examples=[
            "https://github.com/owner/repo.git",
            "git@github.com:owner/repo.git"
        ]
    )
    branch: Optional[str] = Field(
        default="main",
        description="Branch or tag to track",
        max_length=255
    )
    version: Optional[str] = Field(
        default=None,
        description="Specific version/tag to use",
        max_length=100
    )
    auto_update: bool = Field(
        default=False,
        description="Automatically update to latest version"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the dependency",
        max_length=500
    )

    @field_validator('repository_url')
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """Validate GitHub repository URL format"""
        # HTTPS format: https://github.com/{owner}/{repo}.git
        https_pattern = r'^https://github\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?$'
        
        # SSH format: git@github.com:{owner}/{repo}.git
        ssh_pattern = r'^git@github\.com:[\w\-\.]+/[\w\-\.]+(?:\.git)?$'
        
        if not (re.match(https_pattern, v) or re.match(ssh_pattern, v)):
            raise ValueError(
                "Invalid GitHub URL format. Expected formats:\n"
                "  - HTTPS: https://github.com/owner/repo.git\n"
                "  - SSH: git@github.com:owner/repo.git"
            )
        
        return v

    @field_validator('branch')
    @classmethod
    def validate_branch(cls, v: Optional[str]) -> Optional[str]:
        """Validate branch name"""
        if v and not re.match(r'^[\w\-\.\/]+$', v):
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
    version: Optional[str]
    status: RepositoryStatus
    description: Optional[str]
    auto_update: bool
    last_synced: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    metadata: dict = Field(default_factory=dict)


class RepositoryListResponse(BaseModel):
    """Response schema for listing repositories"""
    repositories: List[RepositoryResponse]
    total: int
    page: int
    page_size: int


class RepositoryValidationResult(BaseModel):
    """Result of repository validation"""
    is_valid: bool
    is_accessible: bool
    exists: bool
    default_branch: Optional[str]
    available_branches: List[str] = Field(default_factory=list)
    available_tags: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class DependencyInfo(BaseModel):
    """Dependency information extracted from repository"""
    package_manager: str = Field(..., description="Package manager type (npm, pip, maven, etc.)")
    dependencies: dict = Field(default_factory=dict, description="Direct dependencies")
    dev_dependencies: dict = Field(default_factory=dict, description="Development dependencies")
    peer_dependencies: dict = Field(default_factory=dict, description="Peer dependencies")


class RepositoryUpdateRequest(BaseModel):
    """Request schema for updating repository settings"""
    branch: Optional[str] = None
    version: Optional[str] = None
    auto_update: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[RepositoryStatus] = None
