"""
Infrastructure - GitHub Service Implementation

GitHub API interaction implementation using dependency inversion.
"""
from typing import List, Optional, Dict, Any
import aiohttp
from abc import ABC

from app.domain.services import IGitHubService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GitHubService(IGitHubService):
    """
    GitHub API service implementation.
    
    This implementation follows DIP by implementing the IGitHubService interface.
    The business logic depends on the abstraction (IGitHubService), not this concrete class.
    """
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        self.api_base = "https://api.github.com"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Get repository information from GitHub.
        
        Extracts owner/name from URL and fetches from GitHub API.
        """
        # Parse owner and repo from URL
        parts = repo_url.replace("https://github.com/", "").replace(".git", "").split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        
        owner, repo = parts[0], parts[1]
        
        session = await self._get_session()
        url = f"{self.api_base}/repos/{owner}/{repo}"
        
        async with session.get(url, headers=await self._get_headers()) as response:
            if response.status == 404:
                raise ValueError(f"Repository not found: {owner}/{repo}")
            if response.status == 403:
                raise ValueError("Access denied. Check GitHub token permissions.")
            if response.status != 200:
                raise ValueError(f"GitHub API error: {response.status}")
            
            return await response.json()
    
    async def get_pull_request(
        self,
        repo_full_name: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Get pull request details"""
        session = await self._get_session()
        url = f"{self.api_base}/repos/{repo_full_name}/pulls/{pr_number}"
        
        async with session.get(url, headers=await self._get_headers()) as response:
            if response.status != 200:
                raise ValueError(f"Failed to get PR: {response.status}")
            return await response.json()
    
    async def get_pull_request_files(
        self,
        repo_full_name: str,
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """Get files changed in a pull request"""
        session = await self._get_session()
        url = f"{self.api_base}/repos/{repo_full_name}/pulls/{pr_number}/files"
        
        async with session.get(url, headers=await self._get_headers()) as response:
            if response.status != 200:
                raise ValueError(f"Failed to get PR files: {response.status}")
            return await response.json()
    
    async def post_pull_request_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
        commit_id: Optional[str] = None,
        path: Optional[str] = None,
        line: Optional[int] = None
    ) -> Dict[str, Any]:
        """Post a comment to a pull request"""
        session = await self._get_session()
        
        # Determine comment type (line comment vs PR comment)
        if path and line:
            # Line comment (review comment)
            url = f"{self.api_base}/repos/{repo_full_name}/pulls/{pr_number}/comments"
            data = {
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
            }
        else:
            # PR comment
            url = f"{self.api_base}/repos/{repo_full_name}/issues/{pr_number}/comments"
            data = {"body": body}
        
        async with session.post(url, json=data, headers=await self._get_headers()) as response:
            if response.status not in (200, 201):
                raise ValueError(f"Failed to post comment: {response.status}")
            return await response.json()
    
    async def create_webhook(
        self,
        repo_full_name: str,
        webhook_url: str,
        webhook_secret: str,
        events: List[str]
    ) -> Dict[str, Any]:
        """Create a webhook for the repository"""
        session = await self._get_session()
        url = f"{self.api_base}/repos/{repo_full_name}/hooks"
        
        data = {
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": webhook_secret,
            },
            "events": events,
            "active": True,
        }
        
        async with session.post(url, json=data, headers=await self._get_headers()) as response:
            if response.status != 201:
                raise ValueError(f"Failed to create webhook: {response.status}")
            return await response.json()
    
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook signature using HMAC-SHA256"""
        import hmac
        import hashlib
        
        computed_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={computed_signature}", signature)
