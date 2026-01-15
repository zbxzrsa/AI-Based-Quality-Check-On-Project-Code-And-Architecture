"""
GitHub webhook and integration endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from app.database.postgresql import get_db
from app.models import Project, PullRequest, User, PRStatus
from app.schemas.auth import Message
from app.services.github_client import get_github_client
from app.utils.diff_parser import DiffParser
from app.api.dependencies import get_current_user, check_project_access
from app.services.redis_cache_service import get_cache_service


router = APIRouter()


@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Receive GitHub webhook events
    
    Handles pull_request events (opened, synchronize, closed)
    """
    # Get raw body for signature verification
    body = await request.body()
    payload = await request.json()
    
    # Check for replay protection
    if x_github_delivery:
        cache = await get_cache_service()
        delivery_key = f"webhook:delivery:{x_github_delivery}"
        
        if await cache.cache_exists(delivery_key):
            return {"message": "Webhook already processed"}
        
        # Store delivery ID for 24 hours
        await cache.cache_set(delivery_key, "processed", expiration=86400)
    
    # Get project from repository URL
    repo_full_name = payload.get('repository', {}).get('full_name')
    if not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing repository information"
        )
    
    # Find project by repository URL
    repo_url = f"https://github.com/{repo_full_name}"
    stmt = select(Project).where(Project.github_repo_url == repo_url)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found for repository: {repo_full_name}"
        )
    
    # Verify webhook signature
    if project.github_webhook_secret:
        github_client = get_github_client()
        if not github_client.verify_webhook_signature(
            body,
            x_hub_signature_256 or "",
            project.github_webhook_secret
        ):
            raise HTTPException(
                status_code=httpException.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    
    # Handle different event types
    if x_github_event == "pull_request":
        return await handle_pull_request_event(payload, project, db)
    
    return {"message": f"Event {x_github_event} received but not processed"}


async def handle_pull_request_event(
    payload: Dict[str, Any],
    project: Project,
    db: AsyncSession
) -> Dict[str, str]:
    """Handle pull request webhook event"""
    action = payload.get('action')
    pr_data = payload.get('pull_request', {})
    
    pr_number = pr_data.get('number')
    if not pr_number:
        return {"message": "Invalid PR data"}
    
    # Check if PR already exists
    stmt = select(PullRequest).where(
        PullRequest.project_id == project.id,
        PullRequest.github_pr_number == pr_number
    )
    result = await db.execute(stmt)
    existing_pr = result.scalar_one_or_none()
    
    if action == "opened":
        if existing_pr:
            return {"message": "PR already exists"}
        
        # Create new PR
        pr = PullRequest(
            project_id=project.id,
            github_pr_number=pr_number,
            title=pr_data.get('title'),
            description=pr_data.get('body'),
            branch_name=pr_data.get('head', {}).get('ref'),
            commit_sha=pr_data.get('head', {}).get('sha'),
            files_changed=pr_data.get('changed_files', 0),
            lines_added=pr_data.get('additions', 0),
            lines_deleted=pr_data.get('deletions', 0),
            status=PRStatus.pending
        )
        
        db.add(pr)
        await db.commit()
        await db.refresh(pr)
        
        # Queue analysis task
        cache = await get_cache_service()
        await cache.enqueue_pr_analysis(str(pr.id), {
            "project_id": str(project.id),
            "pr_number": pr_number,
            "commit_sha": pr.commit_sha
        })
        
        return {"message": "PR created and queued for analysis", "pr_id": str(pr.id)}
    
    elif action == "synchronize":
        if not existing_pr:
            return {"message": "PR not found"}
        
        # Update PR with new commit
        existing_pr.commit_sha = pr_data.get('head', {}).get('sha')
        existing_pr.files_changed = pr_data.get('changed_files', 0)
        existing_pr.lines_added = pr_data.get('additions', 0)
        existing_pr.lines_deleted = pr_data.get('deletions', 0)
        existing_pr.status = PRStatus.pending
        
        await db.commit()
        
        # Queue re-analysis
        cache = await get_cache_service()
        await cache.invalidate_analysis(str(existing_pr.id))
        await cache.enqueue_pr_analysis(str(existing_pr.id), {
            "project_id": str(project.id),
            "pr_number": pr_number,
            "commit_sha": existing_pr.commit_sha
        })
        
        return {"message": "PR updated and queued for re-analysis"}
    
    elif action == "closed":
        if existing_pr:
            if pr_data.get('merged'):
                existing_pr.status = PRStatus.approved
            else:
                existing_pr.status = PRStatus.rejected
            
            existing_pr.reviewed_at = datetime.utcnow()
            await db.commit()
        
        return {"message": "PR closed"}
    
    return {"message": f"Action {action} received"}


@router.post("/projects/{project_id}/sync", response_model=Message)
async def sync_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(check_project_access)
):
    """
    Manually trigger project synchronization with GitHub
    """
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get repository info from GitHub
    github_client = get_github_client()
    repo_info = await github_client.get_repository(project.github_repo_url)
    
    # Update project info
    project.language = repo_info.get('language')
    await db.commit()
    
    return Message(message="Project synchronized successfully")


@router.get("/projects/{project_id}/pulls")
async def list_project_pulls(
    project_id: str,
    state: str = "open",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(check_project_access)
):
    """
    List pull requests for a project
    
    - **state**: PR state (open, closed, all)
    """
    # Get project
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get PRs from database
    pr_stmt = select(PullRequest).where(PullRequest.project_id == project_id)
    
    if state != "all":
        status_map = {
            "open": [PRStatus.pending, PRStatus.analyzing, PRStatus.reviewed],
            "closed": [PRStatus.approved, PRStatus.rejected]
        }
        pr_stmt = pr_stmt.where(PullRequest.status.in_(status_map.get(state, [])))
    
    pr_result = await db.execute(pr_stmt)
    prs = pr_result.scalars().all()
    
    return {
        "project_id": project_id,
        "total": len(prs),
        "pull_requests": [
            {
                "id": str(pr.id),
                "number": pr.github_pr_number,
                "title": pr.title,
                "status": pr.status.value,
                "risk_score": pr.risk_score,
                "created_at": pr.created_at.isoformat()
            }
            for pr in prs
        ]
    }


@router.get("/pulls/{pr_id}/files")
async def get_pr_files(
    pr_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get changed files in a pull request
    """
    # Get PR
    stmt = select(PullRequest).where(PullRequest.id == pr_id)
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found"
        )
    
    # Check project access
    await check_project_access(str(pr.project_id), current_user, db)
    
    # Get project to get repo name
    project_stmt = select(Project).where(Project.id == pr.project_id)
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()
    
    if not project or not project.github_repo_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project repository not configured"
        )
    
    # Extract repo full name from URL
    repo_full_name = '/'.join(project.github_repo_url.rstrip('/').split('/')[-2:])
    
    # Get files from GitHub
    github_client = get_github_client()
    files = await github_client.get_pr_files(repo_full_name, pr.github_pr_number)
    
    # Parse diffs
    parsed_files = []
    for file in files:
        file_data = {
            "filename": file['filename'],
            "status": file['status'],
            "additions": file['additions'],
            "deletions": file['deletions'],
            "changes": file['changes']
        }
        
        if file.get('patch'):
            # Parse diff
            diff_parsed = DiffParser.parse_diff(file['patch'])
            if diff_parsed:
                file_data['diff'] = diff_parsed[0]
        
        parsed_files.append(file_data)
    
    return {
        "pr_id": pr_id,
        "pr_number": pr.github_pr_number,
        "files": parsed_files
    }
