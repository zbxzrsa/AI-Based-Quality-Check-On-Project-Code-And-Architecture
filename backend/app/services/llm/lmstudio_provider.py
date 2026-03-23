"""
LM Studio Provider Implementation

LM Studio exposes a local OpenAI-compatible REST API.
This provider connects to an LM Studio instance for local LLM inference.

Supports Requirements: 1.4 (local/private LLM integration)
"""

import logging
from typing import Optional
import httpx
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


class LMStudioProvider(BaseLLMProvider):
    """
    LM Studio local LLM provider.

    LM Studio (https://lmstudio.ai) serves a local OpenAI-compatible API.
    No API key is required — the server must be running and a model loaded
    before requests are made.

    Endpoint format:  http://<host>:<port>/v1
    Default:          http://localhost:1234/v1
    """

    def __init__(
        self,
        model: str = "local-model",
        base_url: str = "http://localhost:1234/v1",
        timeout: int = 120,
        api_key: Optional[str] = None,
    ):
        """
        Initialise the LM Studio provider.

        Args:
            model:    Model identifier as shown in LM Studio (e.g. "qwen2.5-coder-7b-instruct").
                      LM Studio also accepts "local-model" as a catch-all when only one
                      model is loaded.
            base_url: Base URL of the LM Studio server (must end without trailing slash
                      — the AsyncOpenAI client appends /chat/completions automatically).
            timeout:  HTTP request timeout in seconds.  Local inference can be slow,
                      so the default is generous (120 s).
            api_key:  Not required for LM Studio; pass any non-empty string if the
                      underlying HTTP client requires one.
        """
        super().__init__(model, api_key or "lm-studio")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # LM Studio is OpenAI-API-compatible, so we reuse AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=api_key or "lm-studio",  # dummy key — LM Studio ignores it
            base_url=self.base_url,
            timeout=timeout,
        )

        logger.info(
            "LM Studio provider initialised",
            extra={"base_url": self.base_url, "model": self.model},
        )

    @retry(
        retry=retry_if_exception_type((
            openai.APIConnectionError,
            openai.InternalServerError,
            httpx.ConnectError,
            httpx.TimeoutException,
        )),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a completion via the LM Studio OpenAI-compatible API.

        Args:
            request: LLM request parameters

        Returns:
            LLMResponse with content and token metadata

        Raises:
            Exception: If all retry attempts fail
        """
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

            kwargs: dict = {
                "model": self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }

            # LM Studio supports response_format for JSON mode on compatible models
            if request.json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content or ""
            usage = response.usage

            # Token counts (LM Studio provides these)
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            self.total_tokens += total_tokens
            # Local inference has no monetary cost
            self.total_cost += 0.0

            logger.info(
                "LM Studio generation successful",
                extra={
                    "provider": "lmstudio",
                    "model": self.model,
                    "tokens": total_tokens,
                },
            )

            return LLMResponse(
                content=content,
                provider="lmstudio",
                model=self.model,
                tokens={
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": total_tokens,
                },
                cost=0.0,  # Local inference is free
            )

        except Exception as e:
            logger.error(
                f"LM Studio API error: {str(e)}",
                extra={"provider": "lmstudio", "model": self.model, "base_url": self.base_url},
                exc_info=True,
            )
            raise Exception(f"LM Studio API error: {str(e)}")

    def get_provider_type(self) -> LLMProviderType:
        """Return the provider type enum value."""
        return LLMProviderType.LMSTUDIO
