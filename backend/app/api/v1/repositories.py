"""
Repository management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Annotated

from app.database.postgresql import get_db
from app.services.repository_service import RepositoryService
from app.schemas.repository import (
    AddRepositoryRequest,
    RepositoryResponse,
    RepositoryListResponse,
    RepositoryUpdateRequest,
    RepositoryValidationResult
)
from app.core.security import get_current_user
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post(
    "/",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new repository dependency"
)
async def add_repository(
    request: AddRepositoryRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """
    Add a new GitHub repository as a dependency.
    
    Supports both HTTPS and SSH URL formats:
    - HTTPS: https://github.com/owner/repo.git
    - SSH: git@github.com:owner/repo.git
    
    The system will:
    1. Validate the repository URL format
    2. Check repository accessibility
    3. Verify branch/tag existence
    4. Extract dependency information
    5. Store repository metadata
    """
    try:
        service = RepositoryService(db)
        repository = await service.add_repository(request, current_user["sub"])
        
        logger.info(
            f"Repository added successfully: {repository.owner}/{repository.name} "
            f"by user {current_user['sub']}"
        )
        
        return repository
        
    except ValueError as e:
        logger.warning(f"Repository validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add repository"
        )


@router.get(
    "/validate",
    response_model=RepositoryValidationResult,
    summary="Validate a repository URL"
)
async def validate_repository(
    repository_url: str = Query(..., description="GitHub repository URL to validate"),
    branch: Optional[str] = Query(None, description="Optional branch to validate"),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """
    Validate a GitHub repository URL without adding it.
    
    Returns:
    - Repository existence
    - Accessibility status
    - Available branches and tags
    - Default branch
    """
    try:
        service = RepositoryService(db)
        repo_info = service.parse_repository_url(repository_url)
        validation = await service.validate_repository(repo_info, branch)
        
        return validation
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error validating repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate repository"
        )


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
    summary="Get repository details"
)
async def get_repository(
    repository_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """Get detailed information about a specific repository"""
    try:
        from app.models.repository import Repository
        from sqlalchemy import select
        from uuid import UUID
        
        # Convert string to UUID
        try:
            repo_uuid = UUID(repository_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid repository ID format"
            )
        
        # Query repository
        result = await db.execute(
            select(Repository).where(Repository.id == repo_uuid)
        )
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found"
            )
        
        # Check ownership
        if repository.created_by != current_user["sub"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this repository"
            )
        
        logger.info(f"Retrieved repository {repository_id} for user {current_user['sub']}")
        return repository
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve repository"
        )


@router.get(
    "/",
    response_model=RepositoryListResponse,
    summary="List all repositories"
)
async def list_repositories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """List all repository dependencies with pagination"""
    try:
        from app.models.repository import Repository
        from sqlalchemy import select, func
        
        # Build base query for user's repositories
        query = select(Repository).where(Repository.created_by == current_user["sub"])
        
        # Apply status filter if provided
        if status:
            query = query.where(Repository.status == status)
        
        # Order by creation date (newest first)
        query = query.order_by(Repository.created_at.desc())
        
        # Count total matching repositories
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        repositories = result.scalars().all()
        
        logger.info(
            f"Listed {len(repositories)} repositories (page {page}/{(total + page_size - 1) // page_size}) "
            f"for user {current_user['sub']}"
        )
        
        return RepositoryListResponse(
            repositories=list(repositories),
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list repositories"
        )


@router.patch(
    "/{repository_id}",
    response_model=RepositoryResponse,
    summary="Update repository settings"
)
async def update_repository(
    repository_id: str,
    request: RepositoryUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """Update repository configuration and settings"""
    try:
        from app.models.repository import Repository
        from sqlalchemy import select
        from uuid import UUID
        from datetime import datetime, timezone
        
        # Convert string to UUID
        try:
            repo_uuid = UUID(repository_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid repository ID format"
            )
        
        # Query repository
        result = await db.execute(
            select(Repository).where(Repository.id == repo_uuid)
        )
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found"
            )
        
        # Check ownership
        if repository.created_by != current_user["sub"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this repository"
            )
        
        # Update fields (only if provided in request)
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(repository, field):
                setattr(repository, field, value)
        
        # Update timestamp
        repository.updated_at = datetime.now(timezone.utc)
        
        # Commit changes
        await db.commit()
        await db.refresh(repository)
        
        logger.info(f"Updated repository {repository_id} for user {current_user['sub']}")
        return repository
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating repository: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update repository"
        )


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a repository"
)
async def delete_repository(
    repository_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """Remove a repository dependency (soft delete by archiving)"""
    try:
        from app.models.repository import Repository
        from sqlalchemy import select
        from uuid import UUID
        from datetime import datetime, timezone
        
        # Convert string to UUID
        try:
            repo_uuid = UUID(repository_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid repository ID format"
            )
        
        # Query repository
        result = await db.execute(
            select(Repository).where(Repository.id == repo_uuid)
        )
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found"
            )
        
        # Check ownership
        if repository.created_by != current_user["sub"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this repository"
            )
        
        # Soft delete by setting status to archived
        repository.status = "archived"
        repository.updated_at = datetime.now(timezone.utc)
        
        # Commit changes
        await db.commit()
        
        logger.info(f"Archived repository {repository_id} for user {current_user['sub']}")
        return None  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting repository: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete repository"
        )


@router.post(
    "/{repository_id}/sync",
    response_model=RepositoryResponse,
    summary="Sync repository with remote"
)
async def sync_repository(
    repository_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """
    Synchronize repository with remote source.
    
    This will:
    1. Fetch latest changes
    2. Update dependency information
    3. Trigger analysis if configured
    """
    try:
        from app.models.repository import Repository
        from sqlalchemy import select
        from uuid import UUID
        from datetime import datetime, timezone
        
        # Convert string to UUID
        try:
            repo_uuid = UUID(repository_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid repository ID format"
            )
        
        # Query repository
        result = await db.execute(
            select(Repository).where(Repository.id == repo_uuid)
        )
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_IMPLEMENTED,
                detail="Repository not found"
            )
        
        # Check ownership
        if repository.created_by != current_user["sub"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to sync this repository"
            )
        
        # Perform sync using repository service
        service = RepositoryService(db)
        
        # Re-validate and update repository information
        repo_info = service.parse_repository_url(repository.repository_url)
        validation = await service.validate_repository(repo_info, repository.branch)
        
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Repository validation failed: {validation.error}"
            )
        
        # Update last synced timestamp
        repository.last_synced = datetime.now(timezone.utc)
        repository.updated_at = datetime.now(timezone.utc)
        
        # Update metadata if available
        if validation.metadata:
            repository.metadata = validation.metadata
        
        # Commit changes
        await db.commit()
        await db.refresh(repository)
        
        logger.info(f"Synced repository {repository_id} for user {current_user['sub']}")
        return repository
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing repository: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync repository: {str(e)}"
        )
