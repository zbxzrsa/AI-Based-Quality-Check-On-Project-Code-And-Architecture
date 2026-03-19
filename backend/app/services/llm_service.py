"""
Legacy LLM service compatibility layer.
"""

from typing import Any


class _LLMService:
    """Minimal backward-compatible interface used by endpoints/health checks."""

    def is_initialized(self) -> bool:
        return False

    async def generate_architecture_insights(self, architecture_data: dict[str, Any]) -> dict[str, Any]:
        _ = architecture_data
        return {
            "summary": "LLM insights unavailable",
            "recommendations": [],
            "risks": [],
        }


llm_service = _LLMService()
