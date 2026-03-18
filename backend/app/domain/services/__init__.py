"""
Domain Layer - External Service Interfaces

These interfaces define contracts for external services.
Infrastructure layer implements these interfaces.
Domain and Application layers depend on these abstractions (DIP).
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional


class AnalysisType(str, Enum):
    """Code analysis types"""

    FULL = "full"
    QUICK = "quick"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"


class ReviewVerdict(str, Enum):
    """Code review verdict"""

    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    COMMENTED = "commented"


class IGitHubService(ABC):
    """GitHub service interface - defines contract for GitHub API interactions"""

    @abstractmethod
    async def get_repository(self, repo_url: str) -> dict[str, Any]:
        """Get repository information"""
        pass

    @abstractmethod
    async def get_pull_request(self, repo_full_name: str, pr_number: int) -> dict[str, Any]:
        """Get pull request details"""
        pass

    @abstractmethod
    async def get_pull_request_files(self, repo_full_name: str, pr_number: int) -> list[dict[str, Any]]:
        """Get files changed in a PR"""
        pass

    @abstractmethod
    async def post_pull_request_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
        commit_id: str | None = None,
        path: str | None = None,
        line: int | None = None,
    ) -> dict[str, Any]:
        """Post a comment to a PR"""
        pass

    @abstractmethod
    async def create_webhook(
        self, repo_full_name: str, webhook_url: str, webhook_secret: str, events: list[str]
    ) -> dict[str, Any]:
        """Create a webhook for the repository"""
        pass

    @abstractmethod
    async def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        pass


class ILLMService(ABC):
    """LLM service interface - defines contract for LLM interactions"""

    @abstractmethod
    async def analyze_code(
        self, code: str, language: str, analysis_type: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Analyze code using LLM"""
        pass

    @abstractmethod
    async def generate_review_comment(self, file_path: str, code_snippet: str, issue_type: str, language: str) -> str:
        """Generate a review comment"""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Check if LLM service is healthy"""
        pass


class ICacheService(ABC):
    """Cache service interface - defines contract for caching"""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Get value by key"""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value with TTL"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass

    @abstractmethod
    async def enqueue_pr_analysis(self, pr_id: str, data: dict[str, Any]) -> bool:
        """Enqueue PR analysis task"""
        pass


class IGraphService(ABC):
    """Graph database service interface"""

    @abstractmethod
    async def create_node(self, label: str, properties: dict[str, Any]) -> str:
        """Create a node"""
        pass

    @abstractmethod
    async def create_relationship(
        self, from_node_id: str, to_node_id: str, relationship_type: str, properties: dict[str, Any] | None = None
    ) -> str:
        """Create a relationship"""
        pass

    @abstractmethod
    async def find_cycles(self, start_node: str) -> list[list[str]]:
        """Find circular dependencies"""
        pass

    @abstractmethod
    async def get_dependencies(self, node_id: str) -> list[dict[str, Any]]:
        """Get node dependencies"""
        pass


class ICodeAnalysisService(ABC):
    """Code analysis service interface"""

    @abstractmethod
    async def analyze_file(self, file_path: str, content: str, language: str) -> dict[str, Any]:
        """Analyze a single file"""
        pass

    @abstractmethod
    async def analyze_pull_request(
        self, repo_full_name: str, pr_number: int, analysis_type: AnalysisType
    ) -> dict[str, Any]:
        """Analyze a pull request"""
        pass

    @abstractmethod
    async def detect_security_issues(self, code: str, language: str) -> list[dict[str, Any]]:
        """Detect security issues in code"""
        pass

    @abstractmethod
    async def calculate_complexity(self, code: str, language: str) -> dict[str, Any]:
        """Calculate code complexity metrics"""
        pass


class ICodeReviewService(ABC):
    """Code review service interface"""

    @abstractmethod
    async def create_review(self, pr_id: str, repo_full_name: str, pr_number: int) -> dict[str, Any]:
        """Create a new code review"""
        pass

    @abstractmethod
    async def add_comment(
        self, review_id: str, file_path: str, line: int, body: str, severity: str = "info"
    ) -> dict[str, Any]:
        """Add a comment to the review"""
        pass

    @abstractmethod
    async def submit_review(self, review_id: str, verdict: ReviewVerdict, summary: str) -> dict[str, Any]:
        """Submit the review"""
        pass

    @abstractmethod
    async def get_review(self, review_id: str) -> dict[str, Any]:
        """Get review details"""
        pass


class ICodeParserService(ABC):
    """Code parsing service interface"""

    @abstractmethod
    async def parse_file(self, content: str, language: str) -> dict[str, Any]:
        """Parse code file and extract AST"""
        pass

    @abstractmethod
    async def extract_entities(self, content: str, language: str) -> list[dict[str, Any]]:
        """Extract code entities (functions, classes, etc.)"""
        pass

    @abstractmethod
    async def detect_dependencies(self, content: str, language: str) -> list[str]:
        """Detect dependencies in code"""
        pass


class IArchitectureService(ABC):
    """Architecture analysis service interface"""

    @abstractmethod
    async def analyze_architecture(self, repo_url: str) -> dict[str, Any]:
        """Analyze project architecture"""
        pass

    @abstractmethod
    async def detect_drift(self, repo_url: str, baseline_id: str) -> dict[str, Any]:
        """Detect architecture drift from baseline"""
        pass

    @abstractmethod
    async def create_baseline(self, repo_url: str, name: str) -> dict[str, Any]:
        """Create architecture baseline"""
        pass


class ILibraryService(ABC):
    """Library management service interface"""

    @abstractmethod
    async def search_library(self, query: str) -> list[dict[str, Any]]:
        """Search for libraries"""
        pass

    @abstractmethod
    async def get_library_info(self, package_name: str) -> dict[str, Any] | None:
        """Get library information"""
        pass

    @abstractmethod
    async def check_vulnerabilities(self, libraries: list[str]) -> list[dict[str, Any]]:
        """Check for known vulnerabilities"""
        pass
