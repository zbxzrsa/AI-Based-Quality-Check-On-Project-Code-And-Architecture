"""
Application Layer - Analysis Use Cases

Use cases for code analysis operations.
"""

from dataclasses import dataclass

from app.application.base import Command, Query, UseCaseResult
from app.core.logging import get_logger
from app.domain.services import (
    ICacheService,
    ICodeParserService,
    IGitHubService,
    ILLMService,
)

logger = get_logger(__name__)


@dataclass
class AnalyzeFileCommand:
    """Command to analyze a single file"""

    content: str
    file_path: str
    language: str
    analysis_types: list[str] = None


@dataclass
class AnalyzeArchitectureCommand:
    """Command to analyze project architecture"""

    repo_url: str
    baseline_id: str | None = None


@dataclass
class DetectDriftCommand:
    """Command to detect architecture drift"""

    repo_url: str
    baseline_id: str


class AnalyzeFileUseCase(Command):
    """Use case for analyzing a single file"""

    def __init__(
        self,
        llm_service: ILLMService,
        parser_service: ICodeParserService = None,
    ):
        self.llm = llm_service
        self.parser = parser_service

    async def execute(self, command: AnalyzeFileCommand) -> UseCaseResult:
        """Execute file analysis"""
        try:
            analysis_types = command.analysis_types or ["full"]
            results = []

            # Extract code entities if parser available
            entities = []
            if self.parser:
                entities = await self.parser.extract_entities(command.content, command.language)

            # Run analysis for each type
            for analysis_type in analysis_types:
                result = await self.llm.analyze_code(
                    code=command.content,
                    language=command.language,
                    analysis_type=analysis_type,
                    context={
                        "file_path": command.file_path,
                        "entities": entities,
                    },
                )
                results.append(result)

            return UseCaseResult.ok(
                {
                    "file_path": command.file_path,
                    "language": command.language,
                    "entities": entities,
                    "analysis": results,
                }
            )

        except Exception as e:
            logger.error(f"File analysis failed: {e}")
            return UseCaseResult.err(str(e))


class AnalyzeArchitectureUseCase(Command):
    """Use case for analyzing project architecture"""

    def __init__(
        self,
        github_service: IGitHubService,
        cache_service: ICacheService,
    ):
        self.github = github_service
        self.cache = cache_service

    async def execute(self, command: AnalyzeArchitectureCommand) -> UseCaseResult:
        """Execute architecture analysis"""
        try:
            cache_key = f"architecture:{command.repo_url}"

            # Check cache
            cached = await self.cache.get(cache_key)
            if cached:
                return UseCaseResult.ok({"source": "cache", "analysis": cached})

            # Fetch repository
            repo_info = await self.github.get_repository(command.repo_url)

            # Analyze structure
            analysis = {
                "repo_url": command.repo_url,
                "name": repo_info.get("name"),
                "owner": repo_info.get("owner", {}).get("login"),
                "language": repo_info.get("language"),
                "stars": repo_info.get("stargazers_count"),
                "structure": await self._analyze_structure(repo_info),
            }

            # Cache result
            await self.cache.set(cache_key, str(analysis), ttl=7200)

            return UseCaseResult.ok(
                {
                    "source": "fresh",
                    "analysis": analysis,
                }
            )

        except Exception as e:
            logger.error(f"Architecture analysis failed: {e}")
            return UseCaseResult.err(str(e))

    async def _analyze_structure(self, repo_info: dict) -> dict:
        """Analyze repository structure"""
        # Simplified - would analyze actual code structure
        return {
            "layers": [],
            "components": [],
            "dependencies": [],
        }


class DetectDriftUseCase(Command):
    """Use case for detecting architecture drift"""

    def __init__(
        self,
        github_service: IGitHubService,
        cache_service: ICacheService,
    ):
        self.github = github_service
        self.cache = cache_service

    async def execute(self, command: DetectDriftCommand) -> UseCaseResult:
        """Execute drift detection"""
        try:
            # Get current architecture
            current = await self._get_current_architecture(command.repo_url)

            # Get baseline
            baseline = await self._get_baseline(command.baseline_id)

            if not baseline:
                return UseCaseResult.err("Baseline not found")

            # Compare and find drift
            drift = self._compare_architectures(current, baseline)

            return UseCaseResult.ok(
                {
                    "repo_url": command.repo_url,
                    "baseline_id": command.baseline_id,
                    "drift": drift,
                    "severity": self._calculate_severity(drift),
                }
            )

        except Exception as e:
            return UseCaseResult.err(str(e))

    async def _get_current_architecture(self, repo_url: str) -> dict:
        """Get current architecture"""
        return {}

    async def _get_baseline(self, baseline_id: str) -> dict | None:
        """Get architecture baseline"""
        return None

    def _compare_architectures(self, current: dict, baseline: dict) -> list[dict]:
        """Compare architectures and find drift"""
        return []

    def _calculate_severity(self, drift: list[dict]) -> str:
        """Calculate overall drift severity"""
        if not drift:
            return "none"
        return "medium"


class GetAnalysisHistoryUseCase(Query):
    """Use case for getting analysis history"""

    def __init__(self, cache_service: ICacheService):
        self.cache = cache_service

    async def execute(self, repo_url: str) -> UseCaseResult:
        """Get analysis history"""
        try:
            cache_key = f"analysis_history:{repo_url}"
            history = await self.cache.get(cache_key)

            return UseCaseResult.ok(
                {
                    "history": history or [],
                }
            )

        except Exception as e:
            return UseCaseResult.err(str(e))
