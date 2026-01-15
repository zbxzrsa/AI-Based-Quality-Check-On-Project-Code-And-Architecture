"""
GitHub API client wrapper
Handles GitHub REST API interactions
"""
import hmac
import hashlib
from typing import Optional, Dict, Any, List
import httpx
from github import Github, GithubException
from fastapi import HTTPException, status

from app.core.config import settings


class GitHubAPIClient:
    """
    GitHub API client for repository and PR operations
    """
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize GitHub client
        
        Args:
            access_token: GitHub personal access token or App token
        """
        self.token = access_token or settings.GITHUB_TOKEN
        self.client = Github(self.token) if self.token else None
        self.http_client = httpx.AsyncClient()
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
    
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
    
    async def get_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Get repository information
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Repository data
        """
        try:
            # Extract owner/repo from URL
            parts = repo_url.rstrip('/').split('/')
            owner, repo_name = parts[-2], parts[-1]
            
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GitHub API error: {e.data.get('message', str(e))}"
            )
    
    async def get_pull_request(
        self,
        repo_full_name: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """
        Get pull request details
        
        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number
            
        Returns:
            PR data
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pull request not found: {e.data.get('message', str(e))}"
            )
    
    async def get_pr_files(
        self,
        repo_full_name: str,
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of files changed in a PR
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            
        Returns:
            List of changed files with patches
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not fetch PR files: {e.data.get('message', str(e))}"
            )
    
    async def get_file_content(
        self,
        repo_full_name: str,
        file_path: str,
        ref: str = "main"
    ) -> str:
        """
        Get file content from repository
        
        Args:
            repo_full_name: Repository full name
            file_path: Path to file
            ref: Git reference (branch, tag, commit SHA)
            
        Returns:
            File content as string
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {e.data.get('message', str(e))}"
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
        Post a review comment on a specific line
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            body: Comment body
            commit_id: Commit SHA
            path: File path
            line: Line number
            
        Returns:
            Comment data
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
            
            return {
                "id": comment.id,
                "body": comment.body,
                "path": comment.path,
                "line": comment.line,
                "created_at": comment.created_at.isoformat()
            }
        except GithubException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not post comment: {e.data.get('message', str(e))}"
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
        Update PR status check
        
        Args:
            repo_full_name: Repository full name
            commit_sha: Commit SHA
            state: Status state (pending, success, failure, error)
            description: Status description
            context: Status context identifier
            
        Returns:
            Status data
        """
        try:
            repo = self.client.get_repo(repo_full_name)
            commit = repo.get_commit(commit_sha)
            
            status = commit.create_status(
                state=state,
                description=description,
                context=context
            )
            
            return {
                "state": status.state,
                "description": status.description,
                "context": status.context,
                "created_at": status.created_at.isoformat()
            }
        except GithubException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not update status: {e.data.get('message', str(e))}"
            )
    
    async def list_repository_prs(
        self,
        repo_full_name: str,
        state: str = "open",
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        List pull requests in a repository
        
        Args:
            repo_full_name: Repository full name
            state: PR state (open, closed, all)
            limit: Maximum number of PRs to return
            
        Returns:
            List of PR summaries
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
