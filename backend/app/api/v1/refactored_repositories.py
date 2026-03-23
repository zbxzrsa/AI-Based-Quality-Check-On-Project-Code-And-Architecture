"""
重构后的Repository API端点 - 使用设计模式消除重复代码

应用的改进：
1. 使用重构后的服务消除CRUD重复
2. 统一错误处理
3. 简化端点逻辑
4. 使用状态机管理仓库状态
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Annotated

from app.database.postgresql import get_db
from app.services.refactored_repository_service import create_repository_service
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
    
    The system will automatically:
    1. Validate the repository URL format
    2. Check repository accessibility
    3. Verify branch/tag existence
    4. Extract dependency information
    5. Store repository metadata
    6. Initialize repository state machine
    """
    try:
        service = create_repository_service(db)
        repository = await service.create_entity(request, current_user["sub"])
        
        logger.info(
            f"Repository added successfully: {repository.owner}/{repository.name} "
            f"by user {current_user['sub']}"
        )
        
        return repository
        
    except HTTPException:
        raise
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
        service = create_repository_service(db)
        repo_info = service.parse_repository_url(repository_url)
        validation = await service.validate_repository_access(repo_info, branch)
        
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
        service = create_repository_service(db)
        repository = await service.get_by_id(repository_id, current_user["sub"])
        
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
        service = create_repository_service(db)
        
        # 构建过滤条件
        filters = {}
        if status:
            filters["status"] = status
        
        result = await service.list_entities(
            user_id=current_user["sub"],
            page=page,
            page_size=page_size,
            filters=filters
        )
        
        logger.info(
            f"Listed {len(result['items'])} repositories "
            f"(page {page}/{result['total_pages']}) for user {current_user['sub']}"
        )
        
        return RepositoryListResponse(
            repositories=result["items"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"]
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
        service = create_repository_service(db)
        repository = await service.update_entity(repository_id, request, current_user["sub"])
        
        logger.info(f"Updated repository {repository_id} for user {current_user['sub']}")
        return repository
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating repository: {e}")
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
        service = create_repository_service(db)
        await service.delete_entity(repository_id, current_user["sub"], soft_delete=True)
        
        logger.info(f"Archived repository {repository_id} for user {current_user['sub']}")
        return None  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting repository: {e}")
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
    4. Use state machine to manage the process
    """
    try:
        service = create_repository_service(db)
        result = await service.sync_repository(repository_id, current_user["sub"])
        
        if result["success"]:
            logger.info(f"Synced repository {repository_id} for user {current_user['sub']}")
            return result["repository"]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync repository: {str(e)}"
        )


@router.post(
    "/{repository_id}/archive",
    response_model=dict,
    summary="Archive a repository"
)
async def archive_repository(
    repository_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """
    Archive a repository using state machine.
    
    This will transition the repository to archived state.
    """
    try:
        service = create_repository_service(db)
        result = await service.archive_repository(repository_id, current_user["sub"])
        
        if result["success"]:
            logger.info(f"Archived repository {repository_id} for user {current_user['sub']}")
            return {"message": result["message"]}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive repository"
        )


@router.post(
    "/{repository_id}/reactivate",
    response_model=dict,
    summary="Reactivate a repository"
)
async def reactivate_repository(
    repository_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """
    Reactivate an archived or failed repository using state machine.
    
    This will transition the repository back to active processing.
    """
    try:
        service = create_repository_service(db)
        result = await service.reactivate_repository(repository_id, current_user["sub"])
        
        if result["success"]:
            logger.info(f"Reactivated repository {repository_id} for user {current_user['sub']}")
            return {"message": result["message"]}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate repository"
        )


@router.get(
    "/{repository_id}/status",
    response_model=dict,
    summary="Get repository status"
)
async def get_repository_status(
    repository_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
):
    """
    Get detailed repository status information including state machine state.
    
    Returns:
    - Current state
    - Allowed transitions
    - Last update timestamps
    """
    try:
        service = create_repository_service(db)
        result = await service.get_repository_status(repository_id, current_user["sub"])
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting repository status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get repository status"
        )