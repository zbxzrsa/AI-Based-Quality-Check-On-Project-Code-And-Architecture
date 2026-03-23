"""
Library Management API endpoints

Provides endpoints for:
- Validating library URIs and fetching metadata
- Installing libraries into projects
- Searching for libraries across registries
- Listing installed libraries

Validates Requirements: All library management requirements (API layer)
"""
import logging
from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database.postgresql import get_db
from app.api.dependencies import get_current_user
from app.models import User
from app.schemas.library import (
    ValidateLibraryRequest,
    ValidationResponse,
    InstallLibraryRequest,
    InstallationResponse,
    SearchResponse,
    LibraryListResponse,
    ProjectContext
)
from app.models.library import RegistryType
from app.services.library_management.library_manager import (
    LibraryManager,
    ValidationError as LibraryValidationError
)
from app.services.library_management.library_repository import LibraryRepository

logger = logging.getLogger(__name__)


def _sanitize_log_input(value: str, max_length: int = 200) -> str:
    """Sanitize user input for safe logging to prevent log injection."""
    if not value:
        return ""
    # Remove newlines and control characters that could break log format
    sanitized = value.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    # Truncate to prevent log flooding
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "...[truncated]"
    return sanitized


router = APIRouter()


async def get_library_manager(db: AsyncSession = Depends(get_db)) -> LibraryManager:
    """
    Dependency to get LibraryManager instance with database repository.
    
    Args:
        db: Database session
        
    Returns:
        Configured LibraryManager instance
    """
    repository = LibraryRepository(db)
    return LibraryManager(library_repository=repository)


@router.post("/validate", response_model=ValidationResponse)
async def validate_library(
    request: ValidateLibraryRequest,
    current_user: User = Depends(get_current_user),
    library_manager: LibraryManager = Depends(get_library_manager)
):
    """
    Validate library URI and fetch metadata.
    
    - **uri**: Library URI to validate (npm:package@version, pypi:package==version, etc.)
    - **project_context**: Optional target project context (backend, frontend, services)
    
    Returns library metadata if valid, or validation errors if invalid.
    
    Validates Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.6
    """
    try:
        # Use a safe version for logging to avoid sensitive data exposure
        masked_uri = f"{request.uri[:4]}...{request.uri[-4:]}" if len(request.uri) > 10 else "***"
        logger.info(
            f"Validating library URI: {masked_uri}",
            extra={
                'user_id': str(current_user.id),
                'operation': 'validate_library_endpoint',
                'uri_length': len(request.uri),
                'project_context': request.project_context.value if request.project_context else None
            }
        )
        
        # Call LibraryManager to validate the library
        validation_result = await library_manager.validate_library(
            uri=request.uri,
            context=request.project_context,
            user_id=str(current_user.id)
        )
        
        # Convert ValidationResult to ValidationResponse
        response = ValidationResponse(
            valid=validation_result.valid,
            library=validation_result.library,
            suggested_context=validation_result.suggested_context,
            errors=validation_result.errors if validation_result.errors else None
        )
        
        # Return appropriate HTTP status code
        if validation_result.valid:
            logger.info(
                f"Library validation successful: {validation_result.library.name if validation_result.library else 'unknown'}",
                extra={
                    'user_id': str(current_user.id),
                    'operation': 'validate_library_endpoint',
                    'success': True,
                    'library_name': validation_result.library.name if validation_result.library else None,
                    'library_version': validation_result.library.version if validation_result.library else None
                }
            )
            return response
        else:
            logger.warning(
                f"Library validation failed: {validation_result.errors}",
                extra={
                    'user_id': str(current_user.id),
                    'operation': 'validate_library_endpoint',
                    'success': False,
                    'errors': validation_result.errors
                }
            )
            # Return 400 for validation errors (invalid URI, not found, etc.)
            # Return the response directly with 400 status
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=response.model_dump()
            )
            
    except LibraryValidationError as e:
        logger.error(
            f"Library validation error: {str(e)}",
            extra={
                'user_id': str(current_user.id),
                'operation': 'validate_library_endpoint',
                'error': str(e)
            }
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "valid": False,
                "errors": [str(e)]
            }
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during library validation: {str(e)}",
            extra={
                'user_id': str(current_user.id),
                'operation': 'validate_library_endpoint',
                'error': str(e)
            }
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "valid": False,
                "errors": ["Internal server error occurred during validation"]
            }
        )
    finally:
        # Clean up resources
        await library_manager.close()


@router.post("/install", response_model=InstallationResponse)
async def install_library(
    request: InstallLibraryRequest,
    current_user: User = Depends(get_current_user),
    library_manager: LibraryManager = Depends(get_library_manager)
):
    """
    Install a library into the specified project context.
    
    - **uri**: Library URI to install
    - **project_context**: Target project context (backend, frontend, services)
    - **version**: Optional specific version to install (overrides URI version)
    
    Returns installation result with library details or errors.
    
    Validates Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4
    """
    try:
        masked_uri = f"{request.uri[:4]}...{request.uri[-4:]}" if len(request.uri) > 10 else "***"
        logger.info(
            f"Installing library URI: {masked_uri} in context: {request.project_context.value}",
            extra={
                'user_id': str(current_user.id),
                'operation': 'install_library_endpoint',
                'uri_length': len(request.uri),
                'project_context': request.project_context.value,
                'version': request.version
            }
        )
        
        # Call LibraryManager to install the library
        installation_result = await library_manager.install_library(
            uri=request.uri,
            context=request.project_context,
            version=request.version,
            user_id=str(current_user.id),
            project_id=str(current_user.id)  # Using user_id as project_id for now
        )
        
        # Convert InstallationResult to InstallationResponse
        response = InstallationResponse(
            success=installation_result.success,
            installed_library=installation_result.installed_library,
            errors=installation_result.errors if installation_result.errors else None
        )
        
        # Return appropriate HTTP status code based on result
        if installation_result.success:
            logger.info(
                f"Library installation successful: {installation_result.installed_library.name if installation_result.installed_library else 'unknown'}",
                extra={
                    'user_id': str(current_user.id),
                    'operation': 'install_library_endpoint',
                    'success': True,
                    'library_name': installation_result.installed_library.name if installation_result.installed_library else None,
                    'library_version': installation_result.installed_library.version if installation_result.installed_library else None,
                    'library_id': installation_result.installed_library.id if installation_result.installed_library else None
                }
            )
            return response
        else:
            logger.warning(
                f"Library installation failed: {installation_result.errors}",
                extra={
                    'user_id': str(current_user.id),
                    'operation': 'install_library_endpoint',
                    'success': False,
                    'errors': installation_result.errors
                }
            )
            
            # Determine appropriate HTTP status code based on error type
            if installation_result.errors:
                error_text = ' '.join(installation_result.errors).lower()
                
                # Check for validation errors (400)
                if any(keyword in error_text for keyword in [
                    'invalid uri', 'not found', 'validation failed', 'invalid format',
                    'unsupported', 'malformed'
                ]):
                    status_code = status.HTTP_400_BAD_REQUEST
                
                # Check for conflict errors (409)
                elif any(keyword in error_text for keyword in [
                    'conflict', 'version conflict', 'circular dependency',
                    'already installed', 'incompatible'
                ]):
                    status_code = status.HTTP_409_CONFLICT
                
                # Default to 500 for installation failures
                else:
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
            return JSONResponse(
                status_code=status_code,
                content=response.model_dump()
            )
            
    except Exception as e:
        logger.error(
            f"Unexpected error during library installation: {str(e)}",
            extra={
                'user_id': str(current_user.id),
                'operation': 'install_library_endpoint',
                'error': str(e)
            }
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "errors": ["Internal server error occurred during installation"]
            }
        )
    finally:
        # Clean up resources
        await library_manager.close()


@router.get("/search", response_model=SearchResponse)
async def search_libraries(
    q: str = Query(..., min_length=1, description="Search query"),
    registry: Optional[str] = Query(None, description="Registry type filter (npm, pypi, maven)"),
    current_user: User = Depends(get_current_user),
    library_manager: LibraryManager = Depends(get_library_manager),
):
    """
    Search for libraries across package registries.
    
    - **q**: Search query (library name or keywords)
    - **registry**: Optional registry type filter (npm, pypi, maven)
    
    Returns list of matching libraries with metadata.
    
    Validates Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    try:
        logger.info(
            f"Searching libraries in registry: {_sanitize_log_input(registry or 'any')}",
            extra={
                'user_id': str(current_user.id),
                'operation': 'search_libraries_endpoint',
                'query_length': len(q),
                'registry_filter': _sanitize_log_input(registry or '')
            }
        )
        
        # Validate and convert registry parameter to RegistryType enum
        registry_type = None
        if registry:
            registry_lower = registry.lower()
            if registry_lower == "npm":
                registry_type = RegistryType.NPM
            elif registry_lower == "pypi":
                registry_type = RegistryType.PYPI
            elif registry_lower == "maven":
                registry_type = RegistryType.MAVEN
            else:
                logger.warning(
                    f"Invalid registry type: {registry}",
                    extra={
                        'user_id': str(current_user.id),
                        'operation': 'search_libraries_endpoint',
                        'invalid_registry': registry
                    }
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "results": [],
                        "total": 0,
                        "error": f"Invalid registry type: {registry}. Supported types: npm, pypi, maven"
                    }
                )
        
        # Call LibraryManager to search libraries (limit to 20 as per requirements)
        search_results = await library_manager.search_libraries(
            query=q,
            registry_type=registry_type,
            limit=20
        )
        
        # Convert to SearchResponse
        response = SearchResponse(
            results=search_results,
            total=len(search_results)
        )
        
        logger.info(
            f"Library search completed successfully: found {len(search_results)} results",
            extra={
                'user_id': str(current_user.id),
                'operation': 'search_libraries_endpoint',
                'registry_filter': registry,
                'results_count': len(search_results),
                'success': True
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(
            f"Unexpected error during library search: {str(e)}",
            extra={
                'user_id': str(current_user.id),
                'operation': 'search_libraries_endpoint',
                'query': q,
                'registry_filter': registry,
                'error': str(e)
            }
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "results": [],
                "total": 0,
                "error": "Internal server error occurred during search"
            }
        )
    finally:
        # Clean up resources
        await library_manager.close()


@router.get("/", response_model=LibraryListResponse)
async def list_installed_libraries(
    project_id: str = Query(..., description="Project ID to list libraries for"),
    project_context: Optional[ProjectContext] = Query(None, description="Filter by project context"),
    current_user: User = Depends(get_current_user),
    library_manager: LibraryManager = Depends(get_library_manager)
):
    """
    List installed libraries for a project.
    
    - **project_id**: Project ID to list libraries for
    - **project_context**: Optional filter by project context (backend, frontend, services)
    
    Returns list of installed libraries with metadata.
    
    Validates Requirements: 6.5
    """
    try:
        logger.info(
            "Listing installed libraries for project",
            extra={
                'user_id': str(current_user.id),
                'operation': 'list_installed_libraries_endpoint',
                'project_id_hash': hash(project_id) % 10000, # Non-reversible short ID for logs
                'project_context': project_context.value if project_context else None
            }
        )
        
        # Call LibraryManager to get installed libraries
        installed_libraries = await library_manager.get_installed_libraries(
            project_id=project_id,
            context=project_context,
            user_id=str(current_user.id)
        )
        
        # Convert to LibraryListResponse
        response = LibraryListResponse(
            libraries=installed_libraries,
            total=len(installed_libraries)
        )
        
        logger.info(
            f"Successfully retrieved {len(installed_libraries)} installed libraries",
            extra={
                'user_id': str(current_user.id),
                'operation': 'list_installed_libraries_endpoint',
                'project_id': project_id,
                'project_context': project_context.value if project_context else None,
                'library_count': len(installed_libraries),
                'success': True
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(
            f"Unexpected error during library listing: {str(e)}",
            extra={
                'user_id': str(current_user.id),
                'operation': 'list_installed_libraries_endpoint',
                'project_id': project_id,
                'project_context': project_context.value if project_context else None,
                'error': str(e)
            }
        )
        
        # Check if it's a project not found error
        error_text = str(e).lower()
        if any(keyword in error_text for keyword in ['not found', 'does not exist', 'invalid project']):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "libraries": [],
                    "total": 0,
                    "error": f"Project not found: {project_id}"
                }
            )
        
        # Default to 500 for other errors
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "libraries": [],
                "total": 0,
                "error": "Internal server error occurred while retrieving libraries"
            }
        )
    finally:
        # Clean up resources
        await library_manager.close()