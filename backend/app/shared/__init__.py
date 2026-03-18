"""
Shared infrastructure and utilities for the platform

This module provides shared components used across all services:
- Standards data models (ISO/IEC 25010, ISO/IEC 23396, OWASP Top 10)
- Error handling utilities and custom exceptions
- Circuit breaker implementation
- LLM provider abstraction with failover
- Enhanced Redis cache utilities
- Celery task queue enhancements
- Centralized constants

Validates Requirements: 1.3, 1.4, 1.6, 1.7, 3.1, 3.7, 7.2, 7.3, 7.7, 10.6
"""

# Constants
# Note: LLM providers are in app.services.llm
# from app.services.llm import (
#     LLMProvider,
#     LLMProviderType,
#     LLMProviderConfig,
#     LLMOrchestrator,
#     OpenAIProvider,
#     AnthropicProvider,
#     OllamaProvider,
# )
from .cache_manager import (
    CacheKey,
    CacheKeyPrefix,
    CacheManager,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    get_all_circuit_breaker_states,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)
from .constants import (
    API_DESCRIPTION,
    API_TITLE,
    API_VERSION,
    CACHE_TTL_LONG,
    CACHE_TTL_MEDIUM,
    CACHE_TTL_SHORT,
    DEFAULT_PAGE_SIZE,
    DEFAULT_RATE_LIMIT,
    JWT_TOKEN_EXPIRE_MINUTES,
    MAX_FILES_PER_ANALYSIS,
    MAX_PAGE_SIZE,
    PASSWORD_MIN_LENGTH,
)
from .exceptions import (
    AuthenticationException,
    AuthorizationException,
    CacheException,
    CircuitBreakerException,
    DatabaseException,
    LLMProviderException,
    ServiceException,
    ValidationException,
)
from .standards import (
    ISO23396Practice,
    ISO25010Characteristic,
    ISO25010CharacteristicType,
    ISO25010SubCharacteristic,
    OWASPVulnerability,
    StandardsMapper,
)
from .task_priority import (
    PriorityTask,
    PriorityTaskRouter,
    TaskPriority,
    create_priority_task,
    get_celery_config_with_priorities,
)

__all__ = [
    # Constants
    "API_VERSION",
    "API_TITLE",
    "API_DESCRIPTION",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "CACHE_TTL_SHORT",
    "CACHE_TTL_MEDIUM",
    "CACHE_TTL_LONG",
    "DEFAULT_RATE_LIMIT",
    "MAX_FILES_PER_ANALYSIS",
    "PASSWORD_MIN_LENGTH",
    "JWT_TOKEN_EXPIRE_MINUTES",
    # Standards models
    "ISO25010Characteristic",
    "ISO25010CharacteristicType",
    "ISO25010SubCharacteristic",
    "ISO23396Practice",
    "OWASPVulnerability",
    "StandardsMapper",
    # Error handling
    "ServiceException",
    "LLMProviderException",
    "CircuitBreakerException",
    "CacheException",
    "DatabaseException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerConfig",
    "get_circuit_breaker",
    "reset_all_circuit_breakers",
    "get_all_circuit_breaker_states",
    # LLM abstraction
    "LLMProvider",
    "LLMProviderType",
    "LLMProviderConfig",
    "LLMOrchestrator",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    # Cache utilities
    "CacheManager",
    "CacheKey",
    "CacheKeyPrefix",
    # Celery utilities
    "TaskPriority",
    "PriorityTaskRouter",
    "PriorityTask",
    "get_celery_config_with_priorities",
    "create_priority_task",
]
