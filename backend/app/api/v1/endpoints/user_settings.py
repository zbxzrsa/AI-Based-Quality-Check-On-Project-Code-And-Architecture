"""User AI settings endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenPayload, get_current_user
from app.database.postgresql import get_db
from app.models import User

router = APIRouter()

SUPPORTED_PROVIDERS = [
    "openrouter",
    "openai",
    "anthropic",
    "deepseek",
    "google",
    "chatglm",
    "ollama",
    "lmstudio",
]


class UpdateAPISettingsRequest(BaseModel):
    openrouter_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    chatglm_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    lmstudio_base_url: Optional[str] = None
    lmstudio_model: Optional[str] = None
    deepseek_base_url: Optional[str] = None
    deepseek_model: Optional[str] = None
    google_base_url: Optional[str] = None
    google_model: Optional[str] = None
    chatglm_base_url: Optional[str] = None
    chatglm_model: Optional[str] = None
    default_llm_provider: Optional[str] = None
    default_llm_model: Optional[str] = None


class APISettingsResponse(BaseModel):
    openrouter_api_key_set: bool
    openai_api_key_set: bool
    anthropic_api_key_set: bool
    deepseek_api_key_set: bool
    google_api_key_set: bool
    chatglm_api_key_set: bool
    ollama_base_url: Optional[str]
    ollama_model: Optional[str]
    lmstudio_base_url: Optional[str]
    lmstudio_model: Optional[str]
    deepseek_base_url: Optional[str]
    deepseek_model: Optional[str]
    google_base_url: Optional[str]
    google_model: Optional[str]
    chatglm_base_url: Optional[str]
    chatglm_model: Optional[str]
    default_llm_provider: Optional[str]
    default_llm_model: Optional[str]
    message: str


def _response_from_ai_settings(ai_settings: dict, message: str) -> APISettingsResponse:
    return APISettingsResponse(
        openrouter_api_key_set=bool(ai_settings.get("openrouter_api_key")),
        openai_api_key_set=bool(ai_settings.get("openai_api_key")),
        anthropic_api_key_set=bool(ai_settings.get("anthropic_api_key")),
        deepseek_api_key_set=bool(ai_settings.get("deepseek_api_key")),
        google_api_key_set=bool(ai_settings.get("google_api_key")),
        chatglm_api_key_set=bool(ai_settings.get("chatglm_api_key")),
        ollama_base_url=ai_settings.get("ollama_base_url"),
        ollama_model=ai_settings.get("ollama_model"),
        lmstudio_base_url=ai_settings.get("lmstudio_base_url"),
        lmstudio_model=ai_settings.get("lmstudio_model"),
        deepseek_base_url=ai_settings.get("deepseek_base_url"),
        deepseek_model=ai_settings.get("deepseek_model"),
        google_base_url=ai_settings.get("google_base_url"),
        google_model=ai_settings.get("google_model"),
        chatglm_base_url=ai_settings.get("chatglm_base_url"),
        chatglm_model=ai_settings.get("chatglm_model"),
        default_llm_provider=ai_settings.get("default_llm_provider"),
        default_llm_model=ai_settings.get("default_llm_model"),
        message=message,
    )


@router.get("/api-settings", response_model=APISettingsResponse)
async def get_user_api_settings(
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).filter(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _response_from_ai_settings(user.ai_settings or {}, "API settings retrieved successfully")


@router.put("/api-settings", response_model=APISettingsResponse)
async def update_user_api_settings(
    settings: UpdateAPISettingsRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).filter(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    ai_settings = dict(user.ai_settings or {})

    for field_name, value in settings.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            ai_settings.pop(field_name, None)
        else:
            ai_settings[field_name] = value

    provider = ai_settings.get("default_llm_provider")
    if provider and provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Must be one of: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    await db.execute(
        update(User)
        .where(User.id == current_user.user_id)
        .values(ai_settings=ai_settings, updated_at=datetime.utcnow())
    )
    await db.commit()
    return _response_from_ai_settings(ai_settings, "API settings updated successfully")


@router.delete("/api-settings/{provider}", response_model=APISettingsResponse)
async def delete_user_api_key(
    provider: str,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Must be one of: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    result = await db.execute(select(User).filter(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    ai_settings = dict(user.ai_settings or {})
    for suffix in ("api_key", "base_url", "model"):
        ai_settings.pop(f"{provider}_{suffix}", None)

    await db.execute(
        update(User)
        .where(User.id == current_user.user_id)
        .values(ai_settings=ai_settings, updated_at=datetime.utcnow())
    )
    await db.commit()

    return _response_from_ai_settings(ai_settings, f"{provider.capitalize()} settings deleted successfully")
