"""
Shared infrastructure and utilities for the platform

This module provides shared components used across all services:
- Standards data models (ISO/IEC 25010, ISO/IEC 23396, OWASP Top 10)
- Error handling utilities and custom exceptions
- Circuit breaker implementation
- LLM provider abstraction with failover
- Enhanced Redis cache utilities
- Celery task queue enhancements

Validates Requirements: 1.3, 1.4, 1.6, 1.7, 3.1, 3.7, 7.2, 7.3, 7.7, 10.6
"""

from .standards import (
    ISO25010Characteristic,
    ISO25010CharacteristicType,
    ISO25010SubCharacteristic,
    ISO23396Practice,
    OWASPVulnerability,
    StandardsMapper,
)

from .exceptions import (
    ServiceException,
    LLMProviderException,
    CircuitBreakerException,
    CacheException,
    DatabaseException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerConfig,
    get_circuit_breaker,
    reset_all_circuit_breakers,
    get_all_circuit_breaker_states,
)

try:
    from .llm_provider import (
        LLMProvider,
        LLMProviderType,
        LLMProviderConfig,
        LLMOrchestrator,
        OpenAIProvider,
        AnthropicProvider,
        OllamaProvider,
    )
except ImportError:
    # llm_provider module may not be present
    LLMProvider = None
    LLMProviderType = None
    LLMProviderConfig = None
    LLMOrchestrator = None
    OpenAIProvider = None
    AnthropicProvider = None
    OllamaProvider = None

from .cache_manager import (
    CacheManager,
    CacheKey,
    CacheKeyPrefix,
)

from .task_priority import (
    TaskPriority,
    PriorityTaskRouter,
    PriorityTask,
    get_celery_config_with_priorities,
    create_priority_task,
)

__all__ = [
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
