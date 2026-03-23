"""
Code Review Service Webhook Handler

Handles GitHub webhook events for pull requests and queues code review analysis tasks.
Implements webhook signature validation, payload extraction, and task queuing.

Validates Requirements: 1.1
"""
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Header, HTTPException, status, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.postgresql import get_db
from app.models import Project
from app.models.code_review import PullRequest, PRStatus
from app.services.redis_cache_service import get_cache_service
from app.shared.exceptions import ValidationException

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_webhook_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str
) -> bool:
    """
    Verify GitHub webhook signature using HMAC SHA-256.
    
    Args:
        payload_body: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value
        secret: Webhook secret configured in GitHub
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        return False
    
    # GitHub signature format: "sha256=<signature>"
    if not signature_header.startswith("sha256="):
        return False
    
    expected_signature = signature_header[7:]  # Remove "sha256=" prefix
    
    # Compute HMAC SHA-256
    mac = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    computed_signature = mac.hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_signature, expected_signature)


async def extract_pr_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant PR data from webhook payload.
    
    Args:
        payload: GitHub webhook payload
        
    Returns:
        Dictionary containing extracted PR data
        
    Raises:
        ValidationException: If required fields are missing
    """
    pr_data = payload.get('pull_request')
    if not pr_data:
        raise ValidationException(
            message="Missing pull_request data in payload",
            field="pull_request"
        )
    
    repository = payload.get('repository', {})
    
    return {
        'pr_number': pr_data.get('number'),
        'title': pr_data.get('title'),
        'description': pr_data.get('body') or '',  # Handle None values
        'branch_name': pr_data.get('head', {}).get('ref'),
        'commit_sha': pr_data.get('head', {}).get('sha'),
        'files_changed': pr_data.get('changed_files', 0),
        'lines_added': pr_data.get('additions', 0),
        'lines_deleted': pr_data.get('deletions', 0),
        'repository_url': repository.get('html_url'),
        'repository_full_name': repository.get('full_name'),
        'action': payload.get('action'),
        'sender': payload.get('sender', {}).get('login')
    }


async def queue_analysis_task(
    pr_id: str,
    project_id: str,
    pr_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Queue PR analysis task in Celery with priority.
    
    Args:
        pr_id: Pull request database ID
        project_id: Project database ID
        pr_data: Extracted PR data
        
    Returns:
        Task information including task_id
    """
    from app.tasks.pull_request_analysis import analyze_pull_request
    
    # Queue task with high priority for PR events
    task = analyze_pull_request.apply_async(
        args=[pr_id, project_id],
        queue='high_priority',
        priority=9,  # High priority (0-9 scale)
        expires=3600  # 1 hour expiration
    )
    
    logger.info(
        f"Queued analysis task for PR {pr_data.get('pr_number')}",
        extra={
            'task_id': task.id,
            'pr_id': pr_id,
            'project_id': project_id,
            'pr_number': pr_data.get('pr_number')
        }
    )
    
    return {
        'task_id': task.id,
        'status': 'queued',
        'pr_id': pr_id,
        'pr_number': pr_data.get('pr_number')
    }


@router.post("/webhook")
async def code_review_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    db: AsyncSession = Depends(get_db)
):
    """
    GitHub webhook endpoint for pull request events.
    
    Receives GitHub webhook events, validates signatures, extracts PR data,
    and queues analysis tasks. Implements replay protection using delivery IDs.
    
    Headers:
        X-Hub-Signature-256: HMAC SHA-256 signature for payload verification
        X-GitHub-Delivery: Unique delivery ID for replay protection
        X-GitHub-Event: Event type (e.g., "pull_request")
        
    Returns:
        200 OK for ping/unsupported/duplicate events
        202 Accepted for queued analysis tasks
        
    Validates Requirements: 1.1
    """
    start_time = datetime.now(timezone.utc)
    
    # Read raw body for signature verification
    body = await request.body()
    
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Log webhook receipt
    logger.info(
        f"Received GitHub webhook: {x_github_event}",
        extra={
            'event_type': x_github_event,
            'delivery_id': x_github_delivery,
            'action': payload.get('action')
        }
    )
    
    # Handle ping event
    if x_github_event == 'ping':
        logger.info("Received ping event from GitHub")
        return {
            'message': 'pong',
            'timestamp': start_time.isoformat()
        }
    
    # Only handle pull_request events
    if x_github_event != 'pull_request':
        logger.warning(f"Unsupported event type: {x_github_event}")
        return {
            'message': f'Event type {x_github_event} not supported',
            'supported_events': ['pull_request']
        }
    
    # Check for replay protection and concurrent duplicates using atomic SET NX
    if x_github_delivery:
        cache = await get_cache_service()
        
        # Atomically check and mark as processed
        is_new = await cache.mark_webhook_processed(x_github_delivery)
        if not is_new:
            logger.warning(
                f"Duplicate webhook delivery detected: {x_github_delivery}",
                extra={'delivery_id': x_github_delivery}
            )
            return {
                'message': 'Webhook already processed',
                'delivery_id': x_github_delivery
            }
    
    # Extract PR data
    try:
        pr_data = await extract_pr_data(payload)
    except ValidationException as e:
        logger.error(f"Failed to extract PR data: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    
    # Only process relevant actions
    action = pr_data.get('action')
    if action not in ['opened', 'synchronize', 'reopened']:
        logger.info(f"Ignoring PR action: {action}")
        return {
            'message': f'Action {action} does not trigger analysis',
            'supported_actions': ['opened', 'synchronize', 'reopened']
        }
    
    # Find project by repository URL
    repo_url = pr_data.get('repository_url')
    project_stmt = select(Project).where(Project.github_repo_url == repo_url)
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()
    
    if not project:
        logger.warning(
            f"No project found for repository: {repo_url}",
            extra={'repository_url': repo_url}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found for repository: {pr_data.get('repository_full_name')}"
        )
    
    # Verify webhook signature if secret is configured
    if project.github_webhook_secret:
        if not x_hub_signature_256:
            logger.error("Missing webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature"
            )
        
        if not verify_webhook_signature(
            body,
            x_hub_signature_256,
            project.github_webhook_secret
        ):
            logger.error(
                "Invalid webhook signature",
                extra={'project_id': str(project.id)}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    
    # Get or create PR record
    pr_number = pr_data.get('pr_number')
    pr_stmt = select(PullRequest).where(
        PullRequest.project_id == project.id,
        PullRequest.github_pr_number == pr_number
    )
    pr_result = await db.execute(pr_stmt)
    pr = pr_result.scalar_one_or_none()
    
    if not pr:
        # Create new PR record
        pr = PullRequest(
            project_id=project.id,
            github_pr_number=pr_number,
            title=pr_data.get('title'),
            description=pr_data.get('description'),
            branch_name=pr_data.get('branch_name'),
            commit_sha=pr_data.get('commit_sha'),
            files_changed=pr_data.get('files_changed', 0),
            lines_added=pr_data.get('lines_added', 0),
            lines_deleted=pr_data.get('lines_deleted', 0),
            status=PRStatus.PENDING
        )
        db.add(pr)
        await db.commit()
        await db.refresh(pr)
        
        logger.info(
            f"Created new PR record: {pr_number}",
            extra={
                'pr_id': str(pr.id),
                'pr_number': pr_number,
                'project_id': str(project.id)
            }
        )
    else:
        # Update existing PR
        pr.title = pr_data.get('title', pr.title)
        pr.description = pr_data.get('description', pr.description)
        pr.commit_sha = pr_data.get('commit_sha', pr.commit_sha)
        pr.files_changed = pr_data.get('files_changed', pr.files_changed)
        pr.lines_added = pr_data.get('lines_added', pr.lines_added)
        pr.lines_deleted = pr_data.get('lines_deleted', pr.lines_deleted)
        pr.status = PRStatus.PENDING
        pr.updated_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(
            f"Updated PR record: {pr_number}",
            extra={
                'pr_id': str(pr.id),
                'pr_number': pr_number,
                'action': action
            }
        )
    
    # Queue analysis task
    task_info = await queue_analysis_task(
        str(pr.id),
        str(project.id),
        pr_data
    )
    
    # Calculate processing time
    processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    logger.info(
        f"Webhook processed successfully in {processing_time:.3f}s",
        extra={
            'pr_id': str(pr.id),
            'processing_time_seconds': processing_time,
            'task_id': task_info.get('task_id')
        }
    )
    
    # Return 202 Accepted for async processing
    return JSONResponse(
        status_code=202,
        content={
            'message': 'PR analysis queued',
            'pr_id': str(pr.id),
            'pr_number': pr_number,
            'task_id': task_info.get('task_id'),
            'status': 'queued',
            'processing_time_seconds': processing_time
        }
    )
