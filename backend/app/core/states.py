"""
状态模式实现 - 统一处理状态管理和状态转换逻辑

包含以下状态机：
1. ProjectInvitation状态机
2. Repository状态机
3. 通用状态机基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Type
from datetime import datetime, timezone
from enum import Enum
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# 状态机基类
# ============================================================================

class State(ABC):
    """状态基类"""
    
    def __init__(self, context: 'StateMachine'):
        self.context = context
    
    @abstractmethod
    def get_state_name(self) -> str:
        """获取状态名称"""
        pass
    
    @abstractmethod
    def get_allowed_transitions(self) -> Set[str]:
        """获取允许的状态转换"""
        pass
    
    @abstractmethod
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        """检查是否可以转换到新状态"""
        pass
    
    @abstractmethod
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入状态时的操作"""
        pass
    
    @abstractmethod
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        """退出状态时的操作"""
        pass
    
    async def handle_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """处理状态相关的操作"""
        method_name = f"handle_{action}"
        if hasattr(self, method_name):
            return await getattr(self, method_name)(**kwargs)
        else:
            return {
                "success": False,
                "error": f"Action '{action}' not supported in state '{self.get_state_name()}'"
            }


class StateMachine(ABC):
    """状态机基类"""
    
    def __init__(self, db: AsyncSession, entity: Any):
        self.db = db
        self.entity = entity
        self.current_state: Optional[State] = None
        self.states: Dict[str, Type[State]] = {}
        self._initialize_states()
        self._set_current_state()
    
    @abstractmethod
    def _initialize_states(self) -> None:
        """初始化状态映射"""
        pass
    
    @abstractmethod
    def _get_entity_state(self) -> str:
        """获取实体当前状态"""
        pass
    
    @abstractmethod
    async def _update_entity_state(self, new_state: str) -> None:
        """更新实体状态"""
        pass
    
    def _set_current_state(self) -> None:
        """设置当前状态"""
        current_state_name = self._get_entity_state()
        state_class = self.states.get(current_state_name)
        
        if state_class:
            self.current_state = state_class(self)
        else:
            raise ValueError(f"Unknown state: {current_state_name}")
    
    async def transition_to(self, new_state: str, **kwargs) -> Dict[str, Any]:
        """
        状态转换
        
        Args:
            new_state: 新状态名称
            **kwargs: 转换参数
            
        Returns:
            转换结果
        """
        if not self.current_state:
            return {"success": False, "error": "No current state set"}
        
        old_state_name = self.current_state.get_state_name()
        
        try:
            # 检查是否允许转换
            can_transition, reason = await self.current_state.can_transition_to(new_state, **kwargs)
            if not can_transition:
                return {"success": False, "error": reason}
            
            # 执行退出操作
            exit_result = await self.current_state.on_exit(**kwargs)
            if not exit_result.get("success", True):
                return {"success": False, "error": f"Exit failed: {exit_result.get('error')}"}
            
            # 更新实体状态
            await self._update_entity_state(new_state)
            
            # 切换到新状态
            new_state_class = self.states.get(new_state)
            if not new_state_class:
                return {"success": False, "error": f"Unknown state: {new_state}"}
            
            self.current_state = new_state_class(self)
            
            # 执行进入操作
            enter_result = await self.current_state.on_enter(**kwargs)
            if not enter_result.get("success", True):
                logger.warning(f"Enter operation failed for state {new_state}: {enter_result.get('error')}")
            
            logger.info(f"State transition completed: {old_state_name} -> {new_state}")
            
            return {
                "success": True,
                "old_state": old_state_name,
                "new_state": new_state,
                "entity": self.entity
            }
            
        except Exception as e:
            logger.error(f"State transition failed: {old_state_name} -> {new_state}: {e}")
            await self.db.rollback()
            return {"success": False, "error": f"Transition failed: {str(e)}"}
    
    async def handle_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """处理操作"""
        if not self.current_state:
            return {"success": False, "error": "No current state set"}
        
        return await self.current_state.handle_action(action, **kwargs)
    
    def get_current_state_name(self) -> str:
        """获取当前状态名称"""
        return self.current_state.get_state_name() if self.current_state else "unknown"
    
    def get_allowed_transitions(self) -> Set[str]:
        """获取当前状态允许的转换"""
        return self.current_state.get_allowed_transitions() if self.current_state else set()


# ============================================================================
# ProjectInvitation状态机
# ============================================================================

class InvitationState(State):
    """邀请状态基类"""
    
    async def log_state_action(self, action: str, success: bool, **kwargs) -> None:
        """记录状态操作日志"""
        from app.core.audit_service import UnifiedAuditService
        
        user_id = kwargs.get("user_id")
        if user_id:
            await UnifiedAuditService.log_action(
                db=self.context.db,
                user_id=user_id,
                action=action,
                entity_type="invitation",
                entity_id=str(self.context.entity.id),
                success=success,
                changes={
                    "state": self.get_state_name(),
                    "action": action,
                    **kwargs
                }
            )


class PendingInvitationState(InvitationState):
    """待处理邀请状态"""
    
    def get_state_name(self) -> str:
        return "pending"
    
    def get_allowed_transitions(self) -> Set[str]:
        return {"accepted", "declined", "expired"}
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        """检查转换条件"""
        invitation = self.context.entity
        
        # 检查邀请是否过期
        if invitation.is_expired():
            if new_state != "expired":
                return False, "Invitation has expired"
        
        # 检查用户权限
        if new_state in ["accepted", "declined"]:
            user_email = kwargs.get("user_email")
            if user_email != invitation.invitee_email:
                return False, "Only the invitee can accept or decline the invitation"
        
        return True, ""
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入待处理状态"""
        logger.info(f"Invitation {self.context.entity.id} is now pending")
        return {"success": True}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        """退出待处理状态"""
        return {"success": True}
    
    async def handle_accept(self, **kwargs) -> Dict[str, Any]:
        """处理接受操作"""
        user_id = kwargs.get("user_id")
        if not user_id:
            return {"success": False, "error": "User ID required"}
        
        # 检查用户是否已经是项目成员
        from app.models import ProjectMember
        from sqlalchemy import select
        
        existing_member = await self.context.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == self.context.entity.project_id,
                ProjectMember.user_id == user_id
            )
        )
        
        if existing_member.scalar_one_or_none():
            return {"success": False, "error": "User is already a member of this project"}
        
        # 转换到已接受状态
        return await self.context.transition_to("accepted", **kwargs)
    
    async def handle_decline(self, **kwargs) -> Dict[str, Any]:
        """处理拒绝操作"""
        return await self.context.transition_to("declined", **kwargs)
    
    async def handle_expire(self, **kwargs) -> Dict[str, Any]:
        """处理过期操作"""
        return await self.context.transition_to("expired", **kwargs)


class AcceptedInvitationState(InvitationState):
    """已接受邀请状态"""
    
    def get_state_name(self) -> str:
        return "accepted"
    
    def get_allowed_transitions(self) -> Set[str]:
        return set()  # 已接受的邀请不能再转换
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return False, "Accepted invitations cannot be changed"
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入已接受状态 - 创建项目成员"""
        try:
            from app.models import ProjectMember
            
            user_id = kwargs.get("user_id")
            invitation = self.context.entity
            
            # 创建项目成员记录
            member = ProjectMember(
                project_id=invitation.project_id,
                user_id=user_id,
                role=invitation.role
            )
            
            self.context.db.add(member)
            
            # 更新邀请信息
            invitation.accepted_at = datetime.now(timezone.utc)
            invitation.invitee_id = user_id
            
            await self.context.db.commit()
            
            await self.log_state_action("accept", True, **kwargs)
            
            logger.info(f"Created project membership for invitation {invitation.id}")
            return {"success": True, "member": member}
            
        except Exception as e:
            logger.error(f"Failed to create project membership: {e}")
            await self.context.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}


class DeclinedInvitationState(InvitationState):
    """已拒绝邀请状态"""
    
    def get_state_name(self) -> str:
        return "declined"
    
    def get_allowed_transitions(self) -> Set[str]:
        return set()  # 已拒绝的邀请不能再转换
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return False, "Declined invitations cannot be changed"
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入已拒绝状态"""
        user_id = kwargs.get("user_id")
        invitation = self.context.entity
        
        invitation.invitee_id = user_id
        await self.context.db.commit()
        
        await self.log_state_action("decline", True, **kwargs)
        
        logger.info(f"Invitation {invitation.id} declined by user {user_id}")
        return {"success": True}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}


class ExpiredInvitationState(InvitationState):
    """已过期邀请状态"""
    
    def get_state_name(self) -> str:
        return "expired"
    
    def get_allowed_transitions(self) -> Set[str]:
        return set()  # 已过期的邀请不能再转换
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return False, "Expired invitations cannot be changed"
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入已过期状态"""
        await self.context.db.commit()
        
        await self.log_state_action("expire", True, **kwargs)
        
        logger.info(f"Invitation {self.context.entity.id} expired")
        return {"success": True}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}


class InvitationStateMachine(StateMachine):
    """邀请状态机"""
    
    def _initialize_states(self) -> None:
        """初始化状态映射"""
        self.states = {
            "pending": PendingInvitationState,
            "accepted": AcceptedInvitationState,
            "declined": DeclinedInvitationState,
            "expired": ExpiredInvitationState
        }
    
    def _get_entity_state(self) -> str:
        """获取邀请当前状态"""
        return self.entity.status
    
    async def _update_entity_state(self, new_state: str) -> None:
        """更新邀请状态"""
        self.entity.status = new_state


# ============================================================================
# Repository状态机
# ============================================================================

class RepositoryState(State):
    """仓库状态基类"""
    
    async def log_state_action(self, action: str, success: bool, **kwargs) -> None:
        """记录状态操作日志"""
        from app.core.audit_service import UnifiedAuditService
        
        user_id = kwargs.get("user_id")
        if user_id:
            await UnifiedAuditService.log_action(
                db=self.context.db,
                user_id=user_id,
                action=action,
                entity_type="repository",
                entity_id=str(self.context.entity.id),
                success=success,
                changes={
                    "state": self.get_state_name(),
                    "action": action,
                    **kwargs
                }
            )


class PendingRepositoryState(RepositoryState):
    """待处理仓库状态"""
    
    def get_state_name(self) -> str:
        return "pending"
    
    def get_allowed_transitions(self) -> Set[str]:
        return {"validating", "failed"}
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return True, ""
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入待处理状态"""
        logger.info(f"Repository {self.context.entity.id} is now pending")
        return {"success": True}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}
    
    async def handle_validate(self, **kwargs) -> Dict[str, Any]:
        """处理验证操作"""
        return await self.context.transition_to("validating", **kwargs)


class ValidatingRepositoryState(RepositoryState):
    """验证中仓库状态"""
    
    def get_state_name(self) -> str:
        return "validating"
    
    def get_allowed_transitions(self) -> Set[str]:
        return {"cloning", "failed"}
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return True, ""
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入验证状态 - 开始验证仓库"""
        try:
            # 这里可以触发异步验证任务
            logger.info(f"Starting validation for repository {self.context.entity.id}")
            
            # 模拟验证逻辑
            validation_result = kwargs.get("validation_result", {"valid": True})
            
            if validation_result.get("valid"):
                # 验证成功，准备克隆
                await asyncio.create_task(self._schedule_clone())
            else:
                # 验证失败
                await self.context.transition_to("failed", error=validation_result.get("error"))
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Validation failed for repository {self.context.entity.id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}
    
    async def _schedule_clone(self) -> None:
        """安排克隆任务"""
        # 模拟异步克隆任务
        await asyncio.sleep(0.1)  # 模拟延迟
        await self.context.transition_to("cloning")


class CloningRepositoryState(RepositoryState):
    """克隆中仓库状态"""
    
    def get_state_name(self) -> str:
        return "cloning"
    
    def get_allowed_transitions(self) -> Set[str]:
        return {"analyzing", "failed"}
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return True, ""
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入克隆状态"""
        logger.info(f"Starting clone for repository {self.context.entity.id}")
        
        # 模拟克隆过程
        clone_result = kwargs.get("clone_result", {"success": True})
        
        if clone_result.get("success"):
            await self._schedule_analysis()
        else:
            await self.context.transition_to("failed", error=clone_result.get("error"))
        
        return {"success": True}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}
    
    async def _schedule_analysis(self) -> None:
        """安排分析任务"""
        await asyncio.sleep(0.1)  # 模拟延迟
        await self.context.transition_to("analyzing")


class AnalyzingRepositoryState(RepositoryState):
    """分析中仓库状态"""
    
    def get_state_name(self) -> str:
        return "analyzing"
    
    def get_allowed_transitions(self) -> Set[str]:
        return {"active", "failed"}
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return True, ""
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入分析状态"""
        logger.info(f"Starting analysis for repository {self.context.entity.id}")
        
        # 模拟分析过程
        analysis_result = kwargs.get("analysis_result", {"success": True})
        
        if analysis_result.get("success"):
            await self._complete_analysis()
        else:
            await self.context.transition_to("failed", error=analysis_result.get("error"))
        
        return {"success": True}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}
    
    async def _complete_analysis(self) -> None:
        """完成分析"""
        await asyncio.sleep(0.1)  # 模拟延迟
        await self.context.transition_to("active")


class ActiveRepositoryState(RepositoryState):
    """活跃仓库状态"""
    
    def get_state_name(self) -> str:
        return "active"
    
    def get_allowed_transitions(self) -> Set[str]:
        return {"archived", "failed"}
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return True, ""
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入活跃状态"""
        repository = self.context.entity
        repository.last_synced = datetime.now(timezone.utc)
        await self.context.db.commit()
        
        await self.log_state_action("activate", True, **kwargs)
        
        logger.info(f"Repository {repository.id} is now active")
        return {"success": True}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}
    
    async def handle_sync(self, **kwargs) -> Dict[str, Any]:
        """处理同步操作"""
        repository = self.context.entity
        repository.last_synced = datetime.now(timezone.utc)
        await self.context.db.commit()
        
        await self.log_state_action("sync", True, **kwargs)
        
        return {"success": True, "message": "Repository synced successfully"}
    
    async def handle_archive(self, **kwargs) -> Dict[str, Any]:
        """处理归档操作"""
        return await self.context.transition_to("archived", **kwargs)


class FailedRepositoryState(RepositoryState):
    """失败仓库状态"""
    
    def get_state_name(self) -> str:
        return "failed"
    
    def get_allowed_transitions(self) -> Set[str]:
        return {"pending", "archived"}
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return True, ""
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入失败状态"""
        error = kwargs.get("error", "Unknown error")
        
        await self.log_state_action("fail", False, error=error, **kwargs)
        
        logger.error(f"Repository {self.context.entity.id} failed: {error}")
        return {"success": True}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}
    
    async def handle_retry(self, **kwargs) -> Dict[str, Any]:
        """处理重试操作"""
        return await self.context.transition_to("pending", **kwargs)


class ArchivedRepositoryState(RepositoryState):
    """已归档仓库状态"""
    
    def get_state_name(self) -> str:
        return "archived"
    
    def get_allowed_transitions(self) -> Set[str]:
        return {"pending"}  # 可以重新激活
    
    async def can_transition_to(self, new_state: str, **kwargs) -> tuple[bool, str]:
        return True, ""
    
    async def on_enter(self, **kwargs) -> Dict[str, Any]:
        """进入归档状态"""
        await self.log_state_action("archive", True, **kwargs)
        
        logger.info(f"Repository {self.context.entity.id} archived")
        return {"success": True}
    
    async def on_exit(self, **kwargs) -> Dict[str, Any]:
        return {"success": True}
    
    async def handle_reactivate(self, **kwargs) -> Dict[str, Any]:
        """处理重新激活操作"""
        return await self.context.transition_to("pending", **kwargs)


class RepositoryStateMachine(StateMachine):
    """仓库状态机"""
    
    def _initialize_states(self) -> None:
        """初始化状态映射"""
        self.states = {
            "pending": PendingRepositoryState,
            "validating": ValidatingRepositoryState,
            "cloning": CloningRepositoryState,
            "analyzing": AnalyzingRepositoryState,
            "active": ActiveRepositoryState,
            "failed": FailedRepositoryState,
            "archived": ArchivedRepositoryState
        }
    
    def _get_entity_state(self) -> str:
        """获取仓库当前状态"""
        return self.entity.status
    
    async def _update_entity_state(self, new_state: str) -> None:
        """更新仓库状态"""
        self.entity.status = new_state


# ============================================================================
# 状态机工厂
# ============================================================================

class StateMachineFactory:
    """状态机工厂"""
    
    @staticmethod
    def create_invitation_state_machine(db: AsyncSession, invitation: Any) -> InvitationStateMachine:
        """创建邀请状态机"""
        return InvitationStateMachine(db, invitation)
    
    @staticmethod
    def create_repository_state_machine(db: AsyncSession, repository: Any) -> RepositoryStateMachine:
        """创建仓库状态机"""
        return RepositoryStateMachine(db, repository)


# 全局工厂实例
state_machine_factory = StateMachineFactory()