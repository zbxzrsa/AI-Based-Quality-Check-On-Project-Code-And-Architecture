"""
user LLM service

根据userconfig动态选择 LLM provide者and API key
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.auth import User
from app.services.llm.factory import LLMProviderFactory
from app.services.llm.base import BaseLLMProvider, LLMProviderType

logger = logging.getLogger(__name__)


class UserLLMService:
    """
    user LLM service
    
    根据userconfig动态create LLM providerInstance
    优先级：userconfig > system默认config
    """
    
    @staticmethod
    async def get_user_llm_provider(
        db: AsyncSession,
        user_id: str,
        provider_type: Optional[str] = None,
        model: Optional[str] = None
    ) -> BaseLLMProvider:
        """
        getuser的 LLM providerInstance
        
        Args:
            db: dbSession
            user_id: user ID
            provider_type: 可选的provide者type，如果未指定则useuser默认config
            model: 可选的模型名称，如果未指定则useuser默认config
            
        Returns:
            config好的 LLM providerInstance
        """
        # getuserinfo
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User {user_id} not found, using system default LLM provider")
            return UserLLMService._get_system_default_provider(provider_type, model)
        
        # getuser的 API set
        metadata = user.metadata or {}
        api_settings = metadata.get('api_settings', {})
        
        # 确定use的provide者type
        if not provider_type:
            provider_type = api_settings.get('default_llm_provider') or settings.DEFAULT_LLM_PROVIDER
        
        # 确定use的模型
        if not model:
            model = api_settings.get('default_llm_model') or settings.DEFAULT_LLM_MODEL
        
        # getuserconfig的 API key
        user_api_key = None
        if provider_type == 'openrouter':
            user_api_key = api_settings.get('openrouter_api_key')
        elif provider_type == 'openai':
            user_api_key = api_settings.get('openai_api_key')
        elif provider_type == 'anthropic':
            user_api_key = api_settings.get('anthropic_api_key')
        
        # 如果user有config API key，useuser的key
        if user_api_key:
            logger.info(
                f"Using user-configured API key for {provider_type}",
                extra={"user_id": user_id, "provider": provider_type}
            )
            return UserLLMService._create_provider_with_key(
                provider_type, model, user_api_key
            )
        
        # 否则usesystem默认config
        logger.info(
            f"Using system default API key for {provider_type}",
            extra={"user_id": user_id, "provider": provider_type}
        )
        return UserLLMService._get_system_default_provider(provider_type, model)
    
    @staticmethod
    def _create_provider_with_key(
        provider_type: str,
        model: str,
        api_key: str
    ) -> BaseLLMProvider:
        """
        use指定的 API keycreateproviderInstance
        
        Args:
            provider_type: provide者type
            model: 模型名称
            api_key: API key
            
        Returns:
            LLM providerInstance
        """
        # 转换provide者type
        provider_enum = {
            'openrouter': LLMProviderType.OPENROUTER,
            'openai': LLMProviderType.OPENAI,
            'anthropic': LLMProviderType.ANTHROPIC,
        }.get(provider_type.lower())
        
        if not provider_enum:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        # createproviderInstance（不usecache，因为每itemuser的key不同）
        return LLMProviderFactory.create_provider(
            provider_type=provider_enum,
            model=model,
            api_key=api_key
        )
    
    @staticmethod
    def _get_system_default_provider(
        provider_type: Optional[str] = None,
        model: Optional[str] = None
    ) -> BaseLLMProvider:
        """
        getsystem默认的 LLM provide者
        
        Args:
            provider_type: 可选的provide者type
            model: 可选的模型名称
            
        Returns:
            LLM providerInstance
        """
        provider_type = provider_type or settings.DEFAULT_LLM_PROVIDER
        model = model or settings.DEFAULT_LLM_MODEL
        
        # 转换provide者type
        provider_enum = {
            'openrouter': LLMProviderType.OPENROUTER,
            'openai': LLMProviderType.OPENAI,
            'anthropic': LLMProviderType.ANTHROPIC,
        }.get(provider_type.lower())
        
        if not provider_enum:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        # use工厂createprovide者（usesystemconfig的 API key）
        return LLMProviderFactory.get_provider(
            provider_type=provider_enum,
            model=model
        )
    
    @staticmethod
    async def get_user_api_settings(
        db: AsyncSession,
        user_id: str
    ) -> dict:
        """
        getuser的 API set
        
        Args:
            db: dbSession
            user_id: user ID
            
        Returns:
            user的 API set字典
        """
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {}
        
        metadata = user.metadata or {}
        return metadata.get('api_settings', {})
