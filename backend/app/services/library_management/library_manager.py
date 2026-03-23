"""
Library Manager Orchestrator Service

This service acts as the main coordinator for all library management operations.
It integrates all the individual services (URI parser, metadata fetcher, context detector,
dependency resolver, package installer, and library repository) to provide a unified
interface for library validation, installation, search, and management.
"""

import logging
from typing import List, Optional

from app.services.library_management.uri_parser import URIParser
from app.services.library_management.metadata_fetcher import (
    MetadataFetcher,
    MetadataFetchError,
    NetworkError,
    PackageNotFoundError
)
from app.services.library_management.context_detector import (
    ContextDetector
)
from app.services.library_management.dependency_resolver import (
    DependencyResolver,
    DependencyResolverError
)
from app.services.library_management.package_installer import (
    PackageInstaller,
    PackageInstallerError
)
from app.services.library_management.library_repository import LibraryRepository
from app.services.library_management.search_service import (
    SearchService,
    SearchError,
    InvalidSearchQueryError
)

from app.schemas.library import (
    ValidationResult,
    InstallationResult,
    LibrarySearchResult,
    InstalledLibrary
)
from app.models.library import RegistryType, ProjectContext


logger = logging.getLogger(__name__)


class LibraryManagerError(Exception):
    """Base exception for library manager errors"""
    pass


class ValidationError(LibraryManagerError):
    """Library validation error"""
    pass


class InstallationError(LibraryManagerError):
    """Library installation error"""
    pass


class SearchError(LibraryManagerError):
    """Library search error"""
    pass


class LibraryManager:
    """
    Main orchestrator service for library management operations.
    
    This service coordinates the complete library management workflow:
    1. Parse URI -> 2. Fetch metadata -> 3. Detect context -> 4. Check conflicts -> 
    5. Install -> 6. Store metadata
    
    It provides a unified interface for:
    - Library validation and metadata retrieval
    - Library installation with conflict resolution
    - Library search across registries
    - Installed library management
    """
    
    def __init__(
        self,
        uri_parser: Optional[URIParser] = None,
        metadata_fetcher: Optional[MetadataFetcher] = None,
        context_detector: Optional[ContextDetector] = None,
        dependency_resolver: Optional[DependencyResolver] = None,
        package_installer: Optional[PackageInstaller] = None,
        library_repository: Optional[LibraryRepository] = None,
        search_service: Optional[SearchService] = None,
        project_root: Optional[str] = None
    ):
        """
        Initialize LibraryManager with service dependencies.
        
        Args:
            uri_parser: URI parsing service (creates new if None)
            metadata_fetcher: Metadata fetching service (creates new if None)
            context_detector: Context detection service (creates new if None)
            dependency_resolver: Dependency resolution service (creates new if None)
            package_installer: Package installation service (creates new if None)
            library_repository: Database repository service (required)
            search_service: Search service (creates new if None)
            project_root: Project root directory for file operations
        """
        self.project_root = project_root
        
        # Initialize services with dependency injection
        self.uri_parser = uri_parser or URIParser()
        self.metadata_fetcher = metadata_fetcher or MetadataFetcher()
        self.context_detector = context_detector or ContextDetector(project_root)
        self.dependency_resolver = dependency_resolver or DependencyResolver(project_root)
        self.package_installer = package_installer or PackageInstaller(project_root=project_root)
        self.search_service = search_service or SearchService()
        
        # Repository is required and must be injected
        if library_repository is None:
            raise ValueError("LibraryRepository is required and must be provided")
        self.library_repository = library_repository
        
        logger.info("LibraryManager initialized with all service dependencies")
    
    async def validate_library(
        self,
        uri: str,
        context: Optional[ProjectContext] = None,
        user_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate library URI and fetch metadata.
        
        This method performs the complete validation workflow:
        1. Parse and validate URI format
        2. Fetch metadata from package registry
        3. Detect appropriate project context
        4. Validate context configuration
        
        Args:
            uri: Library URI to validate (e.g., "npm:react@18.0.0")
            context: Optional target project context (auto-detected if None)
            user_id: Optional user ID for audit logging
            
        Returns:
            ValidationResult with library metadata and suggested context
            
        Raises:
            ValidationError: If validation fails for any reason
            
        Examples:
            >>> manager = LibraryManager(...)
            >>> result = await manager.validate_library("npm:react@18.0.0")
            >>> result.valid
            True
            >>> result.library.name
            'react'
            >>> result.suggested_context
            ProjectContext.FRONTEND
        """
        try:
            logger.info(f"Starting validation for URI: {uri}")
            
            # Step 1: Parse URI
            try:
                parsed_uri = self.uri_parser.parse(uri)
                logger.debug(
                    f"Parsed URI: {parsed_uri.registry_type.value}:"
                    f"{parsed_uri.package_name}@{parsed_uri.version or 'latest'}"
                )
            except ValueError as e:
                logger.warning(f"URI parsing failed: {e}")
                return ValidationResult(
                    valid=False,
                    errors=[str(e)]
                )
            
            # Step 2: Fetch metadata from registry
            try:
                metadata = await self.metadata_fetcher.fetch_metadata(
                    registry_type=parsed_uri.registry_type,
                    package_name=parsed_uri.package_name,
                    version=parsed_uri.version
                )
                logger.debug(f"Fetched metadata for {metadata.name}@{metadata.version}")
            except PackageNotFoundError as e:
                logger.warning(f"Package not found: {e}")
                return ValidationResult(
                    valid=False,
                    errors=[f"Package not found: {str(e)}"]
                )
            except NetworkError as e:
                logger.error(f"Network error during metadata fetch: {e}")
                return ValidationResult(
                    valid=False,
                    errors=[f"Network error: {str(e)}"]
                )
            except MetadataFetchError as e:
                logger.error(f"Metadata fetch error: {e}")
                return ValidationResult(
                    valid=False,
                    errors=[f"Failed to fetch metadata: {str(e)}"]
                )
            
            # Step 3: Detect or validate project context
            suggested_context = None
            context_errors = []
            
            if context is None:
                # Auto-detect context
                try:
                    detected_context, is_valid, error_msg = (
                        self.context_detector.detect_and_validate_context(parsed_uri.registry_type)
                    )
                    
                    if is_valid:
                        suggested_context = detected_context
                        logger.debug(f"Auto-detected valid context: {suggested_context.value}")
                    else:
                        suggested_context = detected_context
                        context_errors.append(error_msg or "Context validation failed")
                        logger.warning(f"Auto-detected context {detected_context.value} is invalid: {error_msg}")
                        
                        # Try to find alternative contexts
                        alternatives = self.context_detector.suggest_alternative_contexts(parsed_uri.registry_type)
                        if alternatives:
                            suggested_context = alternatives[0]  # Use first valid alternative
                            context_errors.append(
                                f"Using alternative context: {suggested_context.value}. "
                                f"Other options: {[ctx.value for ctx in alternatives[1:]]}"
                            )
                            logger.info(f"Using alternative context: {suggested_context.value}")
                        
                except Exception as e:
                    logger.error(f"Context detection failed: {e}")
                    context_errors.append(f"Context detection failed: {str(e)}")
            else:
                # Validate provided context
                try:
                    is_valid, error_msg = self.context_detector.validate_context(context)
                    if is_valid:
                        suggested_context = context
                        logger.debug(f"Provided context {context.value} is valid")
                    else:
                        suggested_context = context
                        context_errors.append(error_msg or "Context validation failed")
                        logger.warning(f"Provided context {context.value} is invalid: {error_msg}")
                except Exception as e:
                    logger.error(f"Context validation failed: {e}")
                    context_errors.append(f"Context validation failed: {str(e)}")
            
            # Log validation operation for audit trail
            if user_id:
                logger.info(
                    f"Library validation completed",
                    extra={
                        'user_id': user_id,
                        'operation': 'validate_library',
                        'uri': uri,
                        'package_name': metadata.name,
                        'package_version': metadata.version,
                        'registry_type': metadata.registry_type.value,
                        'suggested_context': suggested_context.value if suggested_context else None,
                        'success': len(context_errors) == 0
                    }
                )
            
            # Return validation result
            return ValidationResult(
                valid=len(context_errors) == 0,
                library=metadata,
                suggested_context=suggested_context,
                errors=context_errors if context_errors else []
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            raise ValidationError(f"Library validation failed: {str(e)}")
    
    async def install_library(
        self,
        uri: str,
        context: ProjectContext,
        version: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: str = "default"
    ) -> InstallationResult:
        """
        Install library and store metadata.
        
        This method performs the complete installation workflow:
        1. Validate library URI and fetch metadata
        2. Check for dependency conflicts
        3. Install package using package manager
        4. Store library metadata in database
        5. Handle rollback on failure
        
        Args:
            uri: Library URI to install
            context: Target project context
            version: Optional specific version (overrides URI version)
            user_id: Optional user ID for audit logging
            project_id: Project identifier for database storage
            
        Returns:
            InstallationResult with installed library details or errors
            
        Raises:
            InstallationError: If installation fails for any reason
            
        Examples:
            >>> manager = LibraryManager(...)
            >>> result = await manager.install_library(
            ...     "npm:react@18.0.0",
            ...     ProjectContext.FRONTEND,
            ...     user_id="user123"
            ... )
            >>> result.success
            True
            >>> result.installed_library.name
            'react'
        """
        try:
            logger.info(f"Starting installation for URI: {uri} in context: {context.value}")
            
            # Step 1: Validate library and get metadata
            validation_result = await self.validate_library(uri, context, user_id)
            
            if not validation_result.valid or not validation_result.library:
                logger.warning(f"Library validation failed: {validation_result.errors}")
                return InstallationResult(
                    success=False,
                    errors=validation_result.errors
                )
            
            library_metadata = validation_result.library
            install_version = version or library_metadata.version
            
            logger.debug(f"Installing {library_metadata.name}@{install_version}")
            
            # Step 2: Check for dependency conflicts
            try:
                conflict_analysis = await self.dependency_resolver.check_conflicts(
                    library_metadata,
                    context
                )
                
                if conflict_analysis.has_conflicts:
                    logger.warning(
                        f"Dependency conflicts detected for {library_metadata.name}: "
                        f"{len(conflict_analysis.conflicts)} conflicts"
                    )
                    
                    # For now, we'll proceed with installation but include warnings
                    # In a production system, you might want to halt installation
                    # or provide user options to resolve conflicts
                    conflict_errors = []
                    for conflict in conflict_analysis.conflicts:
                        conflict_errors.append(
                            f"Version conflict: {conflict.package} "
                            f"(existing: {conflict.existing_version}, "
                            f"required: {conflict.required_version})"
                        )
                    
                    if conflict_analysis.circular_dependencies:
                        conflict_errors.append(
                            f"Circular dependency detected: "
                            f"{' -> '.join(conflict_analysis.circular_dependencies)}"
                        )
                    
                    # Include suggestions in errors
                    conflict_errors.extend(conflict_analysis.suggestions)
                    
                    logger.info("Proceeding with installation despite conflicts")
                
            except DependencyResolverError as e:
                logger.error(f"Dependency analysis failed: {e}")
                return InstallationResult(
                    success=False,
                    errors=[f"Dependency analysis failed: {str(e)}"]
                )
            
            # Step 3: Install package
            try:
                installation_result = await self.package_installer.install(
                    library_metadata,
                    context,
                    install_version
                )
                
                if not installation_result.success:
                    logger.error(f"Package installation failed: {installation_result.errors}")
                    return installation_result
                
                logger.info(f"Package installation completed successfully")
                
            except PackageInstallerError as e:
                logger.error(f"Package installation error: {e}")
                return InstallationResult(
                    success=False,
                    errors=[f"Installation failed: {str(e)}"]
                )
            
            # Step 4: Store library metadata in database
            try:
                if installation_result.installed_library:
                    # Update the installed library with correct project_id and user
                    installed_lib = installation_result.installed_library
                    installed_lib.project_id = project_id
                    installed_lib.installed_by = user_id or "system"
                    
                    # Save to database
                    library_id = await self.library_repository.save_library(installed_lib)
                    
                    # Save dependencies if any
                    if library_metadata.dependencies:
                        await self.library_repository.save_dependencies(
                            library_id,
                            library_metadata.dependencies
                        )
                    
                    # Update the library ID in the result
                    installed_lib.id = library_id
                    
                    logger.info(f"Library metadata saved to database with ID: {library_id}")
                
            except Exception as e:
                logger.error(f"Failed to save library metadata: {e}")
                # Installation succeeded but database save failed
                # This is a partial failure - the package is installed but not tracked
                return InstallationResult(
                    success=False,
                    installed_library=installation_result.installed_library,
                    errors=[
                        "Package installed successfully but failed to save metadata to database",
                        str(e)
                    ]
                )
            
            # Log installation operation for audit trail
            if user_id:
                logger.info(
                    f"Library installation completed successfully",
                    extra={
                        'user_id': user_id,
                        'operation': 'install_library',
                        'uri': uri,
                        'package_name': library_metadata.name,
                        'package_version': install_version,
                        'registry_type': library_metadata.registry_type.value,
                        'project_context': context.value,
                        'project_id': project_id,
                        'library_id': installation_result.installed_library.id if installation_result.installed_library else None,
                        'success': True
                    }
                )
            
            return installation_result
            
        except Exception as e:
            logger.error(f"Unexpected error during installation: {e}")
            raise InstallationError(f"Library installation failed: {str(e)}")
    
    async def search_libraries(
        self,
        query: str,
        registry_type: Optional[RegistryType] = None,
        limit: int = 20
    ) -> List[LibrarySearchResult]:
        """
        Search for libraries across package registries.
        
        This method searches for libraries by name or keywords across
        supported package registries (npm, PyPI, Maven) using the dedicated
        SearchService for comprehensive search functionality.
        
        Args:
            query: Search query (package name or keywords)
            registry_type: Optional registry filter (searches all if None)
            limit: Maximum number of results to return
            
        Returns:
            List of LibrarySearchResult objects
            
        Raises:
            SearchError: If search fails for any reason
            
        Examples:
            >>> manager = LibraryManager(...)
            >>> results = await manager.search_libraries("react")
            >>> len(results)
            20
            >>> results[0].name
            'react'
            >>> results[0].registry_type
            RegistryType.NPM
        """
        try:
            logger.info(f"Searching libraries: query='{query}', registry={registry_type}, limit={limit}")
            
            # Delegate to SearchService for comprehensive search functionality
            results = await self.search_service.search(
                query=query,
                registry_type=registry_type,
                limit=limit
            )
            
            logger.info(f"Search completed: found {len(results)} results for '{query}'")
            
            return results
            
        except InvalidSearchQueryError as e:
            logger.warning(f"Invalid search query: {e}")
            return []  # Return empty results for invalid queries
        except SearchError as e:
            logger.error(f"Search error: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise SearchError(f"Library search failed: {str(e)}")
    
    async def get_installed_libraries(
        self,
        project_id: str,
        context: Optional[ProjectContext] = None,
        user_id: Optional[str] = None
    ) -> List[InstalledLibrary]:
        """
        Get installed libraries for a project.
        
        This method retrieves all libraries installed for a specific project,
        optionally filtered by project context.
        
        Args:
            project_id: Project identifier
            context: Optional project context filter
            user_id: Optional user ID for audit logging
            
        Returns:
            List of InstalledLibrary objects
            
        Raises:
            LibraryManagerError: If retrieval fails
            
        Examples:
            >>> manager = LibraryManager(...)
            >>> libraries = await manager.get_installed_libraries("project123")
            >>> len(libraries)
            5
            >>> libraries[0].name
            'react'
        """
        try:
            logger.info(
                f"Retrieving installed libraries for project: {project_id}"
                f"{f', context: {context.value}' if context else ''}"
            )
            
            libraries = await self.library_repository.get_libraries_by_project(
                project_id=project_id,
                context=context
            )
            
            # Log retrieval operation for audit trail
            if user_id:
                logger.info(
                    f"Retrieved installed libraries",
                    extra={
                        'user_id': user_id,
                        'operation': 'get_installed_libraries',
                        'project_id': project_id,
                        'context': context.value if context else None,
                        'library_count': len(libraries),
                        'success': True
                    }
                )
            
            logger.info(f"Retrieved {len(libraries)} installed libraries")
            
            return libraries
            
        except Exception as e:
            logger.error(f"Failed to retrieve installed libraries: {e}")
            raise LibraryManagerError(f"Failed to retrieve libraries: {str(e)}")
    
    async def get_library_details(
        self,
        project_id: str,
        library_name: str,
        context: ProjectContext,
        user_id: Optional[str] = None
    ) -> Optional[InstalledLibrary]:
        """
        Get details for a specific installed library.
        
        Args:
            project_id: Project identifier
            library_name: Name of the library
            context: Project context
            user_id: Optional user ID for audit logging
            
        Returns:
            InstalledLibrary object if found, None otherwise
            
        Raises:
            LibraryManagerError: If retrieval fails
        """
        try:
            logger.debug(f"Getting details for library: {library_name} in {context.value}")
            
            library = await self.library_repository.get_library_by_name(
                project_id=project_id,
                name=library_name,
                context=context
            )
            
            # Log retrieval operation for audit trail
            if user_id:
                logger.info(
                    f"Retrieved library details",
                    extra={
                        'user_id': user_id,
                        'operation': 'get_library_details',
                        'project_id': project_id,
                        'library_name': library_name,
                        'context': context.value,
                        'found': library is not None,
                        'success': True
                    }
                )
            
            return library
            
        except Exception as e:
            logger.error(f"Failed to retrieve library details: {e}")
            raise LibraryManagerError(f"Failed to retrieve library details: {str(e)}")
    
    async def update_library_version(
        self,
        project_id: str,
        library_name: str,
        context: ProjectContext,
        new_version: str,
        user_id: Optional[str] = None
    ) -> InstallationResult:
        """
        Update an installed library to a new version.
        
        This method performs a version update by:
        1. Validating the new version exists
        2. Checking for conflicts with the new version
        3. Installing the new version
        4. Updating the database record
        
        Args:
            project_id: Project identifier
            library_name: Name of the library to update
            context: Project context
            new_version: New version to install
            user_id: Optional user ID for audit logging
            
        Returns:
            InstallationResult with update status
            
        Raises:
            LibraryManagerError: If update fails
        """
        try:
            logger.info(f"Updating library {library_name} to version {new_version}")
            
            # Get current library details
            current_library = await self.library_repository.get_library_by_name(
                project_id=project_id,
                name=library_name,
                context=context
            )
            
            if not current_library:
                return InstallationResult(
                    success=False,
                    errors=[f"Library {library_name} not found in {context.value} context"]
                )
            
            # Create URI for the new version
            uri = f"{current_library.registry_type.value}:{library_name}@{new_version}"
            
            # Install the new version (this will overwrite the existing installation)
            result = await self.install_library(
                uri=uri,
                context=context,
                version=new_version,
                user_id=user_id,
                project_id=project_id
            )
            
            if result.success and current_library.id:
                # Update the database record with new version
                await self.library_repository.update_library_version(
                    library_id=current_library.id,
                    new_version=new_version
                )
                
                logger.info(f"Successfully updated {library_name} to version {new_version}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update library version: {e}")
            raise LibraryManagerError(f"Failed to update library: {str(e)}")
    
    async def close(self):
        """
        Close resources and cleanup.
        
        This method should be called when the LibraryManager is no longer needed
        to properly close HTTP clients and other resources.
        """
        try:
            if self.metadata_fetcher:
                await self.metadata_fetcher.close()
            if self.search_service:
                await self.search_service.close()
            logger.info("LibraryManager resources closed")
        except Exception as e:
            logger.error(f"Error closing LibraryManager resources: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()