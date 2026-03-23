"""
LLM Client Module

Multi-provider LLM client supporting GPT-4 and Claude 3.5 with
resilience patterns (circuit breaker, primary/fallback), code analysis prompts,
and response parsing.

Validates Requirements: 1.4, 2.2, 2.3, 2.6, 2.8
"""

from .base import (
    BaseLLMProvider,
    LLMProviderType,
    LLMRequest,
    LLMResponse
)
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .lmstudio_provider import LMStudioProvider
from .factory import LLMProviderFactory, get_llm_provider
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpenError
)
from .orchestrator import (
    LLMOrchestrator,
    OrchestratorConfig,
    create_orchestrator
)
from .prompts import (
    AnalysisType,
    PromptTemplate,
    CodeAnalysisPrompts,
    PromptManager,
    get_prompt_manager
)
from .response_parser import (
    Severity,
    ReviewComment,
    ParseResult,
    ResponseParser,
    parse_llm_response
)

__all__ = [
    "BaseLLMProvider",
    "LLMProviderType",
    "LLMRequest",
    "LLMResponse",
    "OpenAIProvider",
    "AnthropicProvider",
    "LMStudioProvider",
    "LLMProviderFactory",
    "get_llm_provider",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitBreakerOpenError",
    "LLMOrchestrator",
    "OrchestratorConfig",
    "create_orchestrator",
    "AnalysisType",
    "PromptTemplate",
    "CodeAnalysisPrompts",
    "PromptManager",
    "get_prompt_manager",
    "Severity",
    "ReviewComment",
    "ParseResult",
    "ResponseParser",
    "parse_llm_response",
]
