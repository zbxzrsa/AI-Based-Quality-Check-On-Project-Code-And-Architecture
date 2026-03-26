"""
Generic OpenAI-compatible provider implementation.
"""

import logging
from typing import Optional

import openai
from openai import AsyncOpenAI
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .base import BaseLLMProvider, LLMProviderType, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for vendors exposing the OpenAI chat-completions protocol."""

    def __init__(
        self,
        provider_type: LLMProviderType,
        model: str,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        super().__init__(model, api_key or provider_type.value)
        self.provider_type = provider_type
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = AsyncOpenAI(
            api_key=api_key or provider_type.value,
            base_url=self.base_url,
            timeout=timeout,
        )

    @retry(
        retry=retry_if_exception_type(
            (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def generate(self, request: LLMRequest) -> LLMResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        total_tokens = getattr(usage, "total_tokens", 0) if usage else 0
        self.total_tokens += total_tokens

        return LLMResponse(
            content=content,
            provider=self.provider_type.value,
            model=self.model,
            tokens={
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": total_tokens,
            },
            cost=0.0,
        )

    def get_provider_type(self) -> LLMProviderType:
        return self.provider_type
