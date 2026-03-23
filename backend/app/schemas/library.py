"""
Pydantic schemas for library management
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from app.models.library import RegistryType, ProjectContext


# ============================================================================
# Core Data Models
# ============================================================================

class ParsedURI(BaseModel):
    """Parsed library URI information"""
    registry_type: RegistryType
    package_name: str
    version: Optional[str] = None
    raw_uri: str


class Dependency(BaseModel):
    """Library dependency information"""
    name: str
    version: str
    is_direct: bool = True


class LibraryMetadata(BaseModel):
    """Library metadata from package registry"""
    name: str
    version: str
    description: str
    license: str
    registry_type: RegistryType
    dependencies: List[Dependency] = Field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None


class InstalledLibrary(BaseModel):
    """Installed library information"""
    id: Optional[int] = None
    project_id: str
    name: str
    version: str
    registry_type: RegistryType
    project_context: ProjectContext
    description: str
    license: str
    installed_at: datetime
    installed_by: str
    uri: str
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ============================================================================
# Validation and Analysis Results
# ============================================================================

class ValidationResult(BaseModel):
    """Result of library URI validation"""
    valid: bool
    library: Optional[LibraryMetadata] = None
    suggested_context: Optional[ProjectContext] = None
    errors: List[str] = Field(default_factory=list)


class ConflictInfo(BaseModel):
    """Information about a dependency conflict"""
    package: str
    existing_version: str
    required_version: str


class ConflictAnalysis(BaseModel):
    """Analysis of dependency conflicts"""
    has_conflicts: bool
    conflicts: List[ConflictInfo] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    circular_dependencies: Optional[List[str]] = None


class InstallationResult(BaseModel):
    """Result of library installation"""
    success: bool
    installed_library: Optional[InstalledLibrary] = None
    errors: List[str] = Field(default_factory=list)


# ============================================================================
# Request Schemas
# ============================================================================

class ValidateLibraryRequest(BaseModel):
    """Request to validate a library URI"""
    uri: str = Field(..., min_length=1, description="Library URI to validate")
    project_context: Optional[ProjectContext] = Field(
        None,
        description="Target project context (backend, frontend, services)"
    )

    @field_validator('uri')
    @classmethod
    def validate_uri_not_empty(cls, v: str) -> str:
        """Ensure URI is not just whitespace"""
        if not v or not v.strip():
            raise ValueError("URI cannot be empty or whitespace")
        return v.strip()


class InstallLibraryRequest(BaseModel):
    """Request to install a library"""
    uri: str = Field(..., min_length=1, description="Library URI to install")
    project_context: ProjectContext = Field(
        ...,
        description="Target project context (backend, frontend, services)"
    )
    version: Optional[str] = Field(
        None,
        description="Specific version to install (overrides URI version)"
    )

    @field_validator('uri')
    @classmethod
    def validate_uri_not_empty(cls, v: str) -> str:
        """Ensure URI is not just whitespace"""
        if not v or not v.strip():
            raise ValueError("URI cannot be empty or whitespace")
        return v.strip()


# ============================================================================
# Response Schemas
# ============================================================================

class ValidationResponse(BaseModel):
    """Response from library validation endpoint"""
    valid: bool
    library: Optional[LibraryMetadata] = None
    suggested_context: Optional[ProjectContext] = None
    errors: Optional[List[str]] = None


class InstallationResponse(BaseModel):
    """Response from library installation endpoint"""
    success: bool
    installed_library: Optional[InstalledLibrary] = None
    errors: Optional[List[str]] = None


class LibrarySearchResult(BaseModel):
    """Single library search result"""
    name: str
    description: str
    version: str
    downloads: Optional[int] = None
    uri: str
    registry_type: RegistryType


class SearchResponse(BaseModel):
    """Response from library search endpoint"""
    results: List[LibrarySearchResult] = Field(default_factory=list)
    total: Optional[int] = None


class LibraryListResponse(BaseModel):
    """Response from list installed libraries endpoint"""
    libraries: List[InstalledLibrary] = Field(default_factory=list)
    total: int = 0
