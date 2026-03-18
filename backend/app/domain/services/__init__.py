"""
Domain Layer - External Service Interfaces

These interfaces define contracts for external services.
Infrastructure layer implements these interfaces.
Domain and Application layers depend on these abstractions (DIP).
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class IGitHubService(ABC):
    """GitHub service interface - defines contract for GitHub API interactions"""
    
    @abstractmethod
    async def get_repository(self, repo_url: str) -> Dict[str, Any]:
        """Get repository information"""
        pass
    
    @abstractmethod
    async def get_pull_request(self, repo_full_name: str, pr_number: int) -> Dict[str, Any]:
        """Get pull request details"""
        pass
    
    @abstractmethod
    async def get_pull_request_files(self, repo_full_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get files changed in a PR"""
        pass
    
    @abstractmethod
    async def post_pull_request_comment(
        self, 
        repo_full_name: str, 
        pr_number: int, 
        body: str,
        commit_id: Optional[str] = None,
        path: Optional[str] = None,
        line: Optional[int] = None
    ) -> Dict[str, Any]:
        """Post a comment to a PR"""
        pass
    
    @abstractmethod
    async def create_webhook(
        self,
        repo_full_name: str,
        webhook_url: str,
        webhook_secret: str,
        events: List[str]
    ) -> Dict[str, Any]:
        """Create a webhook for the repository"""
        pass
    
    @abstractmethod
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook signature"""
        pass


class ILLMService(ABC):
    """LLM service interface - defines contract for LLM interactions"""
    
    @abstractmethod
    async def analyze_code(
        self,
        code: str,
        language: str,
        analysis_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze code using LLM"""
        pass
    
    @abstractmethod
    async def generate_review_comment(
        self,
        file_path: str,
        code_snippet: str,
        issue_type: str,
        language: str
    ) -> str:
        """Generate a review comment"""
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """Check if LLM service is healthy"""
        pass


class ICacheService(ABC):
    """Cache service interface - defines contract for caching"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
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
    async def enqueue_pr_analysis(self, pr_id: str, data: Dict[str, Any]) -> bool:
        """Enqueue PR analysis task"""
        pass


class IGraphService(ABC):
    """Graph database service interface"""
    
    @abstractmethod
    async def create_node(self, label: str, properties: Dict[str, Any]) -> str:
        """Create a node"""
        pass
    
    @abstractmethod
    async def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a relationship"""
        pass
    
    @abstractmethod
    async def find_cycles(self, start_node: str) -> List[List[str]]:
        """Find circular dependencies"""
        pass
    
    @abstractmethod
    async def get_dependencies(self, node_id: str) -> List[Dict[str, Any]]:
        """Get node dependencies"""
        pass
