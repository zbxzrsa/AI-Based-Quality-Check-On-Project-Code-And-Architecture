"""
Repository management service for GitHub dependency integration
"""
import re
from typing import Optional
from datetime import datetime
from uuid import uuid4
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.repository import (
    AddRepositoryRequest,
    RepositoryInfo,
    RepositoryURLFormat,
    RepositoryValidationResult,
    RepositoryResponse,
    RepositoryStatus,
    DependencyInfo
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RepositoryService:
    """Service for managing GitHub repository dependencies"""

    def __init__(self, db: AsyncSession, github_token: Optional[str] = None):
        self.db = db
        self.github_token = github_token or settings.GITHUB_TOKEN
        self.github_api_base = "https://api.github.com"

    def parse_repository_url(self, url: str) -> RepositoryInfo:
        """
        Parse GitHub repository URL and extract information
        
        Args:
            url: GitHub repository URL (HTTPS or SSH format)
            
        Returns:
            RepositoryInfo with parsed details
            
        Raises:
            ValueError: If URL format is invalid
        """
        # HTTPS format: https://github.com/{owner}/{repo}.git
        https_match = re.match(
            r'^https://github\.com/([\w\-\.]+)/([\w\-\.]+?)(?:\.git)?$',
            url
        )
        
        # SSH format: git@github.com:{owner}/{repo}.git
        ssh_match = re.match(
            r'^git@github\.com:([\w\-\.]+)/([\w\-\.]+?)(?:\.git)?$',
            url
        )
        
        if https_match:
            owner, name = https_match.groups()
            url_format = RepositoryURLFormat.HTTPS
            clone_url = f"https://github.com/{owner}/{name}.git"
        elif ssh_match:
            owner, name = ssh_match.groups()
            url_format = RepositoryURLFormat.SSH
            clone_url = f"git@github.com:{owner}/{name}.git"
        else:
            raise ValueError("Invalid GitHub repository URL format")
        
        return RepositoryInfo(
            owner=owner,
            name=name,
            url_format=url_format,
            full_url=url,
            clone_url=clone_url
        )

    async def validate_repository(
        self,
        repo_info: RepositoryInfo,
        branch: Optional[str] = None
    ) -> RepositoryValidationResult:
        """
        Validate repository accessibility and existence
        
        Args:
            repo_info: Parsed repository information
            branch: Optional branch to validate
            
        Returns:
            RepositoryValidationResult with validation details
        """
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        headers["Accept"] = "application/vnd.github.v3+json"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check repository existence
                repo_url = f"{self.github_api_base}/repos/{repo_info.owner}/{repo_info.name}"
                
                async with session.get(repo_url, headers=headers) as response:
                    if response.status == 404:
                        return RepositoryValidationResult(
                            is_valid=False,
                            is_accessible=False,
                            exists=False,
                            error_message="Repository not found"
                        )
                    elif response.status == 403:
                        return RepositoryValidationResult(
                            is_valid=False,
                            is_accessible=False,
                            exists=True,
                            error_message="Access denied. Check GitHub token permissions."
                        )
                    elif response.status != 200:
                        return RepositoryValidationResult(
                            is_valid=False,
                            is_accessible=False,
                            exists=False,
                            error_message=f"GitHub API error: {response.status}"
                        )
                    
                    repo_data = await response.json()
                    default_branch = repo_data.get("default_branch", "main")
                
                # Get branches
                branches_url = f"{self.github_api_base}/repos/{repo_info.owner}/{repo_info.name}/branches"
                async with session.get(branches_url, headers=headers) as response:
                    branches = []
                    if response.status == 200:
                        branches_data = await response.json()
                        branches = [b["name"] for b in branches_data]
                
                # Get tags
                tags_url = f"{self.github_api_base}/repos/{repo_info.owner}/{repo_info.name}/tags"
                async with session.get(tags_url, headers=headers) as response:
                    tags = []
                    if response.status == 200:
                        tags_data = await response.json()
                        tags = [t["name"] for t in tags_data[:50]]  # Limit to 50 tags
                
                # Validate specific branch if provided
                if branch and branch not in branches:
                    return RepositoryValidationResult(
                        is_valid=False,
                        is_accessible=True,
                        exists=True,
                        default_branch=default_branch,
                        available_branches=branches,
                        available_tags=tags,
                        error_message=f"Branch '{branch}' not found"
                    )
                
                return RepositoryValidationResult(
                    is_valid=True,
                    is_accessible=True,
                    exists=True,
                    default_branch=default_branch,
                    available_branches=branches,
                    available_tags=tags
                )
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error validating repository: {e}")
            return RepositoryValidationResult(
                is_valid=False,
                is_accessible=False,
                exists=False,
                error_message=f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error validating repository: {e}")
            return RepositoryValidationResult(
                is_valid=False,
                is_accessible=False,
                exists=False,
                error_message=f"Validation error: {str(e)}"
            )

    async def fetch_dependencies(
        self,
        repo_info: RepositoryInfo,
        branch: str = "main"
    ) -> Optional[DependencyInfo]:
        """
        Fetch and parse dependencies from repository
        
        Args:
            repo_info: Repository information
            branch: Branch to fetch from
            
        Returns:
            DependencyInfo if dependencies found, None otherwise
        """
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        headers["Accept"] = "application/vnd.github.v3+json"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Try to fetch package.json (Node.js)
                package_json_url = (
                    f"{self.github_api_base}/repos/{repo_info.owner}/{repo_info.name}"
                    f"/contents/package.json?ref={branch}"
                )
                
                async with session.get(package_json_url, headers=headers) as response:
                    if response.status == 200:
                        content_data = await response.json()
                        # Content is base64 encoded
                        import base64
                        import json
                        
                        content = base64.b64decode(content_data["content"]).decode("utf-8")
                        package_data = json.loads(content)
                        
                        return DependencyInfo(
                            package_manager="npm",
                            dependencies=package_data.get("dependencies", {}),
                            dev_dependencies=package_data.get("devDependencies", {}),
                            peer_dependencies=package_data.get("peerDependencies", {})
                        )
                
                # Try to fetch requirements.txt (Python)
                requirements_url = (
                    f"{self.github_api_base}/repos/{repo_info.owner}/{repo_info.name}"
                    f"/contents/requirements.txt?ref={branch}"
                )
                
                async with session.get(requirements_url, headers=headers) as response:
                    if response.status == 200:
                        content_data = await response.json()
                        import base64
                        
                        content = base64.b64decode(content_data["content"]).decode("utf-8")
                        dependencies = {}
                        for line in content.split("\n"):
                            line = line.strip()
                            if line and not line.startswith("#"):
                                # Parse requirement (simple version)
                                if "==" in line:
                                    pkg, ver = line.split("==", 1)
                                    dependencies[pkg.strip()] = ver.strip()
                                else:
                                    dependencies[line] = "*"
                        
                        return DependencyInfo(
                            package_manager="pip",
                            dependencies=dependencies,
                            dev_dependencies={},
                            peer_dependencies={}
                        )
                
                logger.info(f"No dependency files found in {repo_info.owner}/{repo_info.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching dependencies: {e}")
            return None

    async def add_repository(
        self,
        request: AddRepositoryRequest,
        user_id: str
    ) -> RepositoryResponse:
        """
        Add a new repository dependency
        
        Args:
            request: Repository addition request
            user_id: ID of user adding the repository
            
        Returns:
            RepositoryResponse with created repository details
            
        Raises:
            ValueError: If repository is invalid or inaccessible
        """
        # Parse URL
        repo_info = self.parse_repository_url(request.repository_url)
        
        # Validate repository
        validation = await self.validate_repository(repo_info, request.branch)
        
        if not validation.is_valid:
            raise ValueError(validation.error_message or "Repository validation failed")
        
        # Use default branch if not specified
        branch = request.branch or validation.default_branch or "main"
        
        # Create repository record (simplified - you'll need to create the model)
        repo_id = str(uuid4())
        now = datetime.utcnow()
        
        # Fetch dependencies
        dependencies = await self.fetch_dependencies(repo_info, branch)
        
        metadata = {
            "url_format": repo_info.url_format.value,
            "clone_url": repo_info.clone_url,
            "default_branch": validation.default_branch,
            "available_branches": validation.available_branches[:10],  # Limit stored branches
            "available_tags": validation.available_tags[:10],  # Limit stored tags
            "added_by": user_id
        }
        
        if dependencies:
            metadata["dependencies"] = {
                "package_manager": dependencies.package_manager,
                "count": len(dependencies.dependencies)
            }
        
        logger.info(
            f"Repository added: {repo_info.owner}/{repo_info.name} "
            f"(branch: {branch}, user: {user_id})"
        )
        
        return RepositoryResponse(
            id=repo_id,
            repository_url=request.repository_url,
            owner=repo_info.owner,
            name=repo_info.name,
            branch=branch,
            version=request.version,
            status=RepositoryStatus.ACTIVE,
            description=request.description,
            auto_update=request.auto_update,
            last_synced=now,
            created_at=now,
            updated_at=now,
            metadata=metadata
        )
