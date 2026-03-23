"""
通用CRUD基类 - 消除跨实体的重复操作

提供标准化的CRUD操作模式，包括：
- UUID验证
- 所有权检查
- 分页查询
- 错误处理
- 审计日志记录
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.audit_service import UnifiedAuditService

logger = get_logger(__name__)

# 泛型类型变量
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class ValidationError(Exception):
    """验证错误异常"""
    pass


class PermissionError(Exception):
    """权限错误异常"""
    pass


class BaseCRUDService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType], ABC):
    """
    通用CRUD服务基类
    
    提供标准化的CRUD操作，子类只需实现特定的业务逻辑
    """
    
    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model
        self.audit_service = UnifiedAuditService()
    
    @property
    @abstractmethod
    def entity_name(self) -> str:
        """实体名称，用于日志和错误消息"""
        pass
    
    @property
    @abstractmethod
    def owner_field(self) -> str:
        """所有者字段名称，用于权限检查"""
        pass
    
    def validate_uuid(self, uuid_str: str, field_name: str = "ID") -> UUID:
        """
        验证UUID格式
        
        Args:
            uuid_str: UUID字符串
            field_name: 字段名称，用于错误消息
            
        Returns:
            验证后的UUID对象
            
        Raises:
            HTTPException: UUID格式无效
        """
        try:
            return UUID(uuid_str)
        except ValueError:
            logger.warning(f"Invalid {field_name} format: {uuid_str}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name} format"
            )
    
    async def check_ownership(
        self, 
        entity: ModelType, 
        user_id: str,
        action: str = "access"
    ) -> None:
        """
        检查实体所有权
        
        Args:
            entity: 实体对象
            user_id: 用户ID
            action: 操作类型，用于错误消息
            
        Raises:
            HTTPException: 权限不足
        """
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.entity_name} not found"
            )
        
        owner_id = getattr(entity, self.owner_field, None)
        if owner_id != user_id:
            logger.warning(
                f"Permission denied: User {user_id} attempted to {action} "
                f"{self.entity_name} owned by {owner_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to {action} this {self.entity_name.lower()}"
            )
    
    async def get_by_id(
        self, 
        entity_id: str, 
        user_id: str,
        check_ownership: bool = True
    ) -> ModelType:
        """
        根据ID获取实体
        
        Args:
            entity_id: 实体ID
            user_id: 用户ID
            check_ownership: 是否检查所有权
            
        Returns:
            实体对象
        """
        entity_uuid = self.validate_uuid(entity_id, f"{self.entity_name} ID")
        
        result = await self.db.execute(
            select(self.model).where(self.model.id == entity_uuid)
        )
        entity = result.scalar_one_or_none()
        
        if check_ownership:
            await self.check_ownership(entity, user_id, "access")
        elif not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.entity_name} not found"
            )
        
        return entity
    
    async def list_entities(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        include_all: bool = False
    ) -> Dict[str, Any]:
        """
        分页列表查询
        
        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页大小
            filters: 额外过滤条件
            include_all: 是否包含所有记录（管理员权限）
            
        Returns:
            包含实体列表和分页信息的字典
        """
        # 构建基础查询
        query = select(self.model)
        
        # 应用所有权过滤（除非是管理员查看所有记录）
        if not include_all:
            query = query.where(getattr(self.model, self.owner_field) == user_id)
        
        # 应用额外过滤条件
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)
        
        # 按创建时间降序排列
        if hasattr(self.model, 'created_at'):
            query = query.order_by(self.model.created_at.desc())
        
        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 应用分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # 执行查询
        result = await self.db.execute(query)
        entities = result.scalars().all()
        
        logger.info(
            f"Listed {len(entities)} {self.entity_name.lower()}s "
            f"(page {page}/{(total + page_size - 1) // page_size}) for user {user_id}"
        )
        
        return {
            "items": list(entities),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    async def create_entity(
        self,
        create_data: CreateSchemaType,
        user_id: str,
        **kwargs
    ) -> ModelType:
        """
        创建实体
        
        Args:
            create_data: 创建数据
            user_id: 用户ID
            **kwargs: 额外参数
            
        Returns:
            创建的实体
        """
        try:
            # 调用子类的验证逻辑
            await self.validate_create_data(create_data, user_id)
            
            # 准备创建数据
            create_dict = create_data.dict(exclude_unset=True)
            create_dict[self.owner_field] = user_id
            create_dict['id'] = uuid4()
            
            if hasattr(self.model, 'created_at'):
                create_dict['created_at'] = datetime.now(timezone.utc)
            if hasattr(self.model, 'updated_at'):
                create_dict['updated_at'] = datetime.now(timezone.utc)
            
            # 调用子类的预处理逻辑
            create_dict = await self.preprocess_create_data(create_dict, user_id, **kwargs)
            
            # 创建实体
            entity = self.model(**create_dict)
            self.db.add(entity)
            await self.db.commit()
            await self.db.refresh(entity)
            
            # 记录审计日志
            await self.audit_service.log_action(
                db=self.db,
                user_id=user_id,
                action="create",
                entity_type=self.entity_name.lower(),
                entity_id=str(entity.id),
                success=True,
                changes={"created": create_dict}
            )
            
            logger.info(f"Created {self.entity_name.lower()} {entity.id} by user {user_id}")
            return entity
            
        except ValidationError as e:
            logger.warning(f"{self.entity_name} creation validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error creating {self.entity_name.lower()}: {e}")
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {self.entity_name.lower()}"
            )
    
    async def update_entity(
        self,
        entity_id: str,
        update_data: UpdateSchemaType,
        user_id: str,
        **kwargs
    ) -> ModelType:
        """
        更新实体
        
        Args:
            entity_id: 实体ID
            update_data: 更新数据
            user_id: 用户ID
            **kwargs: 额外参数
            
        Returns:
            更新后的实体
        """
        try:
            # 获取并检查权限
            entity = await self.get_by_id(entity_id, user_id, check_ownership=True)
            
            # 记录原始状态
            original_state = {
                field: getattr(entity, field) 
                for field in update_data.dict(exclude_unset=True).keys()
                if hasattr(entity, field)
            }
            
            # 调用子类的验证逻辑
            await self.validate_update_data(update_data, entity, user_id)
            
            # 准备更新数据
            update_dict = update_data.dict(exclude_unset=True)
            update_dict = await self.preprocess_update_data(update_dict, entity, user_id, **kwargs)
            
            # 更新字段
            for field, value in update_dict.items():
                if hasattr(entity, field):
                    setattr(entity, field, value)
            
            # 更新时间戳
            if hasattr(entity, 'updated_at'):
                entity.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            await self.db.refresh(entity)
            
            # 记录审计日志
            await self.audit_service.log_action(
                db=self.db,
                user_id=user_id,
                action="update",
                entity_type=self.entity_name.lower(),
                entity_id=entity_id,
                success=True,
                changes={
                    "original": original_state,
                    "updated": update_dict
                }
            )
            
            logger.info(f"Updated {self.entity_name.lower()} {entity_id} by user {user_id}")
            return entity
            
        except ValidationError as e:
            logger.warning(f"{self.entity_name} update validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating {self.entity_name.lower()}: {e}")
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {self.entity_name.lower()}"
            )
    
    async def delete_entity(
        self,
        entity_id: str,
        user_id: str,
        soft_delete: bool = True,
        **kwargs
    ) -> None:
        """
        删除实体
        
        Args:
            entity_id: 实体ID
            user_id: 用户ID
            soft_delete: 是否软删除
            **kwargs: 额外参数
        """
        try:
            # 获取并检查权限
            entity = await self.get_by_id(entity_id, user_id, check_ownership=True)
            
            # 调用子类的删除前验证
            await self.validate_delete(entity, user_id)
            
            if soft_delete and hasattr(entity, 'status'):
                # 软删除：设置状态为archived
                entity.status = "archived"
                if hasattr(entity, 'updated_at'):
                    entity.updated_at = datetime.now(timezone.utc)
                await self.db.commit()
                action = "archive"
            else:
                # 硬删除
                await self.db.delete(entity)
                await self.db.commit()
                action = "delete"
            
            # 记录审计日志
            await self.audit_service.log_action(
                db=self.db,
                user_id=user_id,
                action=action,
                entity_type=self.entity_name.lower(),
                entity_id=entity_id,
                success=True,
                changes={"action": action}
            )
            
            logger.info(f"{action.capitalize()}d {self.entity_name.lower()} {entity_id} by user {user_id}")
            
        except ValidationError as e:
            logger.warning(f"{self.entity_name} deletion validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting {self.entity_name.lower()}: {e}")
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {self.entity_name.lower()}"
            )
    
    # 抽象方法 - 子类必须实现
    @abstractmethod
    async def validate_create_data(self, create_data: CreateSchemaType, user_id: str) -> None:
        """验证创建数据"""
        pass
    
    @abstractmethod
    async def validate_update_data(self, update_data: UpdateSchemaType, entity: ModelType, user_id: str) -> None:
        """验证更新数据"""
        pass
    
    @abstractmethod
    async def validate_delete(self, entity: ModelType, user_id: str) -> None:
        """验证删除操作"""
        pass
    
    # 可选的钩子方法 - 子类可以重写
    async def preprocess_create_data(self, create_dict: Dict[str, Any], user_id: str, **kwargs) -> Dict[str, Any]:
        """预处理创建数据"""
        return create_dict
    
    async def preprocess_update_data(self, update_dict: Dict[str, Any], entity: ModelType, user_id: str, **kwargs) -> Dict[str, Any]:
        """预处理更新数据"""
        return update_dict


class BaseEndpoint(ABC):
    """
    通用端点基类
    
    提供标准化的HTTP端点处理，包括错误处理和响应格式化
    """
    
    def __init__(self, service: BaseCRUDService):
        self.service = service
    
    def handle_error(self, e: Exception, operation: str) -> HTTPException:
        """
        统一错误处理
        
        Args:
            e: 异常对象
            operation: 操作名称
            
        Returns:
            格式化的HTTP异常
        """
        if isinstance(e, HTTPException):
            return e
        elif isinstance(e, ValidationError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        elif isinstance(e, PermissionError):
            return HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        else:
            logger.error(f"Unexpected error in {operation}: {e}")
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to {operation}"
            )