"""
Base LLM Provider Interface

Defines the abstract interface for all LLM providers.
Validates Requirements: 1.4
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class LLMProviderType(str, Enum):
    """Supported LLM provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    LMSTUDIO = "lmstudio"


@dataclass
class LLMRequest:
    """Request parameters for LLM generation"""
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4000
    json_mode: bool = False
    
    def __post_init__(self):
        """Validate request parameters"""
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")


@dataclass
class LLMResponse:
    """Response from LLM generation"""
    content: str
    provider: str
    model: str
    tokens: Dict[str, int]  # prompt, completion, total
    cost: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "tokens": self.tokens,
            "cost": self.cost
        }


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM providers must implement this interface to ensure
    consistent behavior across different providers.
    
    Validates Requirements: 1.4
    """
    
    def __init__(self, model: str, api_key: Optional[str] = None):
        """
        Initialize LLM provider.
        
        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-5-sonnet-20241022")
            api_key: API key for authentication
        """
        self.model = model
        self.api_key = api_key
        self.total_tokens = 0
        self.total_cost = 0.0
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate completion from LLM.
        
        Args:
            request: LLM request parameters
            
        Returns:
            LLM response with content and metadata
            
        Raises:
            Exception: If generation fails
        """
        pass
    
    @abstractmethod
    def get_provider_type(self) -> LLMProviderType:
        """Get the provider type"""
        pass
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "provider": self.get_provider_type().value,
            "model": self.model
        }
    
    def reset_usage(self):
        """Reset usage tracking"""
        self.total_tokens = 0
        self.total_cost = 0.0
