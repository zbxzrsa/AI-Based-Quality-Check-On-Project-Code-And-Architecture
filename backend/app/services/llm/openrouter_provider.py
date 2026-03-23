"""
OpenRouter Provider Implementation

OpenRouter provide统一interface访问多item LLM provide商的模型。
support OpenAI、Anthropic、Google 等多itemprovide商。
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


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter provide者实现
    
    OpenRouter provide统一的 API interface访问多item LLM provide商：
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)
    - Google (Gemini Pro)
    - Meta (Llama 2, Llama 3)
    - 以及更多模型
    
    use OpenAI 兼容的 API format，便于integration。
    """
    
    def __init__(
        self,
        model: str = "anthropic/claude-3.5-sonnet",
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 60,
        app_name: str = "AI Code Review Platform"
    ):
        """
        初始化 OpenRouter provide者
        
        Args:
            model: 模型标识符 (例如: "anthropic/claude-3.5-sonnet", "openai/gpt-4")
            api_key: OpenRouter API key
            base_url: OpenRouter API 基础 URL
            timeout: requesttimeout时间（sec）
            app_name: 应用名称（用于 OpenRouter 统计）
        """
        super().__init__(model, api_key)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            default_headers={
                "HTTP-Referer": "https://github.com/ai-code-review",
                "X-Title": app_name
            }
        )
        self.timeout = timeout
        self.app_name = app_name
    
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
        use OpenRouter API generateresponse
        
        对临时性error（connecterror、速率限制、内部service器error）
        实现指数退避retry策略。
        
        Args:
            request: LLM requestparam
            
        Returns:
            containcontentand元data的 LLM response
            
        Raises:
            Exception: retry后generatefailure
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
            
            # 如果request JSON 模式，addresponseformat
            if request.json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            usage = response.usage
            
            # 跟踪use情况
            self.total_tokens += usage.total_tokens
            
            # OpenRouter 在response头中return实际成本
            # 这里use估算value，实际成本可从response头get
            cost = self._estimate_cost(usage.prompt_tokens, usage.completion_tokens)
            self.total_cost += cost
            
            logger.info(
                f"OpenRouter generatesuccess: {usage.total_tokens} tokens, 估算成本 ${cost:.4f}",
                extra={
                    "provider": "openrouter",
                    "model": self.model,
                    "tokens": usage.total_tokens,
                    "cost": cost
                }
            )
            
            return LLMResponse(
                content=content,
                provider="openrouter",
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
                f"OpenRouter API error: {str(e)}",
                extra={"provider": "openrouter", "model": self.model},
                exc_info=True
            )
            raise Exception(f"OpenRouter API error: {str(e)}")
    
    def get_provider_type(self) -> LLMProviderType:
        """getprovide者type"""
        return LLMProviderType.OPENROUTER
    
    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        估算 OpenRouter API 成本
        
        不同模型的定价不同，这里provide常见模型的估算：
        - Claude 3.5 Sonnet: $3/1M prompt tokens, $15/1M completion tokens
        - GPT-4 Turbo: $10/1M prompt tokens, $30/1M completion tokens
        - GPT-3.5 Turbo: $0.5/1M prompt tokens, $1.5/1M completion tokens
        
        note：实际成本应从 OpenRouter response头中get
        
        Args:
            prompt_tokens: hint词 token 数量
            completion_tokens: complete token 数量
            
        Returns:
            估算的总成本（美元）
        """
        # 根据模型名称估算成本
        model_lower = self.model.lower()
        
        if "claude-3.5-sonnet" in model_lower or "claude-3-5-sonnet" in model_lower:
            prompt_cost_per_1m = 3.0
            completion_cost_per_1m = 15.0
        elif "claude-3-opus" in model_lower:
            prompt_cost_per_1m = 15.0
            completion_cost_per_1m = 75.0
        elif "gpt-4-turbo" in model_lower or "gpt-4-1106" in model_lower:
            prompt_cost_per_1m = 10.0
            completion_cost_per_1m = 30.0
        elif "gpt-4" in model_lower:
            prompt_cost_per_1m = 30.0
            completion_cost_per_1m = 60.0
        elif "gpt-3.5-turbo" in model_lower:
            prompt_cost_per_1m = 0.5
            completion_cost_per_1m = 1.5
        else:
            # 默认use中等价格估算
            prompt_cost_per_1m = 5.0
            completion_cost_per_1m = 15.0
        
        prompt_cost = (prompt_tokens / 1_000_000) * prompt_cost_per_1m
        completion_cost = (completion_tokens / 1_000_000) * completion_cost_per_1m
        
        return prompt_cost + completion_cost
