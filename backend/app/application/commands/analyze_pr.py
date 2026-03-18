"""
Application Layer - Analyze Pull Request Command

Example of a command use case that orchestrates PR analysis.
"""

import logging
from dataclasses import dataclass

from app.application.base import Command, UseCaseResult
from app.domain.services import ICacheService, IGitHubService, ILLMService
from app.infrastructure.container import get_container

logger = logging.getLogger(__name__)


@dataclass
class AnalyzePRCommand:
    """Command to analyze a pull request"""

    repo_full_name: str
    pr_number: int
    analysis_type: str = "full"  # full, quick, security


class AnalyzePRUseCase(Command):
    """
    Use case for analyzing pull requests.

    This use case demonstrates:
    1. Dependency injection (uses interfaces, not concrete classes)
    2. Command pattern (write operation)
    3. Orchestration of multiple services
    """

    def __init__(
        self,
        github_service: IGitHubService,
        llm_service: ILLMService,
        cache_service: ICacheService,
    ):
        """
        Initialize with dependency injection.

        Dependencies are injected via constructor, following DIP.
        """
        self.github = github_service
        self.llm = llm_service
        self.cache = cache_service

    async def execute(self, command: AnalyzePRCommand) -> UseCaseResult:
        """
        Execute PR analysis.

        Steps:
        1. Check cache for previous analysis
        2. Fetch PR files from GitHub
        3. Analyze with LLM
        4. Cache results
        5. Return analysis
        """
        cache_key = f"pr_analysis:{command.repo_full_name}:{command.pr_number}"

        # 1. Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            return UseCaseResult.ok({"source": "cache", "analysis": cached})

        # 2. Fetch PR files
        try:
            pr_files = await self.github.get_pull_request_files(command.repo_full_name, command.pr_number)
        except Exception as e:
            return UseCaseResult.err(f"Failed to fetch PR files: {e}")

        if not pr_files:
            return UseCaseResult.ok({"source": "fresh", "analysis": [], "message": "No files changed"})

        # 3. Analyze each file
        analysis_results = []
        for file_data in pr_files[:10]:  # Limit to first 10 files
            try:
                analysis = await self.llm.analyze_code(
                    code=file_data.get("patch", ""),
                    language=self._detect_language(file_data.get("filename", "")),
                    analysis_type=command.analysis_type,
                    context={
                        "filename": file_data.get("filename"),
                        "status": file_data.get("status"),
                    },
                )
                analysis_results.append(
                    {
                        "filename": file_data.get("filename"),
                        "analysis": analysis,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to analyze {file_data.get('filename')}: {e}")

        # 4. Cache results
        await self.cache.set(cache_key, str(analysis_results), ttl=3600)

        return UseCaseResult.ok(
            {
                "source": "fresh",
                "analysis": analysis_results,
                "files_analyzed": len(analysis_results),
            }
        )

    def _detect_language(self, filename: str) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".c": "c",
        }

        for ext, lang in ext_map.items():
            if filename.endswith(ext):
                return lang
        return "unknown"


async def create_analyze_pr_use_case() -> AnalyzePRUseCase:
    """
    Factory function to create AnalyzePRUseCase with dependencies.

    This function resolves dependencies from the DI container.
    """
    get_container()

    # In a real implementation, these would be resolved from container
    # github = container.resolve(IGitHubService)
    # llm = container.resolve(ILLMService)
    # cache = container.resolve(ICacheService)

    # For now, create with None (would be properly injected)
    return AnalyzePRUseCase(
        github_service=None,
        llm_service=None,
        cache_service=None,
    )
