"""
User-scoped LLM provider resolution.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User
from app.services.llm.base import BaseLLMProvider, LLMProviderType
from app.services.llm.factory import LLMProviderFactory

logger = logging.getLogger(__name__)


PROVIDER_ENUM_MAP: Dict[str, LLMProviderType] = {
    "openrouter": LLMProviderType.OPENROUTER,
    "openai": LLMProviderType.OPENAI,
    "anthropic": LLMProviderType.ANTHROPIC,
    "lmstudio": LLMProviderType.LMSTUDIO,
    "ollama": LLMProviderType.OLLAMA,
    "deepseek": LLMProviderType.DEEPSEEK,
    "google": LLMProviderType.GOOGLE,
    "chatglm": LLMProviderType.CHATGLM,
}

PROVIDER_KEY_FIELDS: Dict[str, str] = {
    "openrouter": "openrouter_api_key",
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
    "deepseek": "deepseek_api_key",
    "google": "google_api_key",
    "chatglm": "chatglm_api_key",
}

PROVIDER_BASE_URL_FIELDS: Dict[str, str] = {
    "deepseek": "deepseek_base_url",
    "google": "google_base_url",
    "chatglm": "chatglm_base_url",
    "ollama": "ollama_base_url",
    "lmstudio": "lmstudio_base_url",
}

PROVIDER_MODEL_FIELDS: Dict[str, str] = {
    "deepseek": "deepseek_model",
    "google": "google_model",
    "chatglm": "chatglm_model",
    "ollama": "ollama_model",
    "lmstudio": "lmstudio_model",
}


def _get_user_ai_settings(user: User) -> Dict[str, Any]:
    return dict(getattr(user, "ai_settings", None) or {})


class UserLLMService:
    """Resolve provider/model/key per user settings with system fallback."""

    @staticmethod
    async def get_user_llm_provider(
        db: AsyncSession,
        user_id: str,
        provider_type: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BaseLLMProvider:
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("User %s not found, using system provider", user_id)
            return UserLLMService._get_system_default_provider(provider_type, model)

        ai_settings = _get_user_ai_settings(user)

        selected_provider = (provider_type or ai_settings.get("default_llm_provider") or settings.DEFAULT_LLM_PROVIDER).lower()
        selected_model = model or ai_settings.get("default_llm_model") or settings.DEFAULT_LLM_MODEL

        kwargs: Dict[str, Any] = {}
        base_url_field = PROVIDER_BASE_URL_FIELDS.get(selected_provider)
        if base_url_field and ai_settings.get(base_url_field):
            kwargs["base_url"] = ai_settings[base_url_field]

        model_field = PROVIDER_MODEL_FIELDS.get(selected_provider)
        if model_field and ai_settings.get(model_field):
            selected_model = ai_settings[model_field]

        key_field = PROVIDER_KEY_FIELDS.get(selected_provider)
        user_api_key = ai_settings.get(key_field) if key_field else None

        if user_api_key or selected_provider in {"ollama", "lmstudio"}:
            return UserLLMService._create_provider_with_key(
                selected_provider,
                selected_model,
                user_api_key,
                **kwargs,
            )

        return UserLLMService._get_system_default_provider(selected_provider, selected_model)

    @staticmethod
    def _create_provider_with_key(
        provider_type: str,
        model: str,
        api_key: Optional[str],
        **kwargs: Any,
    ) -> BaseLLMProvider:
        provider_enum = PROVIDER_ENUM_MAP.get(provider_type.lower())
        if not provider_enum:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        return LLMProviderFactory.create_provider(
            provider_type=provider_enum,
            model=model,
            api_key=api_key,
            **kwargs,
        )

    @staticmethod
    def _get_system_default_provider(
        provider_type: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BaseLLMProvider:
        selected_provider = (provider_type or settings.DEFAULT_LLM_PROVIDER).lower()
        selected_model = model or settings.DEFAULT_LLM_MODEL
        provider_enum = PROVIDER_ENUM_MAP.get(selected_provider)

        if not provider_enum:
            raise ValueError(f"Unsupported provider type: {selected_provider}")

        return LLMProviderFactory.get_provider(
            provider_type=provider_enum,
            model=selected_model,
        )

    @staticmethod
    async def get_user_api_settings(
        db: AsyncSession,
        user_id: str,
    ) -> dict:
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {}
        return _get_user_ai_settings(user)
