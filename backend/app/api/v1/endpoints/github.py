"""
GitHub webhook and integration endpoints
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import check_project_access, get_current_user
from app.database.postgresql import get_db
from app.models import ArchitectureAnalysis, CodeReview, PRStatus, Project, PullRequest, ReviewComment, ReviewResult, User
from app.schemas.architecture import ArchitectureViolation
from app.schemas.auth import Message
from app.schemas.code_review import ReviewSeverity
from app.services.agentic_ai_service import create_agentic_ai_service
from app.services.architecture_analyzer import ArchitectureAnalyzer
from app.services.code_reviewer import CodeReviewer
from app.services.encryption_service import decrypt_if_possible
from app.services.github_client import GitHubAPIClient, get_github_client
from app.services.redis_cache_service import get_cache_service
from app.tasks.pull_request_analysis import analyze_pull_request_sync
from app.utils.diff_parser import DiffParser

logger = logging.getLogger(__name__)


router = APIRouter()


def _extract_repo_full_name(repo_url: str | None) -> str:
    """Extract owner/repository from a GitHub URL."""
    if not repo_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project repository not configured")

    normalized = repo_url.rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    parts = normalized.split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid GitHub repository URL")

    return f"{parts[-2]}/{parts[-1]}"


def _get_user_github_client(current_user: User) -> GitHubAPIClient:
    """Get a GitHub client using the current user's OAuth token when available."""
    if current_user.github_token:
        return GitHubAPIClient(current_user.github_token)
    return get_github_client()


def _map_github_pr_state(pr_data: dict[str, Any]) -> PRStatus:
    """Map GitHub PR state into local PR status enum."""
    if pr_data.get("merged"):
        return PRStatus.MERGED

    state = str(pr_data.get("state", "")).lower()
    if state == "closed":
        return PRStatus.REJECTED
    if state == "open":
        return PRStatus.PENDING
    return PRStatus.PENDING


def _build_fallback_comments_from_review_result(review_result: ReviewResult | None) -> list[dict[str, Any]]:
    """Convert legacy ReviewResult.ai_suggestions JSON into review comments."""
    if not review_result or not review_result.ai_suggestions:
        return []

    try:
        issues = review_result.ai_suggestions
        if isinstance(issues, str):
            issues = json.loads(issues)
    except (TypeError, json.JSONDecodeError):
        return []

    if not isinstance(issues, list):
        return []

    comments: list[dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue

        comments.append(
            {
                "id": issue.get("id") or f"legacy-{len(comments) + 1}",
                "file_path": issue.get("file", "unknown"),
                "line_number": issue.get("line", 1),
                "message": issue.get("description") or issue.get("title") or "AI review finding",
                "severity": issue.get("severity", "info"),
                "category": issue.get("type", "quality"),
                "suggested_fix": issue.get("suggestion"),
                "rule_id": issue.get("type"),
                "rule_name": issue.get("title"),
            }
        )

    return comments


async def _get_project_by_id_or_404(project_id: str, db: AsyncSession) -> Project:
    """Get project by id or raise 404."""
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def _get_pull_request_or_404(pr_id: str, db: AsyncSession) -> PullRequest:
    """Get pull request by id or raise 404."""
    stmt = select(PullRequest).where(PullRequest.id == pr_id)
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pull request not found")
    return pr


async def _ensure_project_access(project_id: str, current_user: User, db: AsyncSession) -> None:
    """Enforce project access permission."""
    if not await check_project_access(project_id, current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to access this PR")


async def _enqueue_pr_analysis(
    pr_id: str,
    *,
    project_id: str,
    pr_number: int,
    commit_sha: str | None,
    action: str,
) -> None:
    """Enqueue PR analysis payload to cache queue."""
    cache = await get_cache_service()
    await cache.enqueue_pr_analysis(
        pr_id,
        {
            "project_id": project_id,
            "pr_number": pr_number,
            "commit_sha": commit_sha,
            "action": action,
        },
    )


async def process_pull_request_event(payload: dict[str, Any], project: Project, db: AsyncSession) -> dict[str, Any]:
    """Process pull request event and trigger analysis"""
    pr_data = payload.get("pull_request", {})
    action = payload.get("action")

    if action not in ["opened", "synchronize", "reopened"]:
        return {"message": f"Action '{action}' not supported"}

    # Get or create PR record
    pr_number = pr_data.get("number")
    stmt = select(PullRequest).where(PullRequest.project_id == project.id, PullRequest.github_pr_number == pr_number)
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()

    if not pr:
        pr = PullRequest(
            project_id=project.id,
            github_pr_number=pr_number,
            title=pr_data.get("title"),
            description=pr_data.get("body"),
            branch_name=pr_data.get("head", {}).get("ref"),
            commit_sha=pr_data.get("head", {}).get("sha"),
            files_changed=pr_data.get("changed_files", 0),
            lines_added=pr_data.get("additions", 0),
            lines_deleted=pr_data.get("deletions", 0),
            status=PRStatus.PENDING,
        )
        db.add(pr)
        await db.commit()
        await db.refresh(pr)
    else:
        # Update existing PR
        pr.title = pr_data.get("title", pr.title)
        pr.description = pr_data.get("body", pr.description)
        pr.commit_sha = pr_data.get("head", {}).get("sha", pr.commit_sha)
        pr.files_changed = pr_data.get("changed_files", pr.files_changed)
        pr.lines_added = pr_data.get("additions", pr.lines_added)
        pr.lines_deleted = pr_data.get("deletions", pr.lines_deleted)
        pr.status = PRStatus.PENDING
        await db.commit()

    # Queue analysis tasks
    await _enqueue_pr_analysis(
        str(pr.id),
        project_id=str(project.id),
        pr_number=pr_number,
        commit_sha=pr.commit_sha,
        action=action,
    )

    return {"message": "PR processing started", "pr_id": str(pr.id)}


async def run_code_review(pr_id: str, project_id: str, diff_content: str, db: AsyncSession) -> CodeReview:
    """Run code review analysis on a pull request"""
    # Create a new code review record
    review = CodeReview(pull_request_id=pr_id, status="in_progress", started_at=datetime.now(timezone.utc))
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
            pr_data={"id": pr_id, "title": pr.title, "description": pr.description, "head_sha": pr.commit_sha},
            project_id=project_id,
            diff_content=diff_content,
        )

        # Save review results
        review.status = "completed"
        review.completed_at = datetime.now(timezone.utc)
        review.summary = {
            "total_issues": len(review_result.comments),
            "severity_counts": {
                "critical": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.CRITICAL),
                "high": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.HIGH),
                "medium": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.MEDIUM),
                "low": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.LOW),
                "info": sum(1 for c in review_result.comments if c.severity == ReviewSeverity.INFO),
            },
        }

        # Save individual comments
        for comment in review_result.comments:
            db_comment = ReviewComment(
                review_id=review.id,
                file_path=comment.file_path,
                line_number=comment.line,
                message=comment.message,
                severity=comment.severity.value,
                category=comment.category.value if hasattr(comment, "category") else None,
                rule_id=comment.rule_id,
                rule_name=comment.rule_name,
                suggested_fix=comment.suggested_fix,
            )
            db.add(db_comment)

        await db.commit()

    except Exception as e:
        logger.error(f"Error running code review: {str(e)}", exc_info=True)
        review.status = "failed"
        review.error = str(e)
        await db.commit()

    return review


async def run_architecture_analysis(pr_id: str, project_id: str, db: AsyncSession) -> ArchitectureAnalysis:
    """Run architectural analysis on the codebase"""
    # Create a new analysis record
    analysis = ArchitectureAnalysis(pull_request_id=pr_id, status="in_progress", started_at=datetime.now(timezone.utc))
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
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.summary = {
            "total_violations": len(report.violations),
            "severity_counts": {
                "critical": sum(1 for v in report.violations if v.severity == "critical"),
                "high": sum(1 for v in report.violations if v.severity == "high"),
                "medium": sum(1 for v in report.violations if v.severity == "medium"),
                "low": sum(1 for v in report.violations if v.severity == "low"),
            },
            "metrics": [{"name": m.name, "value": m.value} for m in report.metrics],
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
                rule_name=violation.rule_name,
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
    x_hub_signature_256: str | None = Header(None),
    x_github_delivery: str | None = Header(None),
    x_github_event: str | None = Header(None),
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
    repo_full_name = payload.get("repository", {}).get("full_name")
    if not repo_full_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing repository information")

    # Find project by repository URL
    repo_url = f"https://github.com/{repo_full_name}"
    stmt = select(Project).where(Project.github_repo_url == repo_url)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Project not found for repository: {repo_full_name}"
        )

    # Verify webhook signature
    if project.github_webhook_secret:
        webhook_secret = decrypt_if_possible(project.github_webhook_secret) or project.github_webhook_secret
        github_client = get_github_client()
        if not github_client.verify_webhook_signature(body, x_hub_signature_256 or "", webhook_secret):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    # Handle different event types
    event_type = x_github_event

    if event_type == "ping":
        return {"message": "pong"}

    elif event_type == "pull_request":
        # Get repository information
        repo_name = payload.get("repository", {}).get("full_name")
        if not repo_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Repository information not found in payload"
            )

        # Find project by repository name
        stmt = select(Project).where(Project.github_repo == repo_name)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with repository {repo_name} not found"
            )

        # Handle PR event in the background
        background_tasks.add_task(process_pull_request_event, payload=payload, project=project, db=db)

        return {"message": "PR processing started in the background"}

    return {"message": f"Unhandled event type: {event_type}"}


async def handle_pull_request_event(payload: dict[str, Any], project: Project, db: AsyncSession) -> dict[str, str]:
    """Handle pull request webhook event"""
    action = payload.get("action")
    pr_data = payload.get("pull_request", {})

    pr_number = pr_data.get("number")
    if not pr_number:
        return {"message": "Invalid PR data"}

    # Check if PR already exists
    stmt = select(PullRequest).where(PullRequest.project_id == project.id, PullRequest.github_pr_number == pr_number)
    result = await db.execute(stmt)
    existing_pr = result.scalar_one_or_none()

    if action == "opened":
        if existing_pr:
            return {"message": "PR already exists"}

        # Create new PR
        pr = PullRequest(
            project_id=project.id,
            github_pr_number=pr_number,
            title=pr_data.get("title"),
            description=pr_data.get("body"),
            branch_name=pr_data.get("head", {}).get("ref"),
            commit_sha=pr_data.get("head", {}).get("sha"),
            files_changed=pr_data.get("changed_files", 0),
            lines_added=pr_data.get("additions", 0),
            lines_deleted=pr_data.get("deletions", 0),
            status=PRStatus.PENDING,
        )

        db.add(pr)
        await db.commit()
        await db.refresh(pr)

        # Queue analysis task
        await _enqueue_pr_analysis(
            str(pr.id),
            project_id=str(project.id),
            pr_number=pr_number,
            commit_sha=pr.commit_sha,
            action="opened",
        )

        return {"message": "PR created and queued for analysis", "pr_id": str(pr.id)}

    elif action == "synchronize":
        if not existing_pr:
            return {"message": "PR not found"}

        # Update PR with new commit
        existing_pr.commit_sha = pr_data.get("head", {}).get("sha")
        existing_pr.files_changed = pr_data.get("changed_files", 0)
        existing_pr.lines_added = pr_data.get("additions", 0)
        existing_pr.lines_deleted = pr_data.get("deletions", 0)
        existing_pr.status = PRStatus.PENDING

        await db.commit()

        # Queue re-analysis
        cache = await get_cache_service()
        await cache.invalidate_analysis(str(existing_pr.id))
        await _enqueue_pr_analysis(
            str(existing_pr.id),
            project_id=str(project.id),
            pr_number=pr_number,
            commit_sha=existing_pr.commit_sha,
            action="synchronize",
        )

        return {"message": "PR updated and queued for re-analysis"}

    elif action == "closed":
        if existing_pr:
            if pr_data.get("merged"):
                existing_pr.status = PRStatus.APPROVED
            else:
                existing_pr.status = PRStatus.REJECTED

            existing_pr.reviewed_at = datetime.now(timezone.utc)
            await db.commit()

        return {"message": "PR closed"}

    return {"message": f"Action {action} received"}


@router.post("/pr/{pr_id}/analyze")
async def analyze_pull_request(
    pr_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger analysis of a pull request

    This endpoint can be used to manually trigger analysis of a pull request
    that has already been created.
    """
    pr = await _get_pull_request_or_404(pr_id, db)
    await _ensure_project_access(str(pr.project_id), current_user, db)
    await _enqueue_pr_analysis(
        pr_id,
        project_id=str(pr.project_id),
        pr_number=pr.github_pr_number,
        commit_sha=pr.commit_sha,
        action="manual_trigger",
    )

    return {"message": "Analysis queued", "pr_id": pr_id}


@router.get("/pr/{pr_id}/review")
async def get_code_review(
    pr_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Get code review results for a pull request
    """
    pr = await _get_pull_request_or_404(pr_id, db)
    await _ensure_project_access(str(pr.project_id), current_user, db)

    # Get the latest review
    stmt = select(CodeReview).where(CodeReview.pull_request_id == pr_id).order_by(CodeReview.started_at.desc()).limit(1)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    fallback_review_result = None
    if not review:
        review_result_stmt = select(ReviewResult).where(ReviewResult.pull_request_id == pr.id)
        review_result_res = await db.execute(review_result_stmt)
        fallback_review_result = review_result_res.scalar_one_or_none()

        if not fallback_review_result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No code review found for this PR")

    # Get review comments
    comments_payload: list[dict[str, Any]]
    if review:
        stmt = select(ReviewComment).where(ReviewComment.review_id == review.id)
        result = await db.execute(stmt)
        comments = result.scalars().all()
        comments_payload = [
            {
                "id": str(comment.id),
                "file_path": comment.file_path,
                "line_number": comment.line_number,
                "message": comment.message,
                "severity": comment.severity,
                "category": comment.category,
                "suggested_fix": comment.suggested_fix,
                "rule_id": comment.rule_id,
                "rule_name": comment.rule_name,
            }
            for comment in comments
        ]
    else:
        comments_payload = _build_fallback_comments_from_review_result(fallback_review_result)

    return {
        "review_id": str(review.id) if review else str(fallback_review_result.id),
        "status": review.status.value if review and hasattr(review.status, "value") else "completed",
        "started_at": review.started_at if review else pr.analyzed_at or pr.created_at,
        "completed_at": review.completed_at if review else pr.analyzed_at,
        "summary": review.summary if review else {
            "total_issues": fallback_review_result.total_issues if fallback_review_result else len(comments_payload),
            "severity_counts": {},
        },
        "comments": comments_payload,
    }


@router.post("/projects/{project_id}/sync", response_model=Message)
async def sync_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(check_project_access),
):
    """
    Manually trigger project synchronization with GitHub
    """
    project = await _get_project_by_id_or_404(project_id, db)
    github_client = _get_user_github_client(current_user)

    if not project.github_repo_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not linked to a GitHub repository.",
        )

    # Get repository info from GitHub
    repo_info = await github_client.get_repository(project.github_repo_url)
    repo_full_name = _extract_repo_full_name(project.github_repo_url)
    repository_prs = await github_client.list_repository_prs(repo_full_name, state="all", limit=50)

    # Update project info
    project.language = repo_info.get("language")
    imported_count = 0
    updated_count = 0

    for pr_summary in repository_prs:
        pr_details = await github_client.get_pull_request(repo_full_name, pr_summary["number"])

        stmt = select(PullRequest).where(
            PullRequest.project_id == project.id, PullRequest.github_pr_number == pr_details["number"]
        )
        result = await db.execute(stmt)
        existing_pr = result.scalar_one_or_none()

        status_value = _map_github_pr_state(pr_details)

        if existing_pr is None:
            existing_pr = PullRequest(
                project_id=project.id,
                author_id=current_user.id,
                github_pr_number=pr_details["number"],
                title=pr_details["title"],
                description=pr_details.get("body"),
                branch_name=pr_details.get("head", {}).get("ref"),
                commit_sha=pr_details.get("head", {}).get("sha"),
                files_changed=pr_details.get("changed_files", 0),
                lines_added=pr_details.get("additions", 0),
                lines_deleted=pr_details.get("deletions", 0),
                status=status_value,
            )
            db.add(existing_pr)
            imported_count += 1
        else:
            existing_pr.title = pr_details["title"]
            existing_pr.description = pr_details.get("body")
            existing_pr.branch_name = pr_details.get("head", {}).get("ref")
            existing_pr.commit_sha = pr_details.get("head", {}).get("sha")
            existing_pr.files_changed = pr_details.get("changed_files", 0)
            existing_pr.lines_added = pr_details.get("additions", 0)
            existing_pr.lines_deleted = pr_details.get("deletions", 0)
            existing_pr.status = status_value
            updated_count += 1

        if pr_details.get("merged"):
            existing_pr.merged_at = datetime.now(timezone.utc)
        elif pr_details.get("state") == "closed":
            existing_pr.closed_at = datetime.now(timezone.utc)

    await db.commit()

    return Message(message=f"Project synchronized successfully. Imported {imported_count} PRs and updated {updated_count}.")


@router.get("/projects/{project_id}/pulls")
async def list_project_pulls(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(check_project_access),
    state: str = "open",
):
    """
    List pull requests for a project

    - **state**: PR state (open, closed, all)
    """
    await _get_project_by_id_or_404(project_id, db)

    # Get PRs from database
    pr_stmt = select(PullRequest).where(PullRequest.project_id == project_id)

    if state != "all":
        status_map = {
            "open": [PRStatus.PENDING, PRStatus.ANALYZING, PRStatus.REVIEWED],
            "closed": [PRStatus.APPROVED, PRStatus.REJECTED],
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
                "created_at": pr.created_at.isoformat(),
                "description": pr.description,
                "branch_name": pr.branch_name,
                "commit_sha": pr.commit_sha,
                "files_changed": pr.files_changed,
                "lines_added": pr.lines_added,
                "lines_deleted": pr.lines_deleted,
                "analyzed_at": pr.analyzed_at.isoformat() if pr.analyzed_at else None,
            }
            for pr in prs
        ],
    }


@router.get("/pulls/{pr_id}/files")
async def get_pr_files(pr_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Get changed files in a pull request
    """
    pr = await _get_pull_request_or_404(pr_id, db)
    await _ensure_project_access(str(pr.project_id), current_user, db)

    # Get project to get repo name
    project_stmt = select(Project).where(Project.id == pr.project_id)
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project or not project.github_repo_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project repository not configured")

    # Extract repo full name from URL
    repo_full_name = _extract_repo_full_name(project.github_repo_url)

    # Get files from GitHub
    github_client = _get_user_github_client(current_user)
    files = await github_client.get_pr_files(repo_full_name, pr.github_pr_number)

    # Parse diffs
    parsed_files = []
    for file in files:
        file_data = {
            "filename": file["filename"],
            "status": file["status"],
            "additions": file["additions"],
            "deletions": file["deletions"],
            "changes": file["changes"],
        }

        if file.get("patch"):
            # Parse diff
            diff_parsed = DiffParser.parse_diff(file["patch"])
            if diff_parsed:
                file_data["diff"] = diff_parsed[0]

        parsed_files.append(file_data)

    return {"pr_id": pr_id, "pr_number": pr.github_pr_number, "files": parsed_files}

class GitHubConnectRequest(BaseModel):
    code: str


@router.post("/connect")
async def connect_github(
    request: GitHubConnectRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Connect user's GitHub account using OAuth code

    Exchange OAuth code for GitHub access token and store it
    """
    try:
        import httpx

        from app.core.config import settings

        logger.info("=== GitHub Connect Request ===")
        logger.info(f"User: {current_user.email}")
        logger.info(f"Code length: {len(request.code)}")
        logger.info(f"Client ID configured: {bool(settings.GITHUB_CLIENT_ID)}")
        logger.info(f"Client Secret configured: {bool(settings.GITHUB_CLIENT_SECRET)}")

        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            logger.error("GitHub OAuth credentials not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth is not configured on the server. Please contact administrator.",
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
                    "code": request.code,
                },
            )

            logger.info(f"GitHub token exchange response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:200]}")

            if response.status_code != 200:
                logger.error(f"GitHub token exchange failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for token. GitHub returned status {response.status_code}",
                )

            token_data = response.json()

            # Check for error in response
            if "error" in token_data:
                error_msg = token_data.get("error_description", token_data.get("error"))
                logger.error(f"GitHub returned error: {error_msg}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"GitHub OAuth error: {error_msg}")

            access_token = token_data.get("access_token")

            if not access_token:
                logger.error(f"No access token in response: {token_data}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from GitHub. The authorization code may have expired.",
                )

            logger.info("Successfully received GitHub access token")

            # Get GitHub user info
            logger.info("Fetching GitHub user info...")
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )

            logger.info(f"GitHub user info response status: {user_response.status_code}")

            if user_response.status_code != 200:
                logger.error(f"Failed to get GitHub user info: {user_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to get GitHub user info. Status: {user_response.status_code}",
                )

            github_user = user_response.json()
            github_username = github_user.get("login")

            logger.info(f"Successfully retrieved GitHub user: {github_username}")

            # Store GitHub token in user record
            current_user.github_token = access_token
            current_user.github_username = github_username
            await db.commit()

            logger.info(f"GitHub account connected successfully for user {current_user.email}")

            return {"message": "GitHub account connected successfully", "username": github_username}

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except httpx.TimeoutException as e:
        logger.error(f"Timeout connecting to GitHub: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Timeout connecting to GitHub. Please try again."
        )
    except httpx.RequestError as e:
        logger.error(f"Network error connecting to GitHub: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Network error connecting to GitHub: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error connecting GitHub: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


@router.get("/status")
async def get_github_status(current_user: User = Depends(get_current_user)):
    """
    Check if user's GitHub account is connected
    """
    return {"connected": bool(current_user.github_token), "username": current_user.github_username}


@router.get("/repositories")
async def get_user_repositories(current_user: User = Depends(get_current_user)):
    """
    Get user's GitHub repositories
    """
    if not current_user.github_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub account not connected")

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            # Get user's repositories
            response = await client.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"Bearer {current_user.github_token}", "Accept": "application/json"},
                params={"sort": "updated", "per_page": 100},
            )

            if response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch repositories")

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
                    "updated_at": repo["updated_at"],
                }
                for repo in repos
            ]

            return {"repositories": formatted_repos}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching repositories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch repositories")


@router.delete("/disconnect")
async def disconnect_github(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Disconnect user's GitHub account
    """
    current_user.github_token = None
    current_user.github_username = None
    await db.commit()

    return {"message": "GitHub account disconnected successfully"}


@router.post("/pr/{pr_id}/analyze")
async def trigger_pull_request_analysis(
    pr_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue AI analysis for a synchronized pull request."""
    pr = await _get_pull_request_or_404(pr_id, db)
    await _ensure_project_access(str(pr.project_id), current_user, db)

    task_info = analyze_pull_request_sync(str(pr.id), str(pr.project_id))
    return task_info
