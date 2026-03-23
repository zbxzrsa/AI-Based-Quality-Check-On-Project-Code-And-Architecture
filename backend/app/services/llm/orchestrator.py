"""
LLM Orchestrator with Resilience Patterns

Implements primary/fallback provider pattern with circuit breakers
for resilient LLM API calls.

Validates Requirements: 2.2, 2.3, 2.6, 2.8
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .base import BaseLLMProvider, LLMProviderType, LLMRequest, LLMResponse
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from .factory import LLMProviderFactory

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """Configuration for LLM orchestrator"""
    primary_provider: LLMProviderType = LLMProviderType.OPENAI
    fallback_provider: LLMProviderType = LLMProviderType.ANTHROPIC
    primary_model: Optional[str] = None
    fallback_model: Optional[str] = None
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    timeout: int = 30  # Request timeout in seconds


class LLMOrchestrator:
    """
    LLM orchestrator with primary/fallback provider pattern.
    
    Manages multiple LLM providers with automatic failover and
    circuit breaker protection to prevent cascading failures.
    
    Features:
    - Primary/fallback provider pattern
    - Circuit breaker for each provider
    - Automatic failover on primary failure
    - 30-second timeout enforcement
    - Comprehensive error handling
    
    Validates Requirements: 2.2, 2.3, 2.6, 2.8
    """
    
    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        primary_api_key: Optional[str] = None,
        fallback_api_key: Optional[str] = None
    ):
        """
        Initialize LLM orchestrator.
        
        Args:
            config: Orchestrator configuration
            primary_api_key: Optional API key for primary provider
            fallback_api_key: Optional API key for fallback provider
        """
        self.config = config or OrchestratorConfig()
        
        # Create providers
        self.primary_provider = self._create_provider(
            self.config.primary_provider,
            self.config.primary_model,
            primary_api_key,
            self.config.timeout
        )
        
        self.fallback_provider = self._create_provider(
            self.config.fallback_provider,
            self.config.fallback_model,
            fallback_api_key,
            self.config.timeout
        )
        
        # Create circuit breakers
        cb_config = self.config.circuit_breaker_config or CircuitBreakerConfig()
        self.primary_circuit = CircuitBreaker(
            f"{self.config.primary_provider.value}_circuit",
            cb_config
        )
        self.fallback_circuit = CircuitBreaker(
            f"{self.config.fallback_provider.value}_circuit",
            cb_config
        )
        
        # Statistics
        self.primary_calls = 0
        self.fallback_calls = 0
        self.total_failures = 0
        
        logger.info(
            "LLM orchestrator initialized",
            extra={
                "primary_provider": self.config.primary_provider.value,
                "fallback_provider": self.config.fallback_provider.value,
                "timeout": self.config.timeout
            }
        )
    
    def _create_provider(
        self,
        provider_type: LLMProviderType,
        model: Optional[str],
        api_key: Optional[str],
        timeout: int
    ) -> BaseLLMProvider:
        """Create provider instance with configuration"""
        kwargs = {"timeout": timeout}
        if api_key:
            kwargs["api_key"] = api_key
        
        return LLMProviderFactory.create_provider(
            provider_type,
            model=model,
            **kwargs
        )
    
    async def generate(
        self,
        request: LLMRequest,
        use_fallback: bool = True
    ) -> LLMResponse:
        """
        Generate completion with automatic failover.
        
        Attempts to use primary provider first. If primary fails or
        circuit is open, automatically falls back to secondary provider.
        
        Args:
            request: LLM request parameters
            use_fallback: Whether to use fallback on primary failure
            
        Returns:
            LLM response from primary or fallback provider
            
        Raises:
            Exception: If both primary and fallback fail
            
        Validates Requirements: 2.2, 2.3, 2.6, 2.8
        """
        # Try primary provider
        try:
            response = await self.primary_circuit.call_async(
                self.primary_provider.generate,
                request
            )
            self.primary_calls += 1
            
            logger.info(
                "Primary provider succeeded",
                extra={
                    "provider": self.config.primary_provider.value,
                    "tokens": response.tokens["total"],
                    "cost": response.cost
                }
            )
            
            return response
            
        except CircuitBreakerOpenError as e:
            logger.warning(
                f"Primary provider circuit is OPEN: {str(e)}",
                extra={"provider": self.config.primary_provider.value}
            )
            
            if not use_fallback:
                raise
            
            # Fall through to fallback
            
        except Exception as e:
            logger.error(
                f"Primary provider failed: {str(e)}",
                extra={"provider": self.config.primary_provider.value},
                exc_info=True
            )
            
            if not use_fallback:
                raise
            
            # Fall through to fallback
        
        # Try fallback provider
        if use_fallback:
            try:
                response = await self.fallback_circuit.call_async(
                    self.fallback_provider.generate,
                    request
                )
                self.fallback_calls += 1
                
                logger.info(
                    "Fallback provider succeeded",
                    extra={
                        "provider": self.config.fallback_provider.value,
                        "tokens": response.tokens["total"],
                        "cost": response.cost
                    }
                )
                
                return response
                
            except CircuitBreakerOpenError as e:
                self.total_failures += 1
                logger.error(
                    f"Fallback provider circuit is OPEN: {str(e)}",
                    extra={"provider": self.config.fallback_provider.value}
                )
                raise Exception(
                    "Both primary and fallback providers unavailable "
                    "(circuits open)"
                )
                
            except Exception as e:
                self.total_failures += 1
                logger.error(
                    f"Fallback provider failed: {str(e)}",
                    extra={"provider": self.config.fallback_provider.value},
                    exc_info=True
                )
                raise Exception(
                    f"Both primary and fallback providers failed. "
                    f"Last error: {str(e)}"
                )
        
        # Should not reach here
        self.total_failures += 1
        raise Exception("No providers available")
    
    def get_stats(self) -> dict:
        """
        Get orchestrator statistics.
        
        Returns:
            Dictionary with usage statistics and circuit breaker states
        """
        return {
            "primary_calls": self.primary_calls,
            "fallback_calls": self.fallback_calls,
            "total_failures": self.total_failures,
            "primary_circuit": self.primary_circuit.get_stats(),
            "fallback_circuit": self.fallback_circuit.get_stats(),
            "primary_usage": self.primary_provider.get_usage_stats(),
            "fallback_usage": self.fallback_provider.get_usage_stats()
        }
    
    def reset_stats(self):
        """Reset all statistics"""
        self.primary_calls = 0
        self.fallback_calls = 0
        self.total_failures = 0
        self.primary_provider.reset_usage()
        self.fallback_provider.reset_usage()
        
        logger.info("Orchestrator statistics reset")
    
    def reset_circuits(self):
        """Manually reset all circuit breakers"""
        self.primary_circuit.reset()
        self.fallback_circuit.reset()
        
        logger.info("All circuit breakers reset")
    
    def get_primary_provider(self) -> BaseLLMProvider:
        """Get primary provider instance"""
        return self.primary_provider
    
    def get_fallback_provider(self) -> BaseLLMProvider:
        """Get fallback provider instance"""
        return self.fallback_provider


def create_orchestrator(
    primary_provider: LLMProviderType = LLMProviderType.OPENAI,
    fallback_provider: LLMProviderType = LLMProviderType.ANTHROPIC,
    primary_model: Optional[str] = None,
    fallback_model: Optional[str] = None,
    timeout: int = 30
) -> LLMOrchestrator:
    """
    Convenience function to create LLM orchestrator.
    
    Args:
        primary_provider: Primary provider type
        fallback_provider: Fallback provider type
        primary_model: Optional primary model identifier
        fallback_model: Optional fallback model identifier
        timeout: Request timeout in seconds
        
    Returns:
        Configured LLM orchestrator
        
    Example:
        >>> orchestrator = create_orchestrator(
        ...     primary_provider=LLMProviderType.OPENAI,
        ...     fallback_provider=LLMProviderType.ANTHROPIC,
        ...     timeout=30
        ... )
        >>> request = LLMRequest(prompt="Hello, world!")
        >>> response = await orchestrator.generate(request)
    """
    config = OrchestratorConfig(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
        primary_model=primary_model,
        fallback_model=fallback_model,
        timeout=timeout
    )
    
    return LLMOrchestrator(config)
