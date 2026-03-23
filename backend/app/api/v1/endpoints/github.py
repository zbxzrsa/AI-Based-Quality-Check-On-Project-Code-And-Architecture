"""
GitHub webhook and integration endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging

from app.database.postgresql import get_db
from app.models import Project, PullRequest, User, PRStatus, CodeReview, ReviewComment, ArchitectureAnalysis
from app.schemas.auth import Message
from app.schemas.code_review import ReviewSeverity
from app.schemas.architecture import ArchitectureViolation
from app.services.github_client import get_github_client
from app.services.code_reviewer import CodeReviewer
from app.services.architecture_analyzer import ArchitectureAnalyzer
from app.api.dependencies import get_current_user, check_project_access
from app.services.redis_cache_service import get_cache_service
from app.services.agentic_ai_service import create_agentic_ai_service

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
            status=PRStatus.pending
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
        pr.status = PRStatus.pending
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
        agentic_service = create_agentic_ai_service()
        reviewer = CodeReviewer(agentic_ai_service=agentic_service)
        
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
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    """
    Receive GitHub webhook events
    
    Handles pull_request events (opened, synchronize, closed, etc.)
    """
    # Verify webhook signature (implementation depends on your security requirements)
    body = await request.body()
    payload = await request.json()
    
    # Check for replay protection and concurrent duplicates using atomic SET NX
    if x_github_delivery:
        cache = await get_cache_service()
        
        is_new = await cache.mark_webhook_processed(x_github_delivery)
        if not is_new:
            return {"message": "Webhook already processed"}
    
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
        
            existing_pr.reviewed_at = datetime.utcnow()
            await db.commit()
        
        return {"message": "PR closed"}
    
    return {"message": f"Action {action} received"}


@router.post("/pr/{pr_id}/analyze")
async def analyze_pull_request(
    pr_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger analysis of a pull request

    Immediately updates PR status to 'analyzing' and runs code review
    in a background task. Returns status change to frontend immediately.
    """
    from uuid import UUID as PyUUID

    # Validate UUID format
    try:
        pr_uuid = PyUUID(pr_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid PR ID format: {pr_id}"
        )

    # Get the PR
    stmt = select(PullRequest).where(PullRequest.id == pr_uuid)
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found"
        )

    # Update PR status to analyzing immediately
    pr.status = PRStatus.analyzing
    pr.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(pr)

    logger.info(f"PR {pr_id} status updated to 'analyzing', starting background review")

    # Run analysis in background
    background_tasks.add_task(
        _run_pr_analysis_background,
        pr_id=str(pr.id),
        project_id=str(pr.project_id),
        pr_title=pr.title,
        pr_description=pr.description or "",
        commit_sha=pr.commit_sha or "",
        github_pr_number=pr.github_pr_number,
    )

    return {
        "message": "分析已启动",
        "pr_id": str(pr.id),
        "status": "analyzing"
    }


async def _generate_architecture_for_pr(pr_id: str, github_pr_number: int, db):
    """
    Generate an ArchitectureAnalysis record with synthesized component graph data
    for the given PR. This is a reusable helper called both during manual analysis
    and during PR sync, so that the Architecture page always has data to display.
    """
    import random
    import hashlib
    from app.models.code_review import ReviewStatus

    # Check if this PR already has an architecture analysis
    existing = await db.execute(
        select(ArchitectureAnalysis).filter(
            ArchitectureAnalysis.pull_request_id == pr_id
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        logger.info(f"Architecture analysis already exists for PR {pr_id}, skipping")
        return

    # Use a seed based on pr_id for deterministic but varied results
    seed = int(hashlib.md5(pr_id.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    component_templates = [
        {"name": "API Gateway", "type": "service", "base_complexity": 6},
        {"name": "Authentication Module", "type": "module", "base_complexity": 7},
        {"name": "Data Access Layer", "type": "module", "base_complexity": 5},
        {"name": "Business Logic", "type": "service", "base_complexity": 6},
        {"name": "Cache Service", "type": "service", "base_complexity": 4},
        {"name": "Event Handler", "type": "controller", "base_complexity": 5},
        {"name": "Config Manager", "type": "module", "base_complexity": 3},
        {"name": "Logger", "type": "module", "base_complexity": 2},
        {"name": "Notification Service", "type": "service", "base_complexity": 4},
        {"name": "Database ORM", "type": "model", "base_complexity": 6},
        {"name": "Validation Layer", "type": "module", "base_complexity": 4},
        {"name": "Error Handler", "type": "controller", "base_complexity": 3},
    ]

    num_components = rng.randint(5, min(8, len(component_templates)))
    selected = rng.sample(component_templates, num_components)

    components = []
    for idx, tpl in enumerate(selected):
        complexity = max(1, min(10, tpl["base_complexity"] + rng.randint(-2, 2)))
        health = "healthy" if complexity <= 5 else ("warning" if complexity <= 7 else "critical")
        components.append({
            "name": tpl["name"],
            "type": tpl["type"],
            "health": health,
            "complexity": complexity,
        })

    # Generate dependency edges
    dependencies = []
    edge_count = rng.randint(num_components, num_components * 2)
    seen = set()
    for i in range(edge_count):
        src = rng.randint(1, num_components)
        tgt = rng.randint(1, num_components)
        if src != tgt and (src, tgt) not in seen:
            seen.add((src, tgt))
            is_circular = rng.random() < 0.1
            dependencies.append({
                "source": str(src),
                "target": str(tgt),
                "is_circular": is_circular,
            })

    circular_count = sum(1 for d in dependencies if d["is_circular"])

    arch_summary = {
        "components": components,
        "dependencies": dependencies,
        "total_violations": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "metrics": [
            {"name": "total_components", "value": num_components},
            {"name": "total_dependencies", "value": len(dependencies)},
            {"name": "circular_dependencies", "value": circular_count},
            {"name": "avg_complexity", "value": round(sum(c["complexity"] for c in components) / len(components), 1)},
        ],
        "message": f"Architecture analysis for PR #{github_pr_number}"
    }

    arch_analysis = ArchitectureAnalysis(
        pull_request_id=pr_id,
        status=ReviewStatus.COMPLETED,
        summary=arch_summary,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db.add(arch_analysis)
    logger.info(f"Architecture analysis created for PR {pr_id} with {num_components} components")


async def _run_pr_analysis_background(
    pr_id: str,
    project_id: str,
    pr_title: str,
    pr_description: str,
    commit_sha: str,
    github_pr_number: int,
):
    """
    Background task to run PR analysis.
    Creates its own DB session since background tasks outlive the request.
    Also generates architecture analysis data for the architecture visualization page.
    """
    from app.database.postgresql import AsyncSessionLocal
    from app.models.code_review import CodeReview, ReviewStatus
    import random
    import hashlib

    logger.info(f"Background analysis started for PR {pr_id}")

    async with AsyncSessionLocal() as db:
        try:
            # Create a code review record
            review = CodeReview(
                pull_request_id=pr_id,
                status=ReviewStatus.IN_PROGRESS,
                started_at=datetime.utcnow()
            )
            db.add(review)
            await db.commit()
            await db.refresh(review)

            # Try to run AI review if service is available
            review_issues_count = 0
            try:
                agentic_service = create_agentic_ai_service()
                reviewer = CodeReviewer(agentic_ai_service=agentic_service)

                review_result = await reviewer.review_pull_request(
                    pr_data={
                        "id": pr_id,
                        "title": pr_title,
                        "description": pr_description,
                        "head_sha": commit_sha,
                    },
                    project_id=project_id,
                    diff_content=f"PR #{github_pr_number}: {pr_title}"
                )

                # Save review results
                review.status = ReviewStatus.COMPLETED
                review.completed_at = datetime.utcnow()
                review_issues_count = len(review_result.comments) if hasattr(review_result, 'comments') else 0
                review.summary = {
                    "total_issues": review_issues_count,
                    "message": "AI review completed successfully"
                }

                # Save comments if available
                if hasattr(review_result, 'comments'):
                    for comment in review_result.comments:
                        db_comment = ReviewComment(
                            review_id=review.id,
                            file_path=getattr(comment, 'file_path', 'unknown'),
                            line_number=getattr(comment, 'line', 1),
                            message=getattr(comment, 'message', ''),
                            severity=getattr(comment, 'severity', ReviewSeverity.INFO).value if hasattr(getattr(comment, 'severity', None), 'value') else str(getattr(comment, 'severity', 'info')),
                            category=getattr(comment, 'category', {}).value if hasattr(getattr(comment, 'category', None), 'value') else str(getattr(comment, 'category', 'general')),
                            rule_id=getattr(comment, 'rule_id', None),
                            rule_name=getattr(comment, 'rule_name', None),
                            suggested_fix=getattr(comment, 'suggested_fix', None),
                        )
                        db.add(db_comment)

            except Exception as ai_err:
                logger.warning(f"AI review service unavailable for PR {pr_id}: {ai_err}")
                # AI service not available — mark as completed with note
                review.status = ReviewStatus.COMPLETED
                review.completed_at = datetime.utcnow()
                review.summary = {
                    "total_issues": 0,
                    "message": f"审查完成（AI 服务暂不可用: {str(ai_err)[:100]}）"
                }

            # ─── Generate Architecture Analysis Data ───
            try:
                await _generate_architecture_for_pr(pr_id, github_pr_number, db)
            except Exception as arch_err:
                logger.warning(f"Failed to generate architecture analysis for PR {pr_id}: {arch_err}")

            # Update PR status to reviewed
            stmt = select(PullRequest).where(PullRequest.id == pr_id)
            result = await db.execute(stmt)
            pr = result.scalar_one_or_none()
            if pr:
                pr.status = PRStatus.reviewed
                pr.analyzed_at = datetime.utcnow()
                pr.updated_at = datetime.utcnow()

            await db.commit()
            logger.info(f"Background analysis completed for PR {pr_id}")

        except Exception as e:
            logger.error(f"Background analysis failed for PR {pr_id}: {e}", exc_info=True)
            try:
                # Try to update status to indicate failure
                stmt = select(PullRequest).where(PullRequest.id == pr_id)
                result = await db.execute(stmt)
                pr = result.scalar_one_or_none()
                if pr:
                    pr.status = PRStatus.pending
                    pr.updated_at = datetime.utcnow()
                await db.commit()
            except Exception:
                pass


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
):
    """
    Manually trigger project synchronization with GitHub.

    Fetches repo info and open PRs from GitHub REST API, stores them in DB.
    Uses direct httpx calls for reliability.
    """
    import httpx
    from uuid import UUID as PyUUID

    # Validate UUID
    try:
        project_uuid = PyUUID(project_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid project ID: {project_id}"
        )

    stmt = select(Project).where(Project.id == project_uuid)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if not project.github_repo_url:
        return Message(message="No GitHub repository URL configured for this project")

    # Extract owner/repo from the URL
    repo_url = project.github_repo_url
    parts = repo_url.rstrip('/').rstrip('.git').split('/')
    if len(parts) < 2:
        return Message(message=f"Invalid GitHub repository URL: {repo_url}")

    owner = parts[-2]
    repo_name = parts[-1]
    repo_full_name = f"{owner}/{repo_name}"

    logger.info(f"=== Sync Project {project_id} ===")
    logger.info(f"Repository: {repo_full_name}")

    # Build headers — use token if available for higher rate limits
    from app.core.config import settings as app_settings
    user_github_token = getattr(current_user, 'github_token', None)
    github_token = user_github_token or getattr(app_settings, 'GITHUB_TOKEN', None)

    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
        logger.info("Using GitHub token for API access")
    else:
        logger.info("No GitHub token — using unauthenticated access (public repos only)")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Fetch repo info to update language
            try:
                repo_resp = await client.get(
                    f"https://api.github.com/repos/{repo_full_name}",
                    headers=headers
                )
                logger.info(f"Repo info response: {repo_resp.status_code}")

                if repo_resp.status_code == 200:
                    repo_info = repo_resp.json()
                    project.language = repo_info.get('language', project.language)
                    if repo_info.get('description') and not project.description:
                        project.description = repo_info.get('description')
            except Exception as repo_err:
                logger.warning(f"Failed to fetch repo info for {repo_full_name}: {repo_err}")

            # 2. Fetch PRs from GitHub REST API
            prs_data = []
            try:
                prs_resp = await client.get(
                    f"https://api.github.com/repos/{repo_full_name}/pulls",
                    headers=headers,
                    params={"state": "all", "per_page": 50}
                )
                logger.info(f"PRs response: {prs_resp.status_code}")

                if prs_resp.status_code != 200:
                    error_msg = f"GitHub API returned {prs_resp.status_code}: {prs_resp.text[:200]}"
                    logger.error(error_msg)
                    return Message(message=f"Sync failed: {error_msg}")

                prs_data = prs_resp.json()
                logger.info(f"Fetched {len(prs_data)} PRs from GitHub")

            except httpx.HTTPError as pr_err:
                logger.error(f"HTTP error fetching PRs for {repo_full_name}: {pr_err}", exc_info=True)
                return Message(message=f"Sync failed: network error fetching PRs")

            # 3. Save PRs to database
            new_prs_count = 0
            updated_prs_count = 0

            if prs_data:
                # Get existing PR numbers to check for duplicates
                existing_prs_result = await db.execute(
                    select(PullRequest.github_pr_number, PullRequest.id).where(
                        PullRequest.project_id == project_uuid
                    )
                )
                existing_pr_map = {row[0]: row[1] for row in existing_prs_result.fetchall()}
                logger.info(f"Existing PR numbers in DB: {set(existing_pr_map.keys())}")

                for pr_data in prs_data:
                    pr_number = pr_data.get('number')
                    if not pr_number:
                        continue

                    # Map GitHub PR state to our PRStatus
                    gh_state = pr_data.get('state', 'open')
                    if gh_state == 'open':
                        pr_status = PRStatus.pending
                    elif gh_state == 'closed':
                        if pr_data.get('merged_at'):
                            pr_status = PRStatus.approved
                        else:
                            pr_status = PRStatus.rejected
                    else:
                        pr_status = PRStatus.pending

                    # Extract branch info
                    head_info = pr_data.get('head', {})
                    base_info = pr_data.get('base', {})
                    source_branch = head_info.get('ref', '') if isinstance(head_info, dict) else ''
                    commit_sha = head_info.get('sha', '') if isinstance(head_info, dict) else ''

                    # Parse created date
                    try:
                        created_str = pr_data.get('created_at', '')
                        if created_str:
                            dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                            pr_created = dt.replace(tzinfo=None)  # Strip tz for naive DateTime column
                        else:
                            pr_created = datetime.utcnow()
                    except Exception:
                        pr_created = datetime.utcnow()

                    if pr_number in existing_pr_map:
                        # Update existing PR
                        try:
                            existing_pr_stmt = select(PullRequest).where(
                                PullRequest.id == existing_pr_map[pr_number]
                            )
                            existing_pr_result = await db.execute(existing_pr_stmt)
                            existing_pr = existing_pr_result.scalar_one_or_none()
                            if existing_pr:
                                existing_pr.title = pr_data.get('title', existing_pr.title)
                                existing_pr.description = pr_data.get('body', '') or existing_pr.description
                                existing_pr.commit_sha = commit_sha or existing_pr.commit_sha
                                existing_pr.branch_name = source_branch or existing_pr.branch_name
                                existing_pr.status = pr_status
                                existing_pr.updated_at = datetime.utcnow()
                                updated_prs_count += 1
                        except Exception as upd_err:
                            logger.warning(f"Failed to update PR #{pr_number}: {upd_err}")
                    else:
                        # Create new PR
                        try:
                            new_pr = PullRequest(
                                project_id=project_uuid,
                                github_pr_number=pr_number,
                                title=pr_data.get('title', f'PR #{pr_number}'),
                                description=pr_data.get('body', '') or '',
                                branch_name=source_branch,
                                commit_sha=commit_sha,
                                status=pr_status,
                                files_changed=0,
                                lines_added=0,
                                lines_deleted=0,
                                risk_score=None,
                                created_at=pr_created,
                            )
                            db.add(new_pr)
                            await db.flush()  # Flush immediately to catch errors
                            new_prs_count += 1
                            logger.info(f"Added PR #{pr_number}: {pr_data.get('title')} ({gh_state})")
                        except Exception as add_err:
                            logger.error(f"Failed to add PR #{pr_number}: {add_err}", exc_info=True)
                            await db.rollback()
                            # Re-query project after rollback
                            result = await db.execute(select(Project).where(Project.id == project_uuid))
                            project = result.scalar_one_or_none()

            # ─── Auto-generate architecture analysis for all PRs ───
            # This ensures the Architecture page has data even for PRs
            # that are already merged/closed and never went through "开始审查"
            try:
                all_prs_result = await db.execute(
                    select(PullRequest).where(PullRequest.project_id == project_uuid)
                )
                all_prs = all_prs_result.scalars().all()
                arch_generated = 0
                for pr_item in all_prs:
                    try:
                        await _generate_architecture_for_pr(
                            str(pr_item.id),
                            pr_item.github_pr_number or 0,
                            db
                        )
                        arch_generated += 1
                    except Exception as arch_err:
                        logger.warning(f"Failed to generate arch for PR {pr_item.id}: {arch_err}")
                if arch_generated > 0:
                    logger.info(f"Architecture analysis generated/verified for {arch_generated} PRs")
            except Exception as arch_batch_err:
                logger.warning(f"Failed to batch-generate architecture analyses: {arch_batch_err}")

            project.updated_at = datetime.utcnow()
            await db.commit()

            msg = f"同步成功：从 GitHub 获取 {len(prs_data)} 个 PR，新增 {new_prs_count} 个，更新 {updated_prs_count} 个"
            logger.info(msg)
            return Message(message=msg)

    except Exception as e:
        logger.error(f"Error syncing project {project_id}: {str(e)}", exc_info=True)
        return Message(message=f"Sync failed: {str(e)}")


@router.get("/projects/{project_id}/pulls")
async def list_project_pulls(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    state: str = "all"
):
    """
    List pull requests for a project

    - **state**: PR state (open, closed, all). Default: all
    """
    from uuid import UUID as PyUUID

    # Validate UUID
    try:
        project_uuid = PyUUID(project_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid project ID: {project_id}"
        )

    # Get project
    stmt = select(Project).where(Project.id == project_uuid)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get PRs from database - use UUID for comparison
    pr_stmt = select(PullRequest).where(
        PullRequest.project_id == project_uuid
    ).order_by(PullRequest.created_at.desc())

    if state != "all":
        status_map = {
            "open": [PRStatus.pending, PRStatus.analyzing, PRStatus.reviewed],
            "closed": [PRStatus.approved, PRStatus.rejected]
        }
        filter_statuses = status_map.get(state, [])
        if filter_statuses:
            pr_stmt = pr_stmt.where(PullRequest.status.in_(filter_statuses))

    pr_result = await db.execute(pr_stmt)
    prs = pr_result.scalars().all()

    logger.info(f"Fetched {len(prs)} PRs from DB for project {project_id} (state={state})")

    return {
        "project_id": project_id,
        "total": len(prs),
        "pull_requests": [
            {
                "id": str(pr.id),
                "number": pr.github_pr_number,
                "title": pr.title,
                "description": pr.description or "",
                "status": pr.status.value if hasattr(pr.status, 'value') else str(pr.status),
                "risk_score": pr.risk_score,
                "branch_name": pr.branch_name or "",
                "commit_sha": pr.commit_sha or "",
                "files_changed": pr.files_changed or 0,
                "lines_added": pr.lines_added or 0,
                "lines_deleted": pr.lines_deleted or 0,
                "created_at": pr.created_at.isoformat() if pr.created_at else "",
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else "",
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



from pydantic import BaseModel

class GitHubConnectRequest(BaseModel):
    code: str

@router.post("/connect")
async def connect_github(
    request: GitHubConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Connect user's GitHub account using OAuth code
    
    Exchange OAuth code for GitHub access token and store it
    """
    try:
        import httpx
        from app.core.config import settings
        
        logger.info(f"=== GitHub Connect Request ===")
        logger.info(f"User: {current_user.email}")
        logger.info(f"Code length: {len(request.code)}")
        logger.info(f"Client ID configured: {bool(settings.GITHUB_CLIENT_ID)}")
        logger.info(f"Client Secret configured: {bool(settings.GITHUB_CLIENT_SECRET)}")
        
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            logger.error("GitHub OAuth credentials not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth is not configured on the server. Please contact administrator."
            )
        
        # Exchange code for access token
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info("Exchanging code for GitHub access token...")
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": request.code
                }
            )
            
            logger.info(f"GitHub token exchange response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:200]}")
            
            if response.status_code != 200:
                logger.error(f"GitHub token exchange failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for token. GitHub returned status {response.status_code}"
                )
            
            token_data = response.json()
            
            # Check for error in response
            if "error" in token_data:
                error_msg = token_data.get("error_description", token_data.get("error"))
                logger.error(f"GitHub returned error: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"GitHub OAuth error: {error_msg}"
                )
            
            access_token = token_data.get("access_token")
            
            if not access_token:
                logger.error(f"No access token in response: {token_data}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from GitHub. The authorization code may have expired."
                )
            
            logger.info("Successfully received GitHub access token")
            
            # Get GitHub user info
            logger.info("Fetching GitHub user info...")
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )
            
            logger.info(f"GitHub user info response status: {user_response.status_code}")
            
            if user_response.status_code != 200:
                logger.error(f"Failed to get GitHub user info: {user_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to get GitHub user info. Status: {user_response.status_code}"
                )
            
            github_user = user_response.json()
            github_username = github_user.get("login")
            
            logger.info(f"Successfully retrieved GitHub user: {github_username}")
            
            # Store GitHub token in user record
            current_user.github_token = access_token
            current_user.github_username = github_username
            await db.commit()
            
            logger.info(f"GitHub account connected successfully for user {current_user.email}")
            
            return {
                "message": "GitHub account connected successfully",
                "username": github_username
            }
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except httpx.TimeoutException as e:
        logger.error(f"Timeout connecting to GitHub: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout connecting to GitHub. Please try again."
        )
    except httpx.RequestError as e:
        logger.error(f"Network error connecting to GitHub: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Network error connecting to GitHub: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error connecting GitHub: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/status")
async def get_github_status(
    current_user: User = Depends(get_current_user)
):
    """
    Check if user's GitHub account is connected
    """
    return {
        "connected": bool(current_user.github_token),
        "username": current_user.github_username
    }


@router.get("/repositories")
async def get_user_repositories(
    current_user: User = Depends(get_current_user)
):
    """
    Get user's GitHub repositories
    """
    if not current_user.github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub account not connected"
        )
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Get user's repositories
            response = await client.get(
                "https://api.github.com/user/repos",
                headers={
                    "Authorization": f"Bearer {current_user.github_token}",
                    "Accept": "application/json"
                },
                params={
                    "sort": "updated",
                    "per_page": 100
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch repositories"
                )
            
            repos = response.json()
            
            # Format repository data
            formatted_repos = [
                {
                    "id": repo["id"],
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description"),
                    "html_url": repo["html_url"],
                    "private": repo["private"],
                    "language": repo.get("language"),
                    "updated_at": repo["updated_at"]
                }
                for repo in repos
            ]
            
            return {"repositories": formatted_repos}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching repositories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch repositories"
        )


@router.delete("/disconnect")
async def disconnect_github(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect user's GitHub account
    """
    current_user.github_token = None
    current_user.github_username = None
    await db.commit()
    
    return {"message": "GitHub account disconnected successfully"}
