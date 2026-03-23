"""
userset API endpoint

管理user的item人set，包括 API keyconfig
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from app.database.postgresql import get_db
from app.auth import TokenPayload, get_current_user, User

router = APIRouter()


class UserAPISettings(BaseModel):
    """user API set模型"""
    openrouter_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_llm_provider: Optional[str] = None
    default_llm_model: Optional[str] = None


class UpdateAPISettingsRequest(BaseModel):
    """update API setrequest"""
    openrouter_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_llm_provider: Optional[str] = None
    default_llm_model: Optional[str] = None


class APISettingsResponse(BaseModel):
    """API setresponse"""
    openrouter_api_key_set: bool
    openai_api_key_set: bool
    anthropic_api_key_set: bool
    default_llm_provider: Optional[str]
    default_llm_model: Optional[str]
    message: str


@router.get("/api-settings", response_model=APISettingsResponse)
async def get_user_api_settings(
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    getuser的 API set
    
    return API key是否已set（不return实际key）
    """
    # getuserinfo
    result = await db.execute(
        select(User).filter(User.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # checkuser的 metadata 中是否有 API set
    metadata = user.metadata or {}
    api_settings = metadata.get('api_settings', {})
    
    return APISettingsResponse(
        openrouter_api_key_set=bool(api_settings.get('openrouter_api_key')),
        openai_api_key_set=bool(api_settings.get('openai_api_key')),
        anthropic_api_key_set=bool(api_settings.get('anthropic_api_key')),
        default_llm_provider=api_settings.get('default_llm_provider'),
        default_llm_model=api_settings.get('default_llm_model'),
        message="API settings retrieved successfully"
    )


@router.put("/api-settings", response_model=APISettingsResponse)
async def update_user_api_settings(
    settings: UpdateAPISettingsRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    updateuser的 API set
    
    allowuserconfig自己的 API keyand默认 LLM provide者
    """
    # getuserinfo
    result = await db.execute(
        select(User).filter(User.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # get现有的 metadata
    metadata = user.metadata or {}
    api_settings = metadata.get('api_settings', {})
    
    # update API set
    if settings.openrouter_api_key is not None:
        if settings.openrouter_api_key.strip():
            api_settings['openrouter_api_key'] = settings.openrouter_api_key.strip()
        else:
            api_settings.pop('openrouter_api_key', None)
    
    if settings.openai_api_key is not None:
        if settings.openai_api_key.strip():
            api_settings['openai_api_key'] = settings.openai_api_key.strip()
        else:
            api_settings.pop('openai_api_key', None)
    
    if settings.anthropic_api_key is not None:
        if settings.anthropic_api_key.strip():
            api_settings['anthropic_api_key'] = settings.anthropic_api_key.strip()
        else:
            api_settings.pop('anthropic_api_key', None)
    
    if settings.default_llm_provider is not None:
        if settings.default_llm_provider.strip():
            api_settings['default_llm_provider'] = settings.default_llm_provider.strip()
        else:
            api_settings.pop('default_llm_provider', None)
    
    if settings.default_llm_model is not None:
        if settings.default_llm_model.strip():
            api_settings['default_llm_model'] = settings.default_llm_model.strip()
        else:
            api_settings.pop('default_llm_model', None)
    
    # update metadata
    metadata['api_settings'] = api_settings
    metadata['updated_at'] = datetime.utcnow().isoformat()
    
    # save到database
    await db.execute(
        update(User)
        .where(User.id == current_user.user_id)
        .values(metadata=metadata)
    )
    await db.commit()
    
    return APISettingsResponse(
        openrouter_api_key_set=bool(api_settings.get('openrouter_api_key')),
        openai_api_key_set=bool(api_settings.get('openai_api_key')),
        anthropic_api_key_set=bool(api_settings.get('anthropic_api_key')),
        default_llm_provider=api_settings.get('default_llm_provider'),
        default_llm_model=api_settings.get('default_llm_model'),
        message="API settings updated successfully"
    )


@router.delete("/api-settings/{provider}", response_model=APISettingsResponse)
async def delete_user_api_key(
    provider: str,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    delete指定provide者的 API key
    
    provider: openrouter, openai, anthropic
    """
    if provider not in ['openrouter', 'openai', 'anthropic']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Must be one of: openrouter, openai, anthropic"
        )
    
    # getuserinfo
    result = await db.execute(
        select(User).filter(User.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # get现有的 metadata
    metadata = user.metadata or {}
    api_settings = metadata.get('api_settings', {})
    
    # delete指定的 API key
    key_name = f'{provider}_api_key'
    api_settings.pop(key_name, None)
    
    # update metadata
    metadata['api_settings'] = api_settings
    metadata['updated_at'] = datetime.utcnow().isoformat()
    
    # save到database
    await db.execute(
        update(User)
        .where(User.id == current_user.user_id)
        .values(metadata=metadata)
    )
    await db.commit()
    
    return APISettingsResponse(
        openrouter_api_key_set=bool(api_settings.get('openrouter_api_key')),
        openai_api_key_set=bool(api_settings.get('openai_api_key')),
        anthropic_api_key_set=bool(api_settings.get('anthropic_api_key')),
        default_llm_provider=api_settings.get('default_llm_provider'),
        default_llm_model=api_settings.get('default_llm_model'),
        message=f"{provider.capitalize()} API key deleted successfully"
    )
