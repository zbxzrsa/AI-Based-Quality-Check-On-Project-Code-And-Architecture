"""
OpenAI GPT-4 Provider Implementation

Implements LLM provider interface for OpenAI GPT-4.
Validates Requirements: 1.4
"""

import logging
from typing import Optional
from openai import AsyncOpenAI
import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from .base import BaseLLMProvider, LLMProviderType, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI GPT-4 provider implementation.
    
    Supports GPT-4 and GPT-4 Turbo models with automatic retry
    on transient failures.
    
    Validates Requirements: 1.4, 2.2, 2.3
    """
    
    def __init__(
        self,
        model: str = "gpt-4-turbo-preview",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            model: OpenAI model identifier
            api_key: OpenAI API key
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
        """
        super().__init__(model, api_key)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
        self.timeout = timeout
    
    @retry(
        retry=retry_if_exception_type((
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.InternalServerError
        )),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate completion using OpenAI API.
        
        Implements exponential backoff retry for transient failures
        (connection errors, rate limits, internal server errors).
        
        Args:
            request: LLM request parameters
            
        Returns:
            LLM response with content and metadata
            
        Raises:
            Exception: If generation fails after retries
            
        Validates Requirements: 1.4, 2.2
        """
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
            
            # Enable JSON mode for GPT-4 models if requested
            if request.json_mode and "gpt-4" in self.model:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            usage = response.usage
            
            # Track usage
            self.total_tokens += usage.total_tokens
            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)
            self.total_cost += cost
            
            logger.info(
                f"OpenAI generation successful: {usage.total_tokens} tokens, ${cost:.4f}",
                extra={
                    "provider": "openai",
                    "model": self.model,
                    "tokens": usage.total_tokens,
                    "cost": cost
                }
            )
            
            return LLMResponse(
                content=content,
                provider="openai",
                model=self.model,
                tokens={
                    "prompt": usage.prompt_tokens,
                    "completion": usage.completion_tokens,
                    "total": usage.total_tokens
                },
                cost=cost
            )
            
        except Exception as e:
            logger.error(
                f"OpenAI API error: {str(e)}",
                extra={"provider": "openai", "model": self.model},
                exc_info=True
            )
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def get_provider_type(self) -> LLMProviderType:
        """Get the provider type"""
        return LLMProviderType.OPENAI
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate OpenAI API cost based on token usage.
        
        Pricing as of 2024:
        - GPT-4 Turbo: $0.01/1K prompt tokens, $0.03/1K completion tokens
        - GPT-4: $0.03/1K prompt tokens, $0.06/1K completion tokens
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            Total cost in USD
        """
        if "gpt-4-turbo" in self.model or "gpt-4-1106" in self.model:
            prompt_cost_per_1k = 0.01
            completion_cost_per_1k = 0.03
        else:  # Standard GPT-4
            prompt_cost_per_1k = 0.03
            completion_cost_per_1k = 0.06
        
        prompt_cost = (prompt_tokens / 1000) * prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000) * completion_cost_per_1k
        
        return prompt_cost + completion_cost
