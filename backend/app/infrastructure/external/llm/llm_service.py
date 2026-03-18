"""
Infrastructure - LLM Service Implementation

LLM service implementation following Dependency Inversion Principle.
"""

from abc import ABC
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.services import ILLMService

logger = get_logger(__name__)


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Send chat request - override in subclasses"""
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation"""

    def __init__(self, api_key: str = None, base_url: str = None):
        super().__init__(api_key, base_url)
        self.model = "gpt-4"

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Send chat request to OpenAI"""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"OpenAI API error: {response.status}")
                data = await response.json()
                return data["choices"][0]["message"]["content"]


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider implementation"""

    def __init__(self, api_key: str = None, base_url: str = None):
        super().__init__(api_key, base_url)
        self.model = "claude-3-opus-20240229"

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Send chat request to Anthropic"""
        import aiohttp

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Convert messages to Anthropic format
        system_message = ""
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append(msg)

        payload = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", 2000),
            "messages": claude_messages,
        }

        if system_message:
            payload["system"] = system_message

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=headers,
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Anthropic API error: {response.status}")
                data = await response.json()
                return data["content"][0]["text"]


class LLMServiceImpl(ILLMService):
    """
    LLM Service implementation using configurable provider.

    This implementation follows DIP by implementing ILLMService interface.
    Business logic depends on the abstraction, not this concrete class.
    """

    def __init__(
        self,
        provider: BaseLLMProvider = None,
        api_key: str = None,
        provider_type: str = "openai",
    ):
        """
        Initialize LLM service.

        Args:
            provider: LLM provider (OpenAI, Anthropic, etc.)
            api_key: API key for the provider
            provider_type: Type of provider to use
        """
        self._provider = provider
        self._api_key = api_key or settings.LLM_API_KEY
        self._provider_type = provider_type
        self._provider = self._get_provider()

    def _get_provider(self) -> BaseLLMProvider:
        """Get or create LLM provider"""
        if self._provider:
            return self._provider

        if self._provider_type == "openai":
            return OpenAIProvider(
                api_key=self._api_key,
                base_url=settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
            )
        elif self._provider_type == "anthropic":
            return AnthropicProvider(
                api_key=self._api_key,
                base_url=settings.ANTHROPIC_BASE_URL or "https://api.anthropic.com",
            )
        elif self._provider_type == "openrouter":
            return OpenAIProvider(
                api_key=self._api_key,
                base_url="https://openrouter.ai/api/v1",
            )
        else:
            raise ValueError(f"Unknown provider type: {self._provider_type}")

    async def analyze_code(
        self, code: str, language: str, analysis_type: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Analyze code using LLM.

        Args:
            code: Source code to analyze
            language: Programming language
            analysis_type: Type of analysis (full, quick, security)
            context: Additional context for analysis

        Returns:
            Analysis results
        """
        prompt = self._build_analysis_prompt(code, language, analysis_type, context)

        messages = [
            {"role": "system", "content": "You are an expert code reviewer."},
            {"role": "user", "content": prompt},
        ]

        try:
            result = await self._provider.chat(messages)
            return {
                "success": True,
                "analysis": result,
                "language": language,
                "analysis_type": analysis_type,
            }
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "language": language,
                "analysis_type": analysis_type,
            }

    async def generate_review_comment(self, file_path: str, code_snippet: str, issue_type: str, language: str) -> str:
        """Generate a review comment for code issue"""
        prompt = f"""Review the following code from {file_path}:

```{language}
{code_snippet}
```

Issue type: {issue_type}

Provide a constructive code review comment."""

        messages = [
            {"role": "system", "content": "You are an expert code reviewer."},
            {"role": "user", "content": prompt},
        ]

        try:
            result = await self._provider.chat(messages)
            return result
        except Exception as e:
            logger.error(f"Comment generation failed: {e}")
            return f"Code review: {issue_type} issue detected in {file_path}"

    async def check_health(self) -> bool:
        """Check if LLM service is healthy"""
        try:
            messages = [{"role": "user", "content": "Hi"}]
            await self._provider.chat(messages, max_tokens=5)
            return True
        except Exception:
            return False

    def _build_analysis_prompt(
        self, code: str, language: str, analysis_type: str, context: dict[str, Any] | None
    ) -> str:
        """Build analysis prompt based on analysis type"""
        if analysis_type == "security":
            return f"""Analyze the following {language} code for security vulnerabilities:

```{language}
{code}
```

Identify potential security issues and provide recommendations."""
        elif analysis_type == "performance":
            return f"""Analyze the following {language} code for performance issues:

```{language}
{code}
```

Identify bottlenecks and optimization opportunities."""
        else:
            return f"""Perform a comprehensive code review of the following {language} code:

```{language}
{code}
```

Provide feedback on:
1. Code quality
2. Best practices
3. Potential bugs
4. Suggestions for improvement"""
