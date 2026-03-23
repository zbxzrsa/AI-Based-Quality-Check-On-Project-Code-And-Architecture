"""
GitHub webhook handler endpoint

This module implements the GitHub webhook receiver that:
- Validates webhook signatures using HMAC-SHA256
- Parses pull request events and extracts metadata
- Queues analysis tasks to Celery for async processing
- Implements replay protection using Redis

Requirements:
- 1.1: Receive GitHub webhooks within 10 seconds
- 1.5: Post review comments to pull requests
"""
import hmac
import hashlib
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgresql import get_db
from app.models import Project, PullRequest, PRStatus
from app.services.redis_cache_service import get_cache_service
from app.tasks.pull_request_analysis import analyze_pull_request_sync

logger = logging.getLogger(__name__)

router = APIRouter()




def verify_github_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str
) -> bool:
    """
    Verify GitHub webhook signature using HMAC-SHA256
    
    Args:
        payload_body: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value
        secret: Webhook secret configured in GitHub
        
    Returns:
        True if signature is valid, False otherwise
        
    Requirements:
        - 1.1: Validate webhook signatures for security
    """
    if not signature_header or not secret:
        return False
    
    # GitHub sends signature as "sha256=<hex_digest>"
    if not signature_header.startswith('sha256='):
        return False
    
    # Extract the hex digest
    received_signature = signature_header[7:]  # Remove "sha256=" prefix
    
    # Compute expected signature
    hash_object = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = hash_object.hexdigest()
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, received_signature)




async def check_replay_protection(delivery_id: str) -> bool:
    """
    Check if webhook has already been processed (replay protection)
    Uses atomic SET NX to prevent concurrent duplication
    
    Args:
        delivery_id: X-GitHub-Delivery header value
        
    Returns:
        True if webhook is new, False if already processed
    """
    if not delivery_id:
        return True  # Allow if no delivery ID (shouldn't happen with GitHub)
    
    cache = await get_cache_service()
    
    # mark_webhook_processed uses atomic SET NX (returns True if set successfully)
    return await cache.mark_webhook_processed(delivery_id)


async def extract_pr_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract pull request metadata from webhook payload
    
    Args:
        payload: GitHub webhook payload
        
    Returns:
        Dictionary with extracted PR metadata
        
    Requirements:
        - 1.1: Parse pull request events and extract metadata
    """
    pr_data = payload.get('pull_request', {})
    
    return {
        'number': pr_data.get('number'),
        'title': pr_data.get('title'),
        'description': pr_data.get('body'),
        'branch_name': pr_data.get('head', {}).get('ref'),
        'commit_sha': pr_data.get('head', {}).get('sha'),
        'files_changed': pr_data.get('changed_files', 0),
        'lines_added': pr_data.get('additions', 0),
        'lines_deleted': pr_data.get('deletions', 0),
        'author': pr_data.get('user', {}).get('login'),
        'state': pr_data.get('state'),
        'merged': pr_data.get('merged', False)
    }




async def get_or_create_pr(
    project: Project,
    pr_metadata: Dict[str, Any],
    db: AsyncSession
) -> PullRequest:
    """
    Get existing PR or create new one
    
    Args:
        project: Project model instance
        pr_metadata: Extracted PR metadata
        db: Database session
        
    Returns:
        PullRequest model instance
    """
    pr_number = pr_metadata['number']
    
    # Check if PR already exists
    stmt = select(PullRequest).where(
        PullRequest.project_id == project.id,
        PullRequest.github_pr_number == pr_number
    )
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()
    
    if pr:
        # Update existing PR
        pr.title = pr_metadata.get('title', pr.title)
        pr.description = pr_metadata.get('description', pr.description)
        pr.commit_sha = pr_metadata.get('commit_sha', pr.commit_sha)
        pr.files_changed = pr_metadata.get('files_changed', pr.files_changed)
        pr.lines_added = pr_metadata.get('lines_added', pr.lines_added)
        pr.lines_deleted = pr_metadata.get('lines_deleted', pr.lines_deleted)
        pr.status = PRStatus.PENDING
    else:
        # Create new PR
        pr = PullRequest(
            project_id=project.id,
            github_pr_number=pr_number,
            title=pr_metadata.get('title'),
            description=pr_metadata.get('description'),
            branch_name=pr_metadata.get('branch_name'),
            commit_sha=pr_metadata.get('commit_sha'),
            files_changed=pr_metadata.get('files_changed', 0),
            lines_added=pr_metadata.get('lines_added', 0),
            lines_deleted=pr_metadata.get('lines_deleted', 0),
            status=PRStatus.PENDING
        )
        db.add(pr)
    
    await db.commit()
    await db.refresh(pr)
    
    return pr




@router.post("/github")
async def github_webhook_handler(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event")
):
    """
    GitHub webhook handler endpoint
    
    Receives GitHub webhook events, validates signatures, and queues analysis tasks.
    
    Supported events:
    - ping: Webhook configuration test
    - pull_request: PR opened, synchronized, reopened, closed
    
    Requirements:
        - 1.1: Receive webhooks within 10 seconds
        - 1.5: Queue analysis tasks to Celery
        
    Returns:
        200: Webhook processed successfully
        400: Invalid payload or missing data
        401: Invalid signature
        404: Project not found
        409: Webhook already processed (replay)
    """
    # Read raw body for signature verification
    body = await request.body()
    
    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Check replay protection
    if x_github_delivery:
        is_new = await check_replay_protection(x_github_delivery)
        if not is_new:
            logger.warning(f"Duplicate webhook delivery: {x_github_delivery}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Webhook already processed"
            )
    
    # Get repository information
    repo_data = payload.get('repository', {})
    repo_full_name = repo_data.get('full_name')
    
    if not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing repository information in payload"
        )
    
    # Find project by repository URL
    repo_url = f"https://github.com/{repo_full_name}"
    stmt = select(Project).where(Project.github_repo_url == repo_url)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        logger.warning(f"Project not found for repository: {repo_full_name}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not configured for repository: {repo_full_name}"
        )
    
    # Verify webhook signature if secret is configured
    if project.github_webhook_secret:
        if not x_hub_signature_256:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature"
            )
        
        is_valid = verify_github_signature(
            body,
            x_hub_signature_256,
            project.github_webhook_secret
        )
        
        if not is_valid:
            logger.warning(f"Invalid webhook signature for project {project.id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    
    # Handle different event types
    event_type = x_github_event
    
    if event_type == 'ping':
        # Webhook configuration test
        logger.info(f"Received ping webhook for project {project.id}")
        return {
            "message": "pong",
            "project_id": str(project.id),
            "repository": repo_full_name
        }
    
    elif event_type == 'pull_request':
        # Handle pull request events
        action = payload.get('action')
        
        # Only process relevant actions
        if action not in ['opened', 'synchronize', 'reopened']:
            logger.info(f"Ignoring PR action '{action}' for project {project.id}")
            return {
                "message": f"Action '{action}' not processed",
                "action": action
            }
        
        # Extract PR metadata
        pr_metadata = await extract_pr_metadata(payload)
        
        if not pr_metadata['number']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing PR number in payload"
            )
        
        # Get or create PR record
        pr = await get_or_create_pr(project, pr_metadata, db)
        
        # Queue analysis task to Celery
        task_info = analyze_pull_request_sync(
            pr_id=str(pr.id),
            project_id=str(project.id)
        )
        
        logger.info(
            f"Queued PR analysis: project={project.id}, "
            f"pr={pr.github_pr_number}, task={task_info['task_id']}"
        )
        
        return {
            "message": "Pull request analysis queued",
            "pr_id": str(pr.id),
            "pr_number": pr.github_pr_number,
            "action": action,
            "task_id": task_info['task_id'],
            "status": task_info['status']
        }
    
    else:
        # Unsupported event type
        logger.info(f"Unsupported webhook event: {event_type}")
        return {
            "message": f"Event type '{event_type}' not supported",
            "event_type": event_type
        }
