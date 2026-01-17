"""
Pull Request Analysis endpoints
Handles PR creation, analysis status, and results
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database.postgresql import get_db
from app.models import PullRequest, Project
from app.schemas.auth import Message
from app.api.dependencies import get_current_user, check_project_access
from app.tasks.pull_request_analysis import analyze_pull_request_sync
from celery.result import AsyncResult
from app.celery_config import celery_app


router = APIRouter()


@router.post("/projects/{project_id}/analyze")
async def analyze_pull_request_endpoint(
    project_id: str,
    pr_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _ = Depends(lambda: check_project_access(project_id, current_user))
):
    """
    Queue a pull request for asynchronous analysis
    
    Returns immediately with task ID for polling
    
    Query Parameters:
    - pr_id: Pull request database ID
    
    Returns:
    {
        "task_id": "abc123...",
        "status": "PENDING",
        "pr_id": "...",
        "message": "PR analysis queued and will begin shortly"
    }
    """
    # Verify PR exists and belongs to project
    stmt = select(PullRequest).where(
        PullRequest.id == pr_id,
        PullRequest.project_id == project_id
    )
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found"
        )
    
    # Queue async task
    task_result = analyze_pull_request_sync(pr_id, project_id)
    
    return task_result


@router.get("/analysis/{task_id}/status")
async def get_analysis_status(
    task_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get the status of an analysis task
    
    Returns:
    {
        "task_id": "abc123...",
        "status": "PENDING|PROGRESS|SUCCESS|FAILURE",
        "result": {...},
        "error": null or error message
    }
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.status == 'PENDING':
        response["result"] = None
        response["error"] = None
    elif task_result.status == 'SUCCESS':
        response["result"] = task_result.result
        response["error"] = None
    elif task_result.status == 'FAILURE':
        response["result"] = None
        response["error"] = str(task_result.info)
    elif task_result.status == 'RETRY':
        response["result"] = None
        response["error"] = "Task is retrying"
    
    return response


@router.post("/projects/{project_id}/pull-requests/{pr_id}/reanalyze")
async def reanalyze_pull_request(
    project_id: str,
    pr_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _ = Depends(lambda: check_project_access(project_id, current_user))
):
    """
    Re-analyze an existing pull request
    
    Useful for retrying failed analyses or analyzing with updated rules
    
    Returns task info with task_id
    """
    # Verify PR exists
    stmt = select(PullRequest).where(
        PullRequest.id == pr_id,
        PullRequest.project_id == project_id
    )
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found"
        )
    
    # Queue new analysis task
    task_result = analyze_pull_request_sync(pr_id, project_id)
    
    return {
        "message": "PR re-analysis queued",
        **task_result
    }
