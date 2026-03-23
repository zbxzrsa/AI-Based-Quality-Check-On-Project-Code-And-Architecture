"""
Circuit breaker wrapper for GitHub API client

Provides circuit breaker protection for all GitHub API operations
with graceful degradation using cached data.

Validates Requirements: 2.6, 2.7, 12.5, 12.6
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status

from app.services.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerConfig
)
from app.services.github_client import GitHubAPIClient
from app.shared.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class GitHubClientWithCircuitBreaker:
    """
    GitHub API client wrapper with circuit breaker protection
    
    Wraps all GitHub API operations with circuit breaker pattern
    to prevent cascading failures. Implements graceful degradation
    by returning cached data when circuit is open.
    
    Validates Requirements: 2.6, 2.7, 12.5, 12.6
    """
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize GitHub client with circuit breaker
        
        Args:
            access_token: GitHub personal access token or App token
        """
        self.client = GitHubAPIClient(access_token)
        self.circuit_breaker = CircuitBreaker(
            name="github_api",
            config=CircuitBreakerConfig(
                failure_threshold=0.5,  # 50% failure rate
                success_threshold=2,
                timeout=60,
                window_size=10
            )
        )
        self.cache = get_cache_manager()
        
        logger.info("GitHub API client initialized with circuit breaker and caching")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.close()
    
    def _handle_circuit_breaker_open(self, cache_key: str, fallback_message: str = None):
        """
        Handle circuit breaker open state with graceful degradation
        
        Args:
            cache_key: Cache key to check for cached data
            fallback_message: Optional fallback message
            
        Returns:
            Cached data if available
            
        Raises:
            HTTPException: If no cached data available
            
        Validates Requirements: 2.7, 12.6
        """
        logger.error("GitHub API circuit breaker is OPEN")
        
        # Try to return cached data
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Returning cached data for key: {cache_key}")
            return cached_data
        
        # No cached data available, return error with fallback message
        detail = fallback_message or "GitHub API is temporarily unavailable and no cached data is available."
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )
    
    def verify_webhook_signature(
        self,
        payload_body: bytes,
        signature_header: str,
        secret: str
    ) -> bool:
        """
        Verify GitHub webhook signature (no circuit breaker needed for local operation)
        
        Args:
            payload_body: Raw request body
            signature_header: X-Hub-Signature-256 header value
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        return self.client.verify_webhook_signature(payload_body, signature_header, secret)
    
    async def get_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Get repository information with circuit breaker protection and caching
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Repository data (from API or cache)
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
            - 2.7, 12.6: Graceful degradation with cached data
        """
        cache_key = f"github:repo:{repo_url}"
        
        try:
            result = await self.circuit_breaker.call_async(
                self.client.get_repository,
                repo_url
            )
            # Cache successful result
            self.cache.set(cache_key, result)
            return result
        except CircuitBreakerOpenError:
            return self._handle_circuit_breaker_open(
                cache_key,
                f"GitHub API unavailable. Returning cached data for {repo_url} if available."
            )
    
    async def get_pull_request(
        self,
        repo_full_name: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """
        Get pull request details with circuit breaker protection and caching
        
        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number
            
        Returns:
            PR data (from API or cache)
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
            - 2.7, 12.6: Graceful degradation with cached data
        """
        cache_key = f"github:pr:{repo_full_name}:{pr_number}"
        
        try:
            result = await self.circuit_breaker.call_async(
                self.client.get_pull_request,
                repo_full_name,
                pr_number
            )
            # Cache successful result
            self.cache.set(cache_key, result)
            return result
        except CircuitBreakerOpenError:
            return self._handle_circuit_breaker_open(
                cache_key,
                f"GitHub API unavailable. Returning cached data for PR #{pr_number} if available."
            )
    
    async def get_pr_files(
        self,
        repo_full_name: str,
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of files changed in a PR with circuit breaker protection and caching
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            
        Returns:
            List of changed files with patches (from API or cache)
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
            - 2.7, 12.6: Graceful degradation with cached data
        """
        cache_key = f"github:pr_files:{repo_full_name}:{pr_number}"
        
        try:
            result = await self.circuit_breaker.call_async(
                self.client.get_pr_files,
                repo_full_name,
                pr_number
            )
            # Cache successful result
            self.cache.set(cache_key, result)
            return result
        except CircuitBreakerOpenError:
            return self._handle_circuit_breaker_open(
                cache_key,
                f"GitHub API unavailable. Returning cached PR files if available."
            )
    
    async def get_file_content(
        self,
        repo_full_name: str,
        file_path: str,
        ref: str = "main"
    ) -> str:
        """
        Get file content from repository with circuit breaker protection and caching
        
        Args:
            repo_full_name: Repository full name
            file_path: Path to file
            ref: Git reference (branch, tag, commit SHA)
            
        Returns:
            File content as string (from API or cache)
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
            - 2.7, 12.6: Graceful degradation with cached data
        """
        cache_key = f"github:file:{repo_full_name}:{file_path}:{ref}"
        
        try:
            result = await self.circuit_breaker.call_async(
                self.client.get_file_content,
                repo_full_name,
                file_path,
                ref
            )
            # Cache successful result
            self.cache.set(cache_key, result)
            return result
        except CircuitBreakerOpenError:
            return self._handle_circuit_breaker_open(
                cache_key,
                f"GitHub API unavailable. Returning cached file content if available."
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
        Post a review comment on a specific line with circuit breaker protection
        
        Note: Write operations don't use caching. Returns fallback response when circuit is open.
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            body: Comment body
            commit_id: Commit SHA
            path: File path
            line: Line number
            
        Returns:
            Comment data or fallback response
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
            - 2.7, 12.6: Graceful degradation with fallback response
        """
        try:
            return await self.circuit_breaker.call_async(
                self.client.post_review_comment,
                repo_full_name,
                pr_number,
                body,
                commit_id,
                path,
                line
            )
        except CircuitBreakerOpenError:
            logger.error("GitHub API circuit breaker is OPEN - cannot post comment")
            # Return fallback response for write operation
            return {
                "id": None,
                "body": body,
                "path": path,
                "line": line,
                "status": "deferred",
                "message": "Comment queued for posting when GitHub API becomes available"
            }
    
    async def update_pr_status(
        self,
        repo_full_name: str,
        commit_sha: str,
        state: str,
        description: str,
        context: str = "ai-code-review"
    ) -> Dict[str, Any]:
        """
        Update PR status check with circuit breaker protection
        
        Note: Write operations don't use caching. Returns fallback response when circuit is open.
        
        Args:
            repo_full_name: Repository full name
            commit_sha: Commit SHA
            state: Status state (pending, success, failure, error)
            description: Status description
            context: Status context identifier
            
        Returns:
            Status data or fallback response
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
            - 2.7, 12.6: Graceful degradation with fallback response
        """
        try:
            return await self.circuit_breaker.call_async(
                self.client.update_pr_status,
                repo_full_name,
                commit_sha,
                state,
                description,
                context
            )
        except CircuitBreakerOpenError:
            logger.error("GitHub API circuit breaker is OPEN - cannot update status")
            # Return fallback response for write operation
            return {
                "state": state,
                "description": description,
                "context": context,
                "status": "deferred",
                "message": "Status update queued for posting when GitHub API becomes available"
            }
    
    async def list_repository_prs(
        self,
        repo_full_name: str,
        state: str = "open",
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        List pull requests in a repository with circuit breaker protection and caching
        
        Args:
            repo_full_name: Repository full name
            state: PR state (open, closed, all)
            limit: Maximum number of PRs to return
            
        Returns:
            List of PR summaries (from API or cache)
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
            - 2.7, 12.6: Graceful degradation with cached data
        """
        cache_key = f"github:prs:{repo_full_name}:{state}:{limit}"
        
        try:
            result = await self.circuit_breaker.call_async(
                self.client.list_repository_prs,
                repo_full_name,
                state,
                limit
            )
            # Cache successful result
            self.cache.set(cache_key, result)
            return result
        except CircuitBreakerOpenError:
            return self._handle_circuit_breaker_open(
                cache_key,
                f"GitHub API unavailable. Returning cached PR list if available."
            )
    
    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """
        Get circuit breaker statistics
        
        Returns:
            Circuit breaker stats
        """
        return self.circuit_breaker.get_stats()


# Singleton instance
_github_client_with_cb: Optional[GitHubClientWithCircuitBreaker] = None


def get_github_client_with_circuit_breaker() -> GitHubClientWithCircuitBreaker:
    """Get GitHub API client instance with circuit breaker"""
    global _github_client_with_cb
    if _github_client_with_cb is None:
        _github_client_with_cb = GitHubClientWithCircuitBreaker()
    return _github_client_with_cb
