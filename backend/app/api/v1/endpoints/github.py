"""
GitHub webhook and integration endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, BackgroundTasks
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import json
import logging

from app.database.postgresql import get_db
from app.models import Project, PullRequest, User, PRStatus, CodeReview, ReviewComment, ArchitectureAnalysis
from app.schemas.auth import Message
from app.schemas.code_review import CodeReviewResult, ReviewComment as ReviewCommentSchema, ReviewSeverity
from app.schemas.architecture import ArchitectureReport, ArchitectureViolation
from app.services.github_client import get_github_client
from app.services.code_reviewer import CodeReviewer
from app.services.architecture_analyzer import ArchitectureAnalyzer
from app.utils.diff_parser import DiffParser
from app.api.dependencies import get_current_user, check_project_access
from app.services.redis_cache_service import get_cache_service
from app.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


router = APIRouter()


async def process_pull_request_event(
    payload: Dict[str, Any],
    project: Project,
    db: AsyncSession
) -> Dict[str, Any]:
    """Process pull request event and trigger analysis"""
    pr_data = payload.get('pull_request', {})
    action = payload.get('action')
    
    if action not in ['opened', 'synchronize', 'reopened']:
        return {"message": f"Action '{action}' not supported"}
    
    # Get or create PR record
    pr_number = pr_data.get('number')
    stmt = select(PullRequest).where(
        PullRequest.project_id == project.id,
        PullRequest.github_pr_number == pr_number
    )
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()
    
    if not pr:
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
            status=PRStatus.PENDING
        )
        db.add(pr)
        await db.commit()
        await db.refresh(pr)
    else:
        # Update existing PR
        pr.title = pr_data.get('title', pr.title)
        pr.description = pr_data.get('body', pr.description)
        pr.commit_sha = pr_data.get('head', {}).get('sha', pr.commit_sha)
        pr.files_changed = pr_data.get('changed_files', pr.files_changed)
        pr.lines_added = pr_data.get('additions', pr.lines_added)
        pr.lines_deleted = pr_data.get('deletions', pr.lines_deleted)
        pr.status = PRStatus.PENDING
        await db.commit()
    
    # Queue analysis tasks
    cache = await get_cache_service()
    await cache.enqueue_pr_analysis(str(pr.id), {
        "project_id": str(project.id),
        "pr_number": pr_number,
        "commit_sha": pr.commit_sha,
        "action": action
    })
    
    return {"message": "PR processing started", "pr_id": str(pr.id)}


async def run_code_review(pr_id: str, project_id: str, diff_content: str, db: AsyncSession) -> CodeReview:
    """Run code review analysis on a pull request"""
    # Create a new code review record
    review = CodeReview(
        pull_request_id=pr_id,
        status="in_progress",
        started_at=datetime.utcnow()
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    
    try:
        # Initialize code reviewer
        reviewer = CodeReviewer()
        
        # Get PR data
        stmt = select(PullRequest).where(PullRequest.id == pr_id)
        result = await db.execute(stmt)
        pr = result.scalar_one_or_none()
        
        if not pr:
            raise ValueError(f"Pull request {pr_id} not found")
        
        # Run the review
        review_result = await reviewer.review_pull_request(
            pr_data={
                "id": pr_id,
                "title": pr.title,
                "description": pr.description,
                "head_sha": pr.commit_sha
            },
            project_id=project_id,
            diff_content=diff_content
        )
        
        # Save review results
        review.status = "completed"
        review.completed_at = datetime.utcnow()
        review.summary = {
            "total_issues": len(review_result.comments),
            "severity_counts": {
                "critical": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.CRITICAL),
                "high": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.HIGH),
                "medium": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.MEDIUM),
                "low": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.LOW),
                "info": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.INFO)
            }
        }
        
        # Save individual comments
        for comment in review_result.comments:
            db_comment = ReviewComment(
                review_id=review.id,
                file_path=comment.file_path,
                line_number=comment.line,
                message=comment.message,
                severity=comment.severity.value,
                category=comment.category.value if hasattr(comment, 'category') else None,
                rule_id=comment.rule_id,
                rule_name=comment.rule_name,
                suggested_fix=comment.suggested_fix
            )
            db.add(db_comment)
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error running code review: {str(e)}", exc_info=True)
        review.status = "failed"
        review.error = str(e)
        await db.commit()
    
    return review


async def run_architecture_analysis(
    pr_id: str,
    project_id: str,
    db: AsyncSession
) -> ArchitectureAnalysis:
    """Run architectural analysis on the codebase"""
    # Create a new analysis record
    analysis = ArchitectureAnalysis(
        pull_request_id=pr_id,
        status="in_progress",
        started_at=datetime.utcnow()
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    
    try:
        # Initialize architecture analyzer
        analyzer = ArchitectureAnalyzer()
        
        # Run the analysis
        report = await analyzer.analyze_architecture(project_id)
        
        # Save analysis results
        analysis.status = "completed"
        analysis.completed_at = datetime.utcnow()
        analysis.summary = {
            "total_violations": len(report.violations),
            "severity_counts": {
                "critical": sum(1 for v in report.violations if v.severity == "critical"),
                "high": sum(1 for v in report.violations if v.severity == "high"),
                "medium": sum(1 for v in report.violations if v.severity == "medium"),
                "low": sum(1 for v in report.violations if v.severity == "low")
            },
            "metrics": [{"name": m.name, "value": m.value} for m in report.metrics]
        }
        
        # Save violations
        for violation in report.violations:
            db_violation = ArchitectureViolation(
                analysis_id=analysis.id,
                type=violation.type.value,
                component=violation.component,
                related_component=violation.related_component,
                message=violation.message,
                severity=violation.severity,
                file_path=violation.file_path,
                line_number=violation.line_number,
                suggested_fix=violation.suggested_fix,
                rule_id=violation.rule_id,
                rule_name=violation.rule_name
            )
            db.add(db_violation)
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error running architecture analysis: {str(e)}", exc_info=True)
        analysis.status = "failed"
        analysis.error = str(e)
        await db.commit()
    
    return analysis


@router.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Receive GitHub webhook events
    
    Handles pull_request events (opened, synchronize, closed, etc.)
    """
    # Verify webhook signature (implementation depends on your security requirements)
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
    event_type = x_github_event
    
    if event_type == 'ping':
        return {"message": "pong"}
        
    elif event_type == 'pull_request':
        # Get repository information
        repo_name = payload.get('repository', {}).get('full_name')
        if not repo_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repository information not found in payload"
            )
        
        # Find project by repository name
        stmt = select(Project).where(Project.github_repo == repo_name)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with repository {repo_name} not found"
            )
        
        # Handle PR event in the background
        background_tasks.add_task(
            process_pull_request_event,
            payload=payload,
            project=project,
            db=db
        )
        
        return {"message": "PR processing started in the background"}
    
    return {"message": f"Unhandled event type: {event_type}"}


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
        
            existing_pr.reviewed_at = datetime.now(datetime.utcnow().tzinfo)
            await db.commit()
        
        return {"message": "PR closed"}
    
    return {"message": f"Action {action} received"}


@router.post("/pr/{pr_id}/analyze")
async def analyze_pull_request(
    pr_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger analysis of a pull request
    
    This endpoint can be used to manually trigger analysis of a pull request
    that has already been created.
    """
    # Get the PR
    stmt = select(PullRequest).where(PullRequest.id == pr_id)
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found"
        )
    
    # Check permissions
    if not await check_project_access(pr.project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this PR"
        )
    
    # Queue analysis
    cache = await get_cache_service()
    await cache.enqueue_pr_analysis(pr_id, {
        "project_id": str(pr.project_id),
        "pr_number": pr.github_pr_number,
        "commit_sha": pr.commit_sha,
        "action": "manual_trigger"
    })
    
    return {"message": "Analysis queued", "pr_id": pr_id}


@router.get("/pr/{pr_id}/review")
async def get_code_review(
    pr_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get code review results for a pull request
    """
    # Get the PR
    stmt = select(PullRequest).where(PullRequest.id == pr_id)
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found"
        )
    
    # Check permissions
    if not await check_project_access(pr.project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this PR"
        )
    
    # Get the latest review
    stmt = select(CodeReview)\
        .where(CodeReview.pull_request_id == pr_id)\
        .order_by(CodeReview.started_at.desc())\
        .limit(1)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No code review found for this PR"
        )
    
    # Get review comments
    stmt = select(ReviewComment).where(ReviewComment.review_id == review.id)
    result = await db.execute(stmt)
    comments = result.scalars().all()
    
    return {
        "review_id": str(review.id),
        "status": review.status,
        "started_at": review.started_at,
        "completed_at": review.completed_at,
        "summary": review.summary,
        "comments": [{
            "id": str(comment.id),
            "file_path": comment.file_path,
            "line_number": comment.line_number,
            "message": comment.message,
            "severity": comment.severity,
            "category": comment.category,
            "suggested_fix": comment.suggested_fix,
            "rule_id": comment.rule_id,
            "rule_name": comment.rule_name
        } for comment in comments]
    }


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
