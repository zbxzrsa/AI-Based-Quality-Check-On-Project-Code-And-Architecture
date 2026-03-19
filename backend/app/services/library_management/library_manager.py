"""
Library Manager Orchestrator Service

This module keeps the public LibraryManager API stable while internally
separating workflow steps into focused methods.
"""

import logging
from typing import Protocol

from app.models.library import ProjectContext, RegistryType
from app.schemas.library import InstallationResult, InstalledLibrary, LibrarySearchResult, ValidationResult
from app.services.library_management.context_detector import ContextDetector
from app.services.library_management.dependency_resolver import DependencyResolver, DependencyResolverError
from app.services.library_management.metadata_fetcher import (
    MetadataFetcher,
    MetadataFetchError,
    NetworkError,
    PackageNotFoundError,
)
from app.services.library_management.package_installer import PackageInstaller, PackageInstallerError
from app.services.library_management.search_service import (
    InvalidSearchQueryError,
    SearchError as SearchServiceError,
    SearchService,
)
from app.services.library_management.uri_parser import URIParser

logger = logging.getLogger(__name__)


class LibraryRepositoryPort(Protocol):
    """Repository contract used by the application workflow."""

    async def save_library(self, library: InstalledLibrary) -> int: ...

    async def save_dependencies(self, library_id: int, dependencies: list) -> None: ...

    async def get_libraries_by_project(self, project_id: str, context: ProjectContext | None = None) -> list[InstalledLibrary]: ...

    async def get_library_by_name(
        self, project_id: str, name: str, context: ProjectContext
    ) -> InstalledLibrary | None: ...

    async def update_library_version(self, library_id: int, new_version: str) -> None: ...


class LibraryManagerError(Exception):
    """Base exception for library manager errors."""


class ValidationError(LibraryManagerError):
    """Library validation error."""


class InstallationError(LibraryManagerError):
    """Library installation error."""


class SearchError(LibraryManagerError):
    """Library search error."""


class LibraryManager:
    """Facade for library-management workflows."""

    def __init__(
        self,
        uri_parser: URIParser | None = None,
        metadata_fetcher: MetadataFetcher | None = None,
        context_detector: ContextDetector | None = None,
        dependency_resolver: DependencyResolver | None = None,
        package_installer: PackageInstaller | None = None,
        library_repository: LibraryRepositoryPort | None = None,
        search_service: SearchService | None = None,
        project_root: str | None = None,
    ):
        self.project_root = project_root
        self.uri_parser = uri_parser or URIParser()
        self.metadata_fetcher = metadata_fetcher or MetadataFetcher()
        self.context_detector = context_detector or ContextDetector(project_root)
        self.dependency_resolver = dependency_resolver or DependencyResolver(project_root)
        self.package_installer = package_installer or PackageInstaller(project_root=project_root)
        self.search_service = search_service or SearchService()

        if library_repository is None:
            raise ValueError("LibraryRepository is required and must be provided")
        self.library_repository = library_repository

        logger.info("LibraryManager initialized with decoupled dependencies")

    async def _resolve_validation_context(
        self,
        parsed_registry: RegistryType,
        requested_context: ProjectContext | None,
    ) -> tuple[ProjectContext | None, list[str]]:
        """Resolve and validate target context for a package operation."""
        suggested_context = None
        context_errors: list[str] = []

        if requested_context is None:
            detected_context, is_valid, error_msg = self.context_detector.detect_and_validate_context(parsed_registry)
            if is_valid:
                return detected_context, []

            suggested_context = detected_context
            context_errors.append(error_msg or "Context validation failed")

            alternatives = self.context_detector.suggest_alternative_contexts(parsed_registry)
            if alternatives:
                suggested_context = alternatives[0]
                context_errors.append(
                    f"Using alternative context: {suggested_context.value}. "
                    f"Other options: {[ctx.value for ctx in alternatives[1:]]}"
                )
            return suggested_context, context_errors

        is_valid, error_msg = self.context_detector.validate_context(requested_context)
        if is_valid:
            return requested_context, []

        context_errors.append(error_msg or "Context validation failed")
        return requested_context, context_errors

    async def validate_library(
        self, uri: str, context: ProjectContext | None = None, user_id: str | None = None
    ) -> ValidationResult:
        try:
            logger.info(f"Starting validation for URI: {uri}")

            try:
                parsed_uri = self.uri_parser.parse(uri)
            except ValueError as e:
                logger.warning(f"URI parsing failed: {e}")
                return ValidationResult(valid=False, errors=[str(e)])

            try:
                metadata = await self.metadata_fetcher.fetch_metadata(
                    registry_type=parsed_uri.registry_type,
                    package_name=parsed_uri.package_name,
                    version=parsed_uri.version,
                )
            except PackageNotFoundError as e:
                logger.warning(f"Package not found: {e}")
                return ValidationResult(valid=False, errors=[f"Package not found: {str(e)}"])
            except NetworkError as e:
                logger.error(f"Network error during metadata fetch: {e}")
                return ValidationResult(valid=False, errors=[f"Network error: {str(e)}"])
            except MetadataFetchError as e:
                logger.error(f"Metadata fetch error: {e}")
                return ValidationResult(valid=False, errors=[f"Failed to fetch metadata: {str(e)}"])

            try:
                suggested_context, context_errors = await self._resolve_validation_context(
                    parsed_registry=parsed_uri.registry_type,
                    requested_context=context,
                )
            except Exception as e:
                logger.error(f"Context resolution failed: {e}")
                suggested_context, context_errors = context, [f"Context validation failed: {str(e)}"]

            if user_id:
                logger.info(
                    "Library validation completed",
                    extra={
                        "user_id": user_id,
                        "operation": "validate_library",
                        "uri": uri,
                        "package_name": metadata.name,
                        "package_version": metadata.version,
                        "registry_type": metadata.registry_type.value,
                        "suggested_context": suggested_context.value if suggested_context else None,
                        "success": len(context_errors) == 0,
                    },
                )

            return ValidationResult(
                valid=len(context_errors) == 0,
                library=metadata,
                suggested_context=suggested_context,
                errors=context_errors if context_errors else [],
            )
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            raise ValidationError(f"Library validation failed: {str(e)}")

    async def _persist_installation(
        self,
        installation_result: InstallationResult,
        project_id: str,
        user_id: str | None,
        dependencies: list,
    ) -> InstallationResult:
        """Persist successful installation metadata via repository abstraction."""
        if not installation_result.installed_library:
            return installation_result

        installed_lib = installation_result.installed_library
        installed_lib.project_id = project_id
        installed_lib.installed_by = user_id or "system"

        library_id = await self.library_repository.save_library(installed_lib)
        if dependencies:
            await self.library_repository.save_dependencies(library_id, dependencies)

        installed_lib.id = library_id
        return installation_result

    async def install_library(
        self,
        uri: str,
        context: ProjectContext,
        version: str | None = None,
        user_id: str | None = None,
        project_id: str = "default",
    ) -> InstallationResult:
        try:
            logger.info(f"Starting installation for URI: {uri} in context: {context.value}")

            validation_result = await self.validate_library(uri, context, user_id)
            if not validation_result.valid or not validation_result.library:
                return InstallationResult(success=False, errors=validation_result.errors)

            library_metadata = validation_result.library
            install_version = version or library_metadata.version

            try:
                await self.dependency_resolver.check_conflicts(library_metadata, context)
            except DependencyResolverError as e:
                logger.error(f"Dependency analysis failed: {e}")
                return InstallationResult(success=False, errors=[f"Dependency analysis failed: {str(e)}"])

            try:
                installation_result = await self.package_installer.install(library_metadata, context, install_version)
                if not installation_result.success:
                    return installation_result
            except PackageInstallerError as e:
                logger.error(f"Package installation error: {e}")
                return InstallationResult(success=False, errors=[f"Installation failed: {str(e)}"])

            try:
                installation_result = await self._persist_installation(
                    installation_result=installation_result,
                    project_id=project_id,
                    user_id=user_id,
                    dependencies=library_metadata.dependencies,
                )
            except Exception as e:
                logger.error(f"Failed to save library metadata: {e}")
                return InstallationResult(
                    success=False,
                    installed_library=installation_result.installed_library,
                    errors=["Package installed successfully but failed to save metadata to database", str(e)],
                )

            if user_id:
                logger.info(
                    "Library installation completed successfully",
                    extra={
                        "user_id": user_id,
                        "operation": "install_library",
                        "uri": uri,
                        "package_name": library_metadata.name,
                        "package_version": install_version,
                        "registry_type": library_metadata.registry_type.value,
                        "project_context": context.value,
                        "project_id": project_id,
                        "library_id": installation_result.installed_library.id
                        if installation_result.installed_library
                        else None,
                        "success": True,
                    },
                )

            return installation_result
        except Exception as e:
            logger.error(f"Unexpected error during installation: {e}")
            raise InstallationError(f"Library installation failed: {str(e)}")

    async def search_libraries(
        self, query: str, registry_type: RegistryType | None = None, limit: int = 20
    ) -> list[LibrarySearchResult]:
        try:
            results = await self.search_service.search(query=query, registry_type=registry_type, limit=limit)
            return results
        except InvalidSearchQueryError:
            return []
        except SearchServiceError as e:
            logger.error(f"Search error: {e}")
            raise SearchError(str(e)) from e
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise SearchError(f"Library search failed: {str(e)}") from e

    async def get_installed_libraries(
        self, project_id: str, context: ProjectContext | None = None, user_id: str | None = None
    ) -> list[InstalledLibrary]:
        try:
            libraries = await self.library_repository.get_libraries_by_project(project_id=project_id, context=context)
            if user_id:
                logger.info(
                    "Retrieved installed libraries",
                    extra={
                        "user_id": user_id,
                        "operation": "get_installed_libraries",
                        "project_id": project_id,
                        "context": context.value if context else None,
                        "library_count": len(libraries),
                        "success": True,
                    },
                )
            return libraries
        except Exception as e:
            logger.error(f"Failed to retrieve installed libraries: {e}")
            raise LibraryManagerError(f"Failed to retrieve libraries: {str(e)}")

    async def get_library_details(
        self, project_id: str, library_name: str, context: ProjectContext, user_id: str | None = None
    ) -> InstalledLibrary | None:
        try:
            library = await self.library_repository.get_library_by_name(
                project_id=project_id, name=library_name, context=context
            )
            if user_id:
                logger.info(
                    "Retrieved library details",
                    extra={
                        "user_id": user_id,
                        "operation": "get_library_details",
                        "project_id": project_id,
                        "library_name": library_name,
                        "context": context.value,
                        "found": library is not None,
                        "success": True,
                    },
                )
            return library
        except Exception as e:
            logger.error(f"Failed to retrieve library details: {e}")
            raise LibraryManagerError(f"Failed to retrieve library details: {str(e)}")

    async def update_library_version(
        self, project_id: str, library_name: str, context: ProjectContext, new_version: str, user_id: str | None = None
    ) -> InstallationResult:
        try:
            current_library = await self.library_repository.get_library_by_name(
                project_id=project_id, name=library_name, context=context
            )
            if not current_library:
                return InstallationResult(
                    success=False, errors=[f"Library {library_name} not found in {context.value} context"]
                )

            uri = f"{current_library.registry_type.value}:{library_name}@{new_version}"
            result = await self.install_library(
                uri=uri, context=context, version=new_version, user_id=user_id, project_id=project_id
            )

            if result.success and current_library.id:
                await self.library_repository.update_library_version(
                    library_id=current_library.id,
                    new_version=new_version,
                )
            return result
        except Exception as e:
            logger.error(f"Failed to update library version: {e}")
            raise LibraryManagerError(f"Failed to update library: {str(e)}")

    async def close(self):
        try:
            if self.metadata_fetcher:
                await self.metadata_fetcher.close()
            if self.search_service:
                await self.search_service.close()
            logger.info("LibraryManager resources closed")
        except Exception as e:
            logger.error(f"Error closing LibraryManager resources: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
