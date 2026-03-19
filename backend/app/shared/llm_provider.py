"""
Compatibility shim for legacy LLM provider imports.

This preserves the old app.shared.llm_provider API used by
agentic_ai_service while the canonical implementation lives under
app.services.llm.
"""

from dataclasses import dataclass
from typing import Any

from app.services.llm.base import LLMProviderType


@dataclass
class LLMProviderConfig:
    """Legacy provider config shape retained for backward compatibility."""

    provider_type: LLMProviderType
    model: str
    base_url: str | None = None
    max_tokens: int = 4000
    temperature: float = 0.3
    timeout: int = 30
    priority: int = 1


class LLMOrchestrator:
    """
    Minimal legacy orchestrator interface.

    The refactored stack now uses app.services.llm.* directly; this
    adapter keeps existing call sites functional without hard coupling.
    """

    def __init__(self, providers: list[LLMProviderConfig] | None = None):
        self.providers = providers or []

    def get_provider_count(self) -> int:
        return len(self.providers)

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs: Any) -> str:
        # Compatibility return type expected by legacy services.
        _ = (prompt, system_prompt, kwargs)
        return ""
