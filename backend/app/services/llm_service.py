"""
Compatibility shim for legacy `app.services.llm_service` imports.
"""

import json
import logging
from typing import Any, Dict

from app.core.config import settings
from app.services.llm.base import LLMRequest
from app.services.llm.factory import get_default_llm_provider

logger = logging.getLogger(__name__)


class LLMServiceCompatibility:
    @staticmethod
    def is_initialized() -> bool:
        return any(
            [
                settings.is_openai_enabled(),
                settings.is_anthropic_enabled(),
                settings.is_openrouter_enabled(),
                settings.is_lmstudio_enabled(),
                settings.is_ollama_enabled(),
                settings.is_deepseek_enabled(),
                settings.is_google_enabled(),
                settings.is_chatglm_enabled(),
            ]
        )

    async def generate_architecture_insights(self, architecture_data: Dict[str, Any]) -> Dict[str, Any]:
        provider = get_default_llm_provider()
        request = LLMRequest(
            prompt=json.dumps(architecture_data, ensure_ascii=False),
            system_prompt=(
                "You are an architecture reviewer. "
                "Return strict JSON with keys strengths and recommendations, both arrays of strings."
            ),
            temperature=0.2,
            max_tokens=800,
            json_mode=True,
        )
        response = await provider.generate(request)
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError as exc:
            logger.warning("Architecture insight JSON parse failed: %s", exc)
            raise ValueError("Invalid JSON returned by LLM provider") from exc

        return {
            "strengths": parsed.get("strengths", []),
            "recommendations": parsed.get("recommendations", []),
        }


llm_service = LLMServiceCompatibility()
