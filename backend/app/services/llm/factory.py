"""
LLM Provider Factory

Factory for creating and managing LLM provider instances.
Validates Requirements: 1.4, 2.3
"""

import logging
from typing import Optional, Dict

from app.core.config import settings
from .base import BaseLLMProvider, LLMProviderType
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .openrouter_provider import OpenRouterProvider
from .lmstudio_provider import LMStudioProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.
    
    Manages provider instantiation with proper configuration
    and provides singleton instances for efficiency.
    
    Validates Requirements: 1.4, 2.3
    """
    
    _instances: Dict[str, BaseLLMProvider] = {}
    
    @classmethod
    def create_provider(
        cls,
        provider_type: LLMProviderType,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            provider_type: Type of provider to create
            model: Optional model identifier (uses default if not provided)
            api_key: Optional API key (uses settings if not provided)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Configured LLM provider instance
            
        Raises:
            ValueError: If provider type is not supported
            Exception: If provider initialization fails
        """
        try:
            if provider_type == LLMProviderType.OPENAI:
                return cls._create_openai_provider(model, api_key, **kwargs)
            elif provider_type == LLMProviderType.ANTHROPIC:
                return cls._create_anthropic_provider(model, api_key, **kwargs)
            elif provider_type == LLMProviderType.OPENROUTER:
                return cls._create_openrouter_provider(model, api_key, **kwargs)
            elif provider_type == LLMProviderType.LMSTUDIO:
                return cls._create_lmstudio_provider(model, **kwargs)
            else:
                raise ValueError(f"Unsupported provider type: {provider_type}")
                
        except Exception as e:
            provider_name = provider_type.value if hasattr(provider_type, 'value') else str(provider_type)
            logger.error(
                f"Failed to create {provider_name} provider: {str(e)}",
                extra={"provider": provider_name},
                exc_info=True
            )
            raise
    
    @classmethod
    def _create_openai_provider(
        cls,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> OpenAIProvider:
        """Create OpenAI provider instance"""
        model = model or "gpt-4-turbo-preview"
        api_key = api_key or settings.OPENAI_API_KEY
        
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        logger.info(
            f"Creating OpenAI provider with model: {model}",
            extra={"provider": "openai", "model": model}
        )
        
        return OpenAIProvider(
            model=model,
            api_key=api_key,
            base_url=kwargs.get("base_url"),
            timeout=kwargs.get("timeout", 30)
        )
    
    @classmethod
    def _create_anthropic_provider(
        cls,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> AnthropicProvider:
        """Create Anthropic provider instance"""
        model = model or "claude-3-5-sonnet-20241022"
        api_key = api_key or settings.ANTHROPIC_API_KEY
        
        if not api_key:
            raise ValueError("Anthropic API key not configured")
        
        logger.info(
            f"Creating Anthropic provider with model: {model}",
            extra={"provider": "anthropic", "model": model}
        )
        
        return AnthropicProvider(
            model=model,
            api_key=api_key,
            timeout=kwargs.get("timeout", 30)
        )
    
    @classmethod
    def _create_openrouter_provider(
        cls,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> OpenRouterProvider:
        """Create OpenRouter provider instance"""
        model = model or settings.DEFAULT_LLM_MODEL
        api_key = api_key or settings.OPENROUTER_API_KEY
        
        if not api_key:
            raise ValueError("OpenRouter API key not configured")
        
        logger.info(
            f"Creating OpenRouter provider with model: {model}",
            extra={"provider": "openrouter", "model": model}
        )
        
        return OpenRouterProvider(
            model=model,
            api_key=api_key,
            base_url=settings.OPENROUTER_BASE_URL,
            timeout=kwargs.get("timeout", 60)
        )
    
    @classmethod
    def _create_lmstudio_provider(
        cls,
        model: Optional[str] = None,
        **kwargs
    ) -> LMStudioProvider:
        """Create LM Studio provider instance"""
        base_url = kwargs.get("base_url") or settings.LMSTUDIO_BASE_URL
        model = model or settings.LMSTUDIO_MODEL
        timeout = kwargs.get("timeout", 120)

        logger.info(
            f"Creating LM Studio provider — base_url: {base_url}, model: {model}",
            extra={"provider": "lmstudio", "model": model}
        )

        return LMStudioProvider(
            model=model,
            base_url=base_url,
            timeout=timeout,
        )

    @classmethod
    def get_provider(
        cls,
        provider_type: LLMProviderType,
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> BaseLLMProvider:
        """
        Get an LLM provider instance (cached by default).
        
        Args:
            provider_type: Type of provider to get
            model: Optional model identifier
            use_cache: Whether to use cached instance
            
        Returns:
            LLM provider instance
        """
        cache_key = f"{provider_type.value}:{model or 'default'}"
        
        if use_cache and cache_key in cls._instances:
            logger.debug(
                f"Returning cached provider: {cache_key}",
                extra={"provider": provider_type.value, "model": model}
            )
            return cls._instances[cache_key]
        
        provider = cls.create_provider(provider_type, model)
        
        if use_cache:
            cls._instances[cache_key] = provider
            logger.debug(
                f"Cached provider: {cache_key}",
                extra={"provider": provider_type.value, "model": model}
            )
        
        return provider
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached provider instances"""
        cls._instances.clear()
        logger.info("Cleared all cached LLM provider instances")


def get_llm_provider(
    provider_type: LLMProviderType = LLMProviderType.OPENAI,
    model: Optional[str] = None
) -> BaseLLMProvider:
    """
    Convenience function to get an LLM provider instance.
    
    Args:
        provider_type: Type of provider (default: OpenAI)
        model: Optional model identifier
        
    Returns:
        LLM provider instance
        
    Example:
        >>> provider = get_llm_provider(LLMProviderType.OPENAI, "gpt-4")
        >>> request = LLMRequest(prompt="Hello, world!")
        >>> response = await provider.generate(request)
    """
    return LLMProviderFactory.get_provider(provider_type, model)


def get_default_llm_provider(model: Optional[str] = None) -> BaseLLMProvider:
    """
    get默认config的 LLM provide者
    
    根据envvariable DEFAULT_LLM_PROVIDER 自动选择provide者：
    - openrouter: use OpenRouter (support多item模型)
    - openai: use OpenAI
    - anthropic: use Anthropic
    
    Args:
        model: 可选的模型标识符，如果未provide则use DEFAULT_LLM_MODEL
        
    Returns:
        config好的 LLM providerInstance
        
    Example:
        >>> # use默认config
        >>> provider = get_default_llm_provider()
        >>> 
        >>> # 指定模型
        >>> provider = get_default_llm_provider("anthropic/claude-3.5-sonnet")
    """
    provider_name = settings.DEFAULT_LLM_PROVIDER.lower()
    model = model or settings.DEFAULT_LLM_MODEL
    
    provider_map = {
        "openrouter": LLMProviderType.OPENROUTER,
        "openai": LLMProviderType.OPENAI,
        "anthropic": LLMProviderType.ANTHROPIC,
        "lmstudio": LLMProviderType.LMSTUDIO,
    }
    
    provider_type = provider_map.get(provider_name, LLMProviderType.OPENROUTER)
    
    logger.info(
        f"Using default LLM provider: {provider_name} with model: {model}",
        extra={"provider": provider_name, "model": model}
    )
    
    return LLMProviderFactory.get_provider(provider_type, model)
