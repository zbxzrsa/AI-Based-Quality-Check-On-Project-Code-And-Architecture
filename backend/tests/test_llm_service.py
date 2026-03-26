import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.llm_service import LLMServiceCompatibility


class LLMServiceCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    def test_is_initialized_returns_true_when_any_provider_is_enabled(self):
        settings_stub = SimpleNamespace(
            is_openai_enabled=lambda: False,
            is_anthropic_enabled=lambda: False,
            is_openrouter_enabled=lambda: True,
            is_lmstudio_enabled=lambda: False,
            is_ollama_enabled=lambda: False,
            is_deepseek_enabled=lambda: False,
            is_google_enabled=lambda: False,
            is_chatglm_enabled=lambda: False,
        )
        with patch("app.services.llm_service.settings", settings_stub):
            self.assertTrue(LLMServiceCompatibility.is_initialized())

    def test_is_initialized_returns_false_when_all_providers_are_disabled(self):
        settings_stub = SimpleNamespace(
            is_openai_enabled=lambda: False,
            is_anthropic_enabled=lambda: False,
            is_openrouter_enabled=lambda: False,
            is_lmstudio_enabled=lambda: False,
            is_ollama_enabled=lambda: False,
            is_deepseek_enabled=lambda: False,
            is_google_enabled=lambda: False,
            is_chatglm_enabled=lambda: False,
        )
        with patch("app.services.llm_service.settings", settings_stub):
            self.assertFalse(LLMServiceCompatibility.is_initialized())

    async def test_generate_architecture_insights_returns_legacy_shape(self):
        provider = SimpleNamespace(
            generate=AsyncMock(
                return_value=SimpleNamespace(
                    content=json.dumps(
                        {
                            "strengths": ["clear module boundaries"],
                            "recommendations": ["reduce coupling in services"],
                        }
                    )
                )
            )
        )

        with patch("app.services.llm_service.get_default_llm_provider", return_value=provider):
            service = LLMServiceCompatibility()
            result = await service.generate_architecture_insights({"components": ["api", "worker"]})

        self.assertEqual(
            result,
            {
                "strengths": ["clear module boundaries"],
                "recommendations": ["reduce coupling in services"],
            },
        )
        provider.generate.assert_awaited_once()

    async def test_generate_architecture_insights_raises_value_error_on_invalid_json(self):
        provider = SimpleNamespace(
            generate=AsyncMock(return_value=SimpleNamespace(content="not-json"))
        )

        with patch("app.services.llm_service.get_default_llm_provider", return_value=provider):
            service = LLMServiceCompatibility()
            with self.assertRaisesRegex(ValueError, "Invalid JSON returned by LLM provider"):
                await service.generate_architecture_insights({"components": ["api"]})


if __name__ == "__main__":
    unittest.main()
