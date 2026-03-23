"""
统一的审计服务 - 合并所有审计日志功能
处理认证、授权和通用用户操作的审计日志记录
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Union, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

from app.models import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class AuditFilter:
    """审计日志查询过滤器"""
    def __init__(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success: Optional[bool] = None,
        ip_address: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ):
        self.user_id = user_id
        self.action = action
        self.entity_type = entity_type
        self.start_date = start_date
        self.end_date = end_date
        self.success = success
        self.ip_address = ip_address
        self.limit = limit
        self.offset = offset


class UnifiedAuditService:
    """统一的审计服务类"""
    
    @staticmethod
    async def log_action(
        db: AsyncSession,
        user_id: Optional[Union[str, uuid.UUID]],
        action: Union[str, AuditAction],
        entity_type: str,
        entity_id: Optional[Union[str, uuid.UUID]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        changes: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        记录用户操作到审计日志
        
        Args:
            db: 异步数据库会话
            user_id: 用户ID
            action: 操作类型
            entity_type: 实体类型
            entity_id: 实体ID
            ip_address: 客户端IP地址
            user_agent: 用户代理字符串
            success: 操作是否成功
            changes: 变更详情
            error_message: 错误消息（如果失败）
            username: 用户名（向后兼容）
            resource_type: 资源类型（向后兼容）
            resource_id: 资源ID（向后兼容）
            
        Returns:
            创建的审计日志条目，失败时返回None
        """
        try:
            # 处理向后兼容性
            if resource_type and not entity_type:
                entity_type = resource_type
            if resource_id and not entity_id:
                entity_id = resource_id
            
            # 确保UUID格式
            if user_id and isinstance(user_id, str):
                try:
                    user_id = uuid.UUID(user_id)
                except ValueError:
                    # 如果不是有效的UUID，保持为字符串
                    pass
            
            if entity_id and isinstance(entity_id, str):
                try:
                    entity_id = uuid.UUID(entity_id)
                except ValueError:
                    entity_id = uuid.uuid4()  # 生成新的UUID
            elif not entity_id:
                entity_id = uuid.uuid4()
            
            # 构建变更记录
            if not changes:
                changes = {}
            
            if username:
                changes['username'] = username
            if error_message:
                changes['error_message'] = error_message
            
            changes['timestamp'] = datetime.now(timezone.utc).isoformat()
            changes['success'] = success
            
            # 创建审计日志条目
            audit_entry = AuditLog(
                id=uuid.uuid4(),
                user_id=user_id,
                action=action if isinstance(action, AuditAction) else AuditAction.create,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.now(timezone.utc)
            )
            
            db.add(audit_entry)
            await db.commit()
            await db.refresh(audit_entry)
            
            # 记录到结构化日志
            logger.info(
                f"Audit log created: {action} on {entity_type}",
                extra={
                    "audit_id": str(audit_entry.id),
                    "user_id": str(user_id) if user_id else None,
                    "action": str(action),
                    "entity_type": entity_type,
                    "entity_id": str(entity_id),
                    "success": success,
                    "ip_address": ip_address,
                    "timestamp": audit_entry.timestamp.isoformat()
                }
            )
            
            return audit_entry
            
        except Exception as e:
            logger.error(
                f"Failed to create audit log: {e}",
                extra={
                    "user_id": str(user_id) if user_id else None,
                    "action": str(action),
                    "entity_type": entity_type,
                    "error": str(e)
                }
            )
            try:
                await db.rollback()
            except Exception:
                pass
            return None
    
    @staticmethod
    async def log_auth_failure(
        db: AsyncSession,
        email: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        failure_reason: str = "Invalid credentials",
        user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        记录认证失败尝试
        
        Args:
            db: 数据库会话
            email: 尝试的邮箱/用户名
            ip_address: 客户端IP地址
            user_agent: 用户代理字符串
            failure_reason: 失败原因
            user_id: 用户ID（如果用户存在）
        """
        await UnifiedAuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.create,
            entity_type="authentication_failure",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            changes={
                "email": email,
                "failure_reason": failure_reason
            }
        )
        
        # 额外的结构化日志记录
        logger.warning(
            "Authentication failure",
            extra={
                "event_type": "auth_failure",
                "email": email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "failure_reason": failure_reason,
                "user_id": str(user_id) if user_id else None
            }
        )
    
    @staticmethod
    async def log_authz_failure(
        db: AsyncSession,
        user_id: uuid.UUID,
        email: str,
        resource_type: str,
        resource_id: Optional[str],
        ip_address: str,
        user_agent: Optional[str] = None,
        required_permission: Optional[str] = None
    ) -> None:
        """
        记录授权失败尝试（403错误）
        
        Args:
            db: 数据库会话
            user_id: 尝试访问的用户ID
            email: 用户邮箱
            resource_type: 被访问的资源类型
            resource_id: 被访问的资源ID
            ip_address: 客户端IP地址
            user_agent: 用户代理字符串
            required_permission: 所需权限
        """
        await UnifiedAuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.create,
            entity_type="authorization_failure",
            entity_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            changes={
                "email": email,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "required_permission": required_permission
            }
        )
        
        # 额外的结构化日志记录
        logger.warning(
            "Authorization failure",
            extra={
                "event_type": "authz_failure",
                "user_id": str(user_id),
                "email": email,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "required_permission": required_permission,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )
    
    @staticmethod
    async def log_token_refresh_failure(
        db: AsyncSession,
        user_id: Optional[uuid.UUID],
        ip_address: str,
        user_agent: Optional[str] = None,
        failure_reason: str = "Invalid or expired token"
    ) -> None:
        """
        记录令牌刷新失败尝试
        
        Args:
            db: 数据库会话
            user_id: 用户ID（如果令牌可以解码）
            ip_address: 客户端IP地址
            user_agent: 用户代理字符串
            failure_reason: 失败原因
        """
        await UnifiedAuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.create,
            entity_type="token_refresh_failure",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            changes={
                "failure_reason": failure_reason
            }
        )
        
        # 额外的结构化日志记录
        logger.warning(
            "Token refresh failure",
            extra={
                "event_type": "token_refresh_failure",
                "user_id": str(user_id) if user_id else None,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "failure_reason": failure_reason
            }
        )
    
    @staticmethod
    async def query_logs(
        db: AsyncSession,
        filter: AuditFilter
    ) -> List[AuditLog]:
        """
        查询审计日志
        
        Args:
            db: 数据库会话
            filter: 过滤条件
            
        Returns:
            匹配的审计日志条目列表
        """
        try:
            # 构建查询
            stmt = select(AuditLog)
            conditions = []
            
            if filter.user_id:
                if isinstance(filter.user_id, str):
                    try:
                        user_uuid = uuid.UUID(filter.user_id)
                        conditions.append(AuditLog.user_id == user_uuid)
                    except ValueError:
                        # 如果不是有效UUID，跳过此条件
                        pass
                else:
                    conditions.append(AuditLog.user_id == filter.user_id)
            
            if filter.action:
                conditions.append(AuditLog.action == filter.action)
            
            if filter.entity_type:
                conditions.append(AuditLog.entity_type == filter.entity_type)
            
            if filter.start_date:
                conditions.append(AuditLog.timestamp >= filter.start_date)
            
            if filter.end_date:
                conditions.append(AuditLog.timestamp <= filter.end_date)
            
            if filter.ip_address:
                conditions.append(AuditLog.ip_address == filter.ip_address)
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            # 按时间戳降序排列（最新的在前）
            stmt = stmt.order_by(AuditLog.timestamp.desc())
            
            # 应用分页
            stmt = stmt.offset(filter.offset).limit(filter.limit)
            
            result = await db.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return []
    
    @staticmethod
    async def get_user_logs(
        db: AsyncSession,
        user_id: Union[str, uuid.UUID],
        limit: int = 100
    ) -> List[AuditLog]:
        """
        获取特定用户的审计日志
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 返回的最大日志数量
            
        Returns:
            用户的审计日志条目列表
        """
        filter = AuditFilter(user_id=str(user_id), limit=limit)
        return await UnifiedAuditService.query_logs(db, filter)
    
    @staticmethod
    async def get_failed_attempts(
        db: AsyncSession,
        ip_address: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        获取失败的认证/授权尝试
        
        Args:
            db: 数据库会话
            ip_address: 可选的IP地址过滤
            hours: 查询过去多少小时的记录
            limit: 返回的最大日志数量
            
        Returns:
            失败尝试的审计日志列表
        """
        start_date = datetime.now(timezone.utc) - timezone.timedelta(hours=hours)
        
        try:
            stmt = select(AuditLog).where(
                and_(
                    AuditLog.timestamp >= start_date,
                    AuditLog.entity_type.in_([
                        "authentication_failure",
                        "authorization_failure",
                        "token_refresh_failure"
                    ])
                )
            )
            
            if ip_address:
                stmt = stmt.where(AuditLog.ip_address == ip_address)
            
            stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit)
            
            result = await db.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get failed attempts: {e}")
            return []


# 向后兼容的别名
AuditService = UnifiedAuditService