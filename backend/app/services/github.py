"""
GitHub API service for interacting with GitHub's API
"""
from typing import Optional, Dict, Any, List
import aiohttp
from urllib.parse import urljoin
from app.core.config import settings

class GitHubService:
    """Service for interacting with GitHub's API"""
    
    def __init__(self, access_token: Optional[str] = None, api_url: str = "https://api.github.com"):
        """
        Initialize the GitHub service
        
        Args:
            access_token: GitHub personal access token
            api_url: Base URL for GitHub API (can be overridden for GitHub Enterprise)
        """
        self.base_url = api_url
        self.headers = {
            "Accept": "application/vnd.github.v3.diff",
            "Authorization": f"token {access_token or settings.GITHUB_ACCESS_TOKEN}",
            "User-Agent": "AI-Code-Review-System"
        }
    
    async def get_pull_request_diff(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        media_type: str = "diff"
    ) -> Optional[str]:
        """
        Get the diff for a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number
            media_type: Response format ('diff' or 'patch')
            
        Returns:
            The diff as a string, or None if not found
        """
        url = f"/repos/{owner}/{repo}/pulls/{pull_number}"
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(
                    urljoin(self.base_url, url),
                    headers={"Accept": f"application/vnd.github.v3.{media_type}"}
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        error = await response.text()
                        print(f"Error getting PR diff: {response.status} - {error}")
                        return None
        except Exception as e:
            print(f"Exception when fetching PR diff: {str(e)}")
            return None
    
    async def get_pull_request_files(
        self,
        owner: str,
        repo: str,
        pull_number: int
    ) -> List[Dict[str, Any]]:
        """
        Get the list of files changed in a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number
            
        Returns:
            List of file change objects
        """
        url = f"/repos/{owner}/{repo}/pulls/{pull_number}/files"
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(urljoin(self.base_url, url)) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error = await response.text()
                        print(f"Error getting PR files: {response.status} - {error}")
                        return []
        except Exception as e:
            print(f"Exception when fetching PR files: {str(e)}")
            return []
    
    async def get_repository_content(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the contents of a file or directory in a repository
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Path to file or directory
            ref: Git reference (branch, tag, or commit SHA)
            
        Returns:
            Dictionary containing the file/directory contents or None if not found
        """
        url = f"/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref
            
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(
                    urljoin(self.base_url, url),
                    params=params
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error = await response.text()
                        print(f"Error getting repository content: {response.status} - {error}")
                        return None
        except Exception as e:
            print(f"Exception when fetching repository content: {str(e)}")
            return None
