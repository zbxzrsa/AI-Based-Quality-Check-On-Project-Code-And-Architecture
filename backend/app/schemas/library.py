"""
Pydantic schemas for library management
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.library import ProjectContext, RegistryType

# ============================================================================
# Core Data Models
# ============================================================================


class ParsedURI(BaseModel):
    """Parsed library URI information"""

    registry_type: RegistryType
    package_name: str
    version: str | None = None
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
    dependencies: list[Dependency] = Field(default_factory=list)
    homepage: str | None = None
    repository: str | None = None


class InstalledLibrary(BaseModel):
    """Installed library information"""

    id: int | None = None
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
    metadata: dict[str, Any] | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Validation and Analysis Results
# ============================================================================


class ValidationResult(BaseModel):
    """Result of library URI validation"""

    valid: bool
    library: LibraryMetadata | None = None
    suggested_context: ProjectContext | None = None
    errors: list[str] = Field(default_factory=list)


class ConflictInfo(BaseModel):
    """Information about a dependency conflict"""

    package: str
    existing_version: str
    required_version: str


class ConflictAnalysis(BaseModel):
    """Analysis of dependency conflicts"""

    has_conflicts: bool
    conflicts: list[ConflictInfo] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    circular_dependencies: list[str] | None = None


class InstallationResult(BaseModel):
    """Result of library installation"""

    success: bool
    installed_library: InstalledLibrary | None = None
    errors: list[str] = Field(default_factory=list)


# ============================================================================
# Request Schemas
# ============================================================================


class ValidateLibraryRequest(BaseModel):
    """Request to validate a library URI"""

    uri: str = Field(..., min_length=1, description="Library URI to validate")
    project_context: ProjectContext | None = Field(
        None, description="Target project context (backend, frontend, services)"
    )

    @field_validator("uri")
    @classmethod
    def validate_uri_not_empty(cls, v: str) -> str:
        """Ensure URI is not just whitespace"""
        if not v or not v.strip():
            raise ValueError("URI cannot be empty or whitespace")
        return v.strip()


class InstallLibraryRequest(BaseModel):
    """Request to install a library"""

    uri: str = Field(..., min_length=1, description="Library URI to install")
    project_context: ProjectContext = Field(..., description="Target project context (backend, frontend, services)")
    version: str | None = Field(None, description="Specific version to install (overrides URI version)")

    @field_validator("uri")
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
    library: LibraryMetadata | None = None
    suggested_context: ProjectContext | None = None
    errors: list[str] | None = None


class InstallationResponse(BaseModel):
    """Response from library installation endpoint"""

    success: bool
    installed_library: InstalledLibrary | None = None
    errors: list[str] | None = None


class LibrarySearchResult(BaseModel):
    """Single library search result"""

    name: str
    description: str
    version: str
    downloads: int | None = None
    uri: str
    registry_type: RegistryType


class SearchResponse(BaseModel):
    """Response from library search endpoint"""

    results: list[LibrarySearchResult] = Field(default_factory=list)
    total: int | None = None


class LibraryListResponse(BaseModel):
    """Response from list installed libraries endpoint"""

    libraries: list[InstalledLibrary] = Field(default_factory=list)
    total: int = 0
