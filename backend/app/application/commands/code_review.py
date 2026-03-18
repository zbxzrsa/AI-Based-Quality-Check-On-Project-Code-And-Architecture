"""
Application Layer - Code Review Use Cases

Use cases for code review operations.
"""

from dataclasses import dataclass

from app.application.base import Command, Query, UseCaseResult
from app.core.logging import get_logger
from app.domain.services import (
    ICacheService,
    IGitHubService,
    ILLMService,
    ReviewVerdict,
)

logger = get_logger(__name__)


@dataclass
class CreateReviewCommand:
    """Command to create a code review"""

    repo_full_name: str
    pr_number: int
    analysis_type: str = "full"


@dataclass
class SubmitReviewCommand:
    """Command to submit a code review"""

    review_id: str
    verdict: ReviewVerdict
    summary: str


class CreateReviewUseCase(Command):
    """
    Use case for creating a code review.

    Orchestrates:
    1. Fetch PR files from GitHub
    2. Analyze each file with LLM
    3. Cache results
    4. Return review results
    """

    def __init__(
        self,
        github_service: IGitHubService,
        llm_service: ILLMService,
        cache_service: ICacheService,
    ):
        self.github = github_service
        self.llm = llm_service
        self.cache = cache_service

    async def execute(self, command: CreateReviewCommand) -> UseCaseResult:
        """Execute code review creation"""
        try:
            # Check cache
            cache_key = f"review:{command.repo_full_name}:{command.pr_number}"
            cached = await self.cache.get(cache_key)
            if cached:
                return UseCaseResult.ok({"source": "cache", "review": cached})

            # Fetch PR files
            files = await self.github.get_pull_request_files(command.repo_full_name, command.pr_number)

            if not files:
                return UseCaseResult.ok(
                    {
                        "source": "fresh",
                        "review": {"message": "No files changed"},
                    }
                )

            # Analyze each file
            findings = []
            for file_data in files[:10]:  # Limit to 10 files
                content = file_data.get("patch", "")
                if not content:
                    continue

                filename = file_data.get("filename", "")
                language = self._detect_language(filename)

                try:
                    analysis = await self.llm.analyze_code(
                        code=content,
                        language=language,
                        analysis_type=command.analysis_type,
                        context={"filename": filename},
                    )

                    if analysis.get("success"):
                        findings.append(
                            {
                                "filename": filename,
                                "analysis": analysis.get("analysis"),
                                "status": file_data.get("status"),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to analyze {filename}: {e}")

            # Create review object
            review = {
                "repo_full_name": command.repo_full_name,
                "pr_number": command.pr_number,
                "analysis_type": command.analysis_type,
                "files_analyzed": len(findings),
                "findings": findings,
            }

            # Cache result
            await self.cache.set(cache_key, str(review), ttl=3600)

            logger.info(f"Review created: {command.repo_full_name}/PR{command.pr_number} ({len(findings)} files)")

            return UseCaseResult.ok(
                {
                    "source": "fresh",
                    "review": review,
                }
            )

        except Exception as e:
            logger.error(f"Failed to create review: {e}")
            return UseCaseResult.err(str(e))

    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".c": "c",
            ".swift": "swift",
            ".kt": "kotlin",
        }

        for ext, lang in ext_map.items():
            if filename.endswith(ext):
                return lang
        return "text"


class SubmitReviewUseCase(Command):
    """Use case for submitting a code review"""

    def __init__(self, github_service: IGitHubService):
        self.github = github_service

    async def execute(self, command: SubmitReviewCommand) -> UseCaseResult:
        """Submit the review"""
        try:
            # In a real implementation, would post to GitHub
            logger.info(f"Review submitted: {command.review_id}")

            return UseCaseResult.ok(
                {
                    "review_id": command.review_id,
                    "verdict": command.verdict,
                    "status": "submitted",
                }
            )

        except Exception as e:
            return UseCaseResult.err(str(e))


class GetReviewUseCase(Query):
    """Use case for retrieving a code review"""

    def __init__(self, cache_service: ICacheService):
        self.cache = cache_service

    async def execute(self, review_id: str) -> UseCaseResult:
        """Get review by ID"""
        try:
            cache_key = f"review:{review_id}"
            cached = await self.cache.get(cache_key)

            if not cached:
                return UseCaseResult.err("Review not found")

            return UseCaseResult.ok({"review": cached})

        except Exception as e:
            return UseCaseResult.err(str(e))
