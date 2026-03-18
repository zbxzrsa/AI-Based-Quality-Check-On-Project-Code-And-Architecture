"""
Application Layer - Repository Use Cases

Use cases for repository operations.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from app.application.base import Command, Query, UseCaseResult
from app.domain.services import IGitHubService, ICacheService
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AddRepositoryCommand:
    """Command to add a new repository"""
    repository_url: str
    branch: Optional[str] = None
    description: Optional[str] = None
    auto_update: bool = False


@dataclass
class GetRepositoryQuery:
    """Query to get repository information"""
    repo_full_name: str


class AddRepositoryUseCase(Command):
    """
    Use case for adding a new repository.
    
    Demonstrates:
    - Command pattern (write operation)
    - Dependency injection
    - Orchestration of multiple services
    - Error handling
    """
    
    def __init__(
        self,
        github_service: IGitHubService,
        cache_service: ICacheService,
    ):
        """
        Initialize with dependency injection.
        
        Args:
            github_service: GitHub service for repository operations
            cache_service: Cache service for caching
        """
        self.github = github_service
        self.cache = cache_service
    
    async def execute(self, command: AddRepositoryCommand) -> UseCaseResult:
        """
        Execute repository addition.
        
        Steps:
        1. Validate repository URL
        2. Check if repository exists
        3. Fetch repository details
        4. Cache repository info
        5. Return result
        """
        try:
            # Step 1: Validate URL
            repo_info = self.github.get_repository(command.repository_url)
            repo_full_name = f"{repo_info['owner']['login']}/{repo_info['name']}"
            
            # Step 2: Check if exists
            cache_key = f"repo:{repo_full_name}"
            cached = await self.cache.get(cache_key)
            if cached:
                return UseCaseResult.ok({"source": "cache", "repo": cached})
            
            # Step 3: Build repository data
            repo_data = {
                "full_name": repo_full_name,
                "name": repo_info["name"],
                "owner": repo_info["owner"]["login"],
                "description": repo_info.get("description"),
                "default_branch": repo_info.get("default_branch", "main"),
                "url": repo_info["html_url"],
                "stars": repo_info.get("stargazers_count", 0),
                "language": repo_info.get("language"),
            }
            
            # Step 4: Cache repository info
            await self.cache.set(cache_key, str(repo_data), ttl=3600)
            
            logger.info(f"Repository added: {repo_full_name}")
            
            return UseCaseResult.ok({
                "source": "fresh",
                "repo": repo_data,
            })
            
        except ValueError as e:
            return UseCaseResult.err(str(e))
        except Exception as e:
            logger.error(f"Failed to add repository: {e}")
            return UseCaseResult.err(f"Failed to add repository: {e}")


class GetRepositoryUseCase(Query):
    """
    Use case for retrieving repository information.
    
    Demonstrates:
    - Query pattern (read operation)
    - Caching strategy
    - Error handling
    """
    
    def __init__(
        self,
        github_service: IGitHubService,
        cache_service: ICacheService,
    ):
        self.github = github_service
        self.cache = cache_service
    
    async def execute(self, query: GetRepositoryQuery) -> UseCaseResult:
        """Execute repository retrieval"""
        try:
            cache_key = f"repo:{query.repo_full_name}"
            
            # Check cache first
            cached = await self.cache.get(cache_key)
            if cached:
                return UseCaseResult.ok({"source": "cache", "repo": cached})
            
            # Fetch from GitHub
            repo_data = await self.github.get_repository(query.repo_full_name)
            
            # Transform to simplified format
            repo = {
                "full_name": repo_data.get("full_name"),
                "name": repo_data.get("name"),
                "owner": repo_data.get("owner", {}).get("login"),
                "description": repo_data.get("description"),
                "default_branch": repo_data.get("default_branch"),
                "url": repo_data.get("html_url"),
            }
            
            # Cache result
            await self.cache.set(cache_key, str(repo), ttl=1800)
            
            return UseCaseResult.ok({
                "source": "api",
                "repo": repo,
            })
            
        except Exception as e:
            logger.error(f"Failed to get repository: {e}")
            return UseCaseResult.err(str(e))


class SearchRepositoriesUseCase(Query):
    """Use case for searching repositories"""
    
    def __init__(
        self,
        github_service: IGitHubService,
        cache_service: ICacheService,
    ):
        self.github = github_service
        self.cache = cache_service
    
    async def execute(self, query: str) -> UseCaseResult:
        """Execute repository search"""
        try:
            cache_key = f"search:{query}"
            
            cached = await self.cache.get(cache_key)
            if cached:
                return UseCaseResult.ok({"source": "cache", "repos": cached})
            
            # Search would require additional implementation
            # For now, return empty result
            return UseCaseResult.ok({
                "source": "api",
                "repos": [],
                "message": "Search not implemented",
            })
            
        except Exception as e:
            return UseCaseResult.err(str(e))
