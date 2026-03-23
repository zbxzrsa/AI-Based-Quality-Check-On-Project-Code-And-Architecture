"""
Anthropic Claude 3.5 Provider Implementation

Implements LLM provider interface for Anthropic Claude 3.5.
Validates Requirements: 1.4
"""

import logging
from typing import Optional
from anthropic import AsyncAnthropic
import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from .base import BaseLLMProvider, LLMProviderType, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude 3.5 provider implementation.
    
    Supports Claude 3.5 Sonnet and other Claude models with automatic
    retry on transient failures.
    
    Validates Requirements: 1.4, 2.2, 2.3
    """
    
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Anthropic provider.
        
        Args:
            model: Anthropic model identifier
            api_key: Anthropic API key
            timeout: Request timeout in seconds
        """
        super().__init__(model, api_key)
        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=timeout
        )
        self.timeout = timeout
    
    @retry(
        retry=retry_if_exception_type((
            anthropic.APIConnectionError,
            anthropic.RateLimitError,
            anthropic.InternalServerError
        )),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate completion using Anthropic API.
        
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
            # Add JSON instruction if JSON mode is requested
            prompt = request.prompt
            if request.json_mode:
                prompt += "\n\nPlease respond with valid JSON only."
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system_prompt or "",
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Track usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            self.total_tokens += total_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)
            self.total_cost += cost
            
            logger.info(
                f"Anthropic generation successful: {total_tokens} tokens, ${cost:.4f}",
                extra={
                    "provider": "anthropic",
                    "model": self.model,
                    "tokens": total_tokens,
                    "cost": cost
                }
            )
            
            return LLMResponse(
                content=content,
                provider="anthropic",
                model=self.model,
                tokens={
                    "prompt": input_tokens,
                    "completion": output_tokens,
                    "total": total_tokens
                },
                cost=cost
            )
            
        except Exception as e:
            logger.error(
                f"Anthropic API error: {str(e)}",
                extra={"provider": "anthropic", "model": self.model},
                exc_info=True
            )
            raise Exception(f"Anthropic API error: {str(e)}")
    
    def get_provider_type(self) -> LLMProviderType:
        """Get the provider type"""
        return LLMProviderType.ANTHROPIC
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate Anthropic API cost based on token usage.
        
        Pricing as of 2024:
        - Claude 3.5 Sonnet: $3/MTok input, $15/MTok output
        - Claude 3 Opus: $15/MTok input, $75/MTok output
        - Claude 3 Sonnet: $3/MTok input, $15/MTok output
        - Claude 3 Haiku: $0.25/MTok input, $1.25/MTok output
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Total cost in USD
        """
        # Determine pricing based on model
        if "opus" in self.model.lower():
            input_cost_per_1m = 15.0
            output_cost_per_1m = 75.0
        elif "sonnet" in self.model.lower():
            input_cost_per_1m = 3.0
            output_cost_per_1m = 15.0
        elif "haiku" in self.model.lower():
            input_cost_per_1m = 0.25
            output_cost_per_1m = 1.25
        else:
            # Default to Sonnet pricing
            input_cost_per_1m = 3.0
            output_cost_per_1m = 15.0
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * output_cost_per_1m
        
        return input_cost + output_cost
