"""
GitHub API client wrapper
Handles GitHub REST API interactions

This module implements the GitHub API client with:
- Authentication using GitHub App tokens
- Methods to fetch PR files and diffs
- Method to post review comments
- Retry logic with exponential backoff
- Circuit breaker pattern for resilience

Requirements:
- 1.5: Post review comments to pull requests
- 2.2: Implement exponential backoff with maximum of 3 retry attempts
- 2.6: Circuit breaker pattern for external service calls
- 12.5: Circuit breaker pattern for external service calls
"""
import hmac
import hashlib
from typing import Optional, Dict, Any, List
import logging
import httpx
from github import Github, GithubException
from fastapi import HTTPException, status
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.core.config import settings
from app.services.llm.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitBreakerConfig

logger = logging.getLogger(__name__)


class GitHubAPIClient:
    """
    GitHub API client for repository and PR operations
    
    Validates Requirements: 2.6, 12.5 (Circuit breaker pattern)
    """
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize GitHub client
        
        Args:
            access_token: GitHub personal access token or App token
        """
        self.token = access_token or settings.GITHUB_TOKEN
        # Always create client — PyGithub supports unauthenticated access for public repos
        self.client = Github(self.token) if self.token else Github()
        self.http_client = httpx.AsyncClient()
        
        # Initialize circuit breaker for GitHub API
        self.circuit_breaker = CircuitBreaker(
            name="github_api",
            config=CircuitBreakerConfig(
                failure_threshold=0.5,  # 50% failure rate
                success_threshold=2,
                timeout=60,
                window_size=10
            )
        )
        
        logger.info("GitHub API client initialized with circuit breaker")
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
    
    def _wrap_with_circuit_breaker(self, func, *args, **kwargs):
        """
        Wrap a function call with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        try:
            return self.circuit_breaker.call(func, *args, **kwargs)
        except CircuitBreakerOpenError as e:
            logger.error(f"GitHub API circuit breaker is OPEN: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GitHub API is temporarily unavailable. Please try again later."
            )
    
    def verify_webhook_signature(
        self,
        payload_body: bytes,
        signature_header: str,
        secret: str
    ) -> bool:
        """
        Verify GitHub webhook signature
        
        Args:
            payload_body: Raw request body
            signature_header: X-Hub-Signature-256 header value
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        if not signature_header:
            return False
        
        hash_object = hmac.new(
            secret.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        
        return hmac.compare_digest(expected_signature, signature_header)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GithubException, httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def get_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Get repository information with retry logic and circuit breaker
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Repository data
            
        Requirements:
            - 2.2: Retry with exponential backoff (max 3 attempts)
            - 2.6, 12.5: Circuit breaker pattern
        """
        def _get_repo():
            # Extract owner/repo from URL
            parts = repo_url.rstrip('/').split('/')
            owner, repo_name = parts[-2], parts[-1]
            
            try:
                repo = self.client.get_repo(f"{owner}/{repo_name}")
                
                return {
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "language": repo.language,
                    "default_branch": repo.default_branch,
                    "private": repo.private
                }
            except GithubException as e:
                # Log and re-raise for retry logic
                logger.error(f"GitHub API error fetching repository {repo_url}: {e}")
                # Check if this is a retryable error (5xx server errors)
                if hasattr(e, 'status') and e.status >= 500:
                    raise  # Re-raise for retry
                # For client errors (4xx), convert to HTTPException
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"GitHub API error: {e.data.get('message', str(e))}"
                )
        
        return self._wrap_with_circuit_breaker(_get_repo)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GithubException, httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def get_pull_request(
        self,
        repo_full_name: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """
        Get pull request details with retry logic
        
        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number
            
        Returns:
            PR data
            
        Requirements:
            - 1.5: Fetch PR data for analysis
            - 2.2: Retry with exponential backoff (max 3 attempts)
        """
        try:
            repo = self.client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            
            return {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "user": {
                    "login": pr.user.login,
                    "id": pr.user.id
                },
                "head": {
                    "ref": pr.head.ref,
                    "sha": pr.head.sha
                },
                "base": {
                    "ref": pr.base.ref,
                    "sha": pr.base.sha
                },
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "merged": pr.merged,
                "mergeable": pr.mergeable,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files
            }
        except GithubException as e:
            logger.error(f"GitHub API error fetching PR {repo_full_name}#{pr_number}: {e}")
            # Retry on server errors (5xx)
            if hasattr(e, 'status') and e.status >= 500:
                raise
            # Convert client errors to HTTPException
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pull request not found: {e.data.get('message', str(e))}"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GithubException, httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def get_pr_files(
        self,
        repo_full_name: str,
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of files changed in a PR with retry logic
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            
        Returns:
            List of changed files with patches
            
        Requirements:
            - 1.5: Fetch PR files and diffs for analysis
            - 2.2: Retry with exponential backoff (max 3 attempts)
        """
        try:
            repo = self.client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            files = pr.get_files()
            
            result = []
            for file in files:
                result.append({
                    "filename": file.filename,
                    "status": file.status,  # added, removed, modified, renamed
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": file.patch if hasattr(file, 'patch') else None,
                    "blob_url": file.blob_url,
                    "raw_url": file.raw_url
                })
            
            return result
        except GithubException as e:
            logger.error(f"GitHub API error fetching PR files {repo_full_name}#{pr_number}: {e}")
            # Retry on server errors (5xx)
            if hasattr(e, 'status') and e.status >= 500:
                raise
            # Convert client errors to HTTPException
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not fetch PR files: {e.data.get('message', str(e))}"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GithubException, httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def get_file_content(
        self,
        repo_full_name: str,
        file_path: str,
        ref: str = "main"
    ) -> str:
        """
        Get file content from repository with retry logic
        
        Args:
            repo_full_name: Repository full name
            file_path: Path to file
            ref: Git reference (branch, tag, commit SHA)
            
        Returns:
            File content as string
            
        Requirements:
            - 2.2: Retry with exponential backoff (max 3 attempts)
        """
        try:
            repo = self.client.get_repo(repo_full_name)
            content = repo.get_contents(file_path, ref=ref)
            
            if isinstance(content, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Path is a directory, not a file"
                )
            
            return content.decoded_content.decode('utf-8')
        except GithubException as e:
            logger.error(f"GitHub API error fetching file {file_path} from {repo_full_name}: {e}")
            # Retry on server errors (5xx)
            if hasattr(e, 'status') and e.status >= 500:
                raise
            # Convert client errors to HTTPException
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {e.data.get('message', str(e))}"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GithubException, httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def post_review_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
        commit_id: str,
        path: str,
        line: int
    ) -> Dict[str, Any]:
        """
        Post a review comment on a specific line with retry logic
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            body: Comment body
            commit_id: Commit SHA
            path: File path
            line: Line number
            
        Returns:
            Comment data
            
        Requirements:
            - 1.5: Post review comments to pull requests
            - 2.2: Retry with exponential backoff (max 3 attempts)
        """
        try:
            repo = self.client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            
            comment = pr.create_review_comment(
                body=body,
                commit_id=commit_id,
                path=path,
                line=line
            )
            
            logger.info(f"Posted review comment on {repo_full_name}#{pr_number} at {path}:{line}")
            
            return {
                "id": comment.id,
                "body": comment.body,
                "path": comment.path,
                "line": comment.line,
                "created_at": comment.created_at.isoformat()
            }
        except GithubException as e:
            logger.error(f"GitHub API error posting comment on {repo_full_name}#{pr_number}: {e}")
            # Retry on server errors (5xx)
            if hasattr(e, 'status') and e.status >= 500:
                raise
            # Convert client errors to HTTPException
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not post comment: {e.data.get('message', str(e))}"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GithubException, httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def update_pr_status(
        self,
        repo_full_name: str,
        commit_sha: str,
        state: str,
        description: str,
        context: str = "ai-code-review"
    ) -> Dict[str, Any]:
        """
        Update PR status check with retry logic
        
        Args:
            repo_full_name: Repository full name
            commit_sha: Commit SHA
            state: Status state (pending, success, failure, error)
            description: Status description
            context: Status context identifier
            
        Returns:
            Status data
            
        Requirements:
            - 2.2: Retry with exponential backoff (max 3 attempts)
        """
        try:
            repo = self.client.get_repo(repo_full_name)
            commit = repo.get_commit(commit_sha)
            
            status = commit.create_status(
                state=state,
                description=description,
                context=context
            )
            
            logger.info(f"Updated PR status for {repo_full_name}@{commit_sha[:7]}: {state}")
            
            return {
                "state": status.state,
                "description": status.description,
                "context": status.context,
                "created_at": status.created_at.isoformat()
            }
        except GithubException as e:
            logger.error(f"GitHub API error updating status for {repo_full_name}@{commit_sha}: {e}")
            # Retry on server errors (5xx)
            if hasattr(e, 'status') and e.status >= 500:
                raise
            # Convert client errors to HTTPException
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not update status: {e.data.get('message', str(e))}"
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GithubException, httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def list_repository_prs(
        self,
        repo_full_name: str,
        state: str = "open",
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        List pull requests in a repository with retry logic
        
        Args:
            repo_full_name: Repository full name
            state: PR state (open, closed, all)
            limit: Maximum number of PRs to return
            
        Returns:
            List of PR summaries
            
        Requirements:
            - 2.2: Retry with exponential backoff (max 3 attempts)
        """
        try:
            repo = self.client.get_repo(repo_full_name)
            prs = repo.get_pulls(state=state)
            
            result = []
            for i, pr in enumerate(prs):
                if i >= limit:
                    break
                
                result.append({
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "user": pr.user.login,
                    "created_at": pr.created_at.isoformat(),
                    "updated_at": pr.updated_at.isoformat()
                })
            
            return result
        except GithubException as e:
            logger.error(f"GitHub API error listing PRs for {repo_full_name}: {e}")
            # Retry on server errors (5xx)
            if hasattr(e, 'status') and e.status >= 500:
                raise
            # Convert client errors to HTTPException
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not list PRs: {e.data.get('message', str(e))}"
            )


# Singleton instance
_github_client: Optional[GitHubAPIClient] = None


def get_github_client() -> GitHubAPIClient:
    """Get GitHub API client instance"""
    global _github_client
    if _github_client is None:
        _github_client = GitHubAPIClient()
    return _github_client
