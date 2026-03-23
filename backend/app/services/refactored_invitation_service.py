"""
重构后的ProjectInvitation服务 - 使用设计模式消除重复代码

应用的设计模式：
1. 使用InvitationStateMachine管理状态转换
2. 使用模板方法模式处理邀请流程
3. 使用策略模式处理不同类型的邀请
4. 继承BusinessProcessTemplate统一业务流程
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.templates import BusinessProcessTemplate
from app.core.states import InvitationStateMachine, state_machine_factory
from app.core.logging import get_logger
from app.models import (
    ProjectInvitation, ProjectMember, User, Project, 
    InvitationStatus, ProjectRole
)
from app.core.audit_service import UnifiedAuditService

logger = get_logger(__name__)


class InvitationCreationProcess(BusinessProcessTemplate):
    """
    邀请创建业务流程 - 使用模板方法模式
    """
    
    def get_process_name(self) -> str:
        return "invitation_creation"
    
    async def validate_input(
        self, 
        input_data: Dict[str, Any], 
        user_id: str, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """验证邀请创建输入"""
        required_fields = ["project_id", "invitee_email", "role"]
        
        for field in required_fields:
            if field not in input_data:
                return {"valid": False, "error": f"Missing required field: {field}"}
        
        # 验证角色
        valid_roles = [role.value for role in ProjectRole]
        if input_data["role"] not in valid_roles:
            return {"valid": False, "error": f"Invalid role. Must be one of: {valid_roles}"}
        
        # 验证邮箱格式
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, input_data["invitee_email"]):
            return {"valid": False, "error": "Invalid email format"}
        
        return {"valid": True}
    
    async def check_permissions(
        self,
        db: AsyncSession,
        input_data: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """检查邀请权限"""
        try:
            project_id = UUID(input_data["project_id"])
            user_uuid = UUID(user_id)
            
            # 检查项目是否存在
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                return {"allowed": False, "reason": "Project not found"}
            
            # 检查用户是否是项目所有者或有邀请权限的成员
            if project.owner_id == user_uuid:
                return {"allowed": True, "reason": "Project owner"}
            
            # 检查是否是项目维护者
            member_result = await db.execute(
                select(ProjectMember).where(
                    and_(
                        ProjectMember.project_id == project_id,
                        ProjectMember.user_id == user_uuid,
                        ProjectMember.role.in_([ProjectRole.maintainer.value, ProjectRole.owner.value])
                    )
                )
            )
            
            if member_result.scalar_one_or_none():
                return {"allowed": True, "reason": "Project maintainer"}
            
            return {"allowed": False, "reason": "Insufficient permissions to invite users"}
            
        except ValueError:
            return {"allowed": False, "reason": "Invalid project ID format"}
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return {"allowed": False, "reason": "Permission check failed"}
    
    async def execute_business_logic(
        self,
        db: AsyncSession,
        input_data: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行邀请创建逻辑"""
        try:
            project_id = UUID(input_data["project_id"])
            inviter_id = UUID(user_id)
            invitee_email = input_data["invitee_email"]
            role = input_data["role"]
            message = input_data.get("message")
            days_valid = input_data.get("days_valid", 7)
            
            # 检查用户是否已经是成员
            existing_member = await self._check_existing_member(db, project_id, invitee_email)
            if existing_member:
                return {"success": False, "error": "User is already a member of this project"}
            
            # 检查是否存在待处理邀请
            existing_invitation = await self._check_existing_invitation(db, project_id, invitee_email)
            if existing_invitation:
                return {"success": False, "error": "Pending invitation already exists for this user"}
            
            # 创建邀请
            invitation = ProjectInvitation.create_with_expiry(
                project_id=project_id,
                inviter_id=inviter_id,
                invitee_email=invitee_email,
                role=role,
                message=message,
                days_valid=days_valid
            )
            
            db.add(invitation)
            await db.commit()
            await db.refresh(invitation)
            
            return {
                "success": True,
                "invitation": invitation,
                "invitation_id": str(invitation.id),
                "invitation_token": invitation.invitation_token
            }
            
        except Exception as e:
            logger.error(f"Invitation creation failed: {e}")
            return {"success": False, "error": f"Failed to create invitation: {str(e)}"}
    
    async def _check_existing_member(self, db: AsyncSession, project_id: UUID, email: str) -> bool:
        """检查用户是否已经是项目成员"""
        result = await db.execute(
            select(ProjectMember)
            .join(User, ProjectMember.user_id == User.id)
            .where(
                and_(
                    ProjectMember.project_id == project_id,
                    User.email == email
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def _check_existing_invitation(self, db: AsyncSession, project_id: UUID, email: str) -> bool:
        """检查是否存在待处理邀请"""
        result = await db.execute(
            select(ProjectInvitation).where(
                and_(
                    ProjectInvitation.project_id == project_id,
                    ProjectInvitation.invitee_email == email,
                    ProjectInvitation.status == InvitationStatus.pending.value
                )
            )
        )
        return result.scalar_one_or_none() is not None


class InvitationResponseProcess(BusinessProcessTemplate):
    """
    邀请响应业务流程 - 处理接受/拒绝邀请
    """
    
    def get_process_name(self) -> str:
        return "invitation_response"
    
    async def validate_input(
        self, 
        input_data: Dict[str, Any], 
        user_id: str, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """验证邀请响应输入"""
        required_fields = ["invitation_token", "action"]
        
        for field in required_fields:
            if field not in input_data:
                return {"valid": False, "error": f"Missing required field: {field}"}
        
        # 验证操作类型
        valid_actions = ["accept", "decline"]
        if input_data["action"] not in valid_actions:
            return {"valid": False, "error": f"Invalid action. Must be one of: {valid_actions}"}
        
        return {"valid": True}
    
    async def check_permissions(
        self,
        db: AsyncSession,
        input_data: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """检查邀请响应权限"""
        try:
            invitation_token = input_data["invitation_token"]
            
            # 获取邀请
            result = await db.execute(
                select(ProjectInvitation).where(
                    ProjectInvitation.invitation_token == invitation_token
                )
            )
            invitation = result.scalar_one_or_none()
            
            if not invitation:
                return {"allowed": False, "reason": "Invalid invitation token"}
            
            # 获取用户信息
            user_result = await db.execute(
                select(User).where(User.id == UUID(user_id))
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"allowed": False, "reason": "User not found"}
            
            # 检查邮箱是否匹配
            if user.email != invitation.invitee_email:
                return {"allowed": False, "reason": "User email does not match invitation"}
            
            # 检查邀请状态
            if invitation.status != InvitationStatus.pending.value:
                return {"allowed": False, "reason": "Invitation has already been processed"}
            
            # 检查是否过期
            if invitation.is_expired():
                return {"allowed": False, "reason": "Invitation has expired"}
            
            return {"allowed": True, "reason": "Valid invitation", "invitation": invitation}
            
        except ValueError:
            return {"allowed": False, "reason": "Invalid user ID format"}
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return {"allowed": False, "reason": "Permission check failed"}
    
    async def execute_business_logic(
        self,
        db: AsyncSession,
        input_data: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行邀请响应逻辑"""
        try:
            invitation = context["invitation"]
            action = input_data["action"]
            user_email = context.get("user_email")
            
            # 创建状态机
            state_machine = state_machine_factory.create_invitation_state_machine(db, invitation)
            
            # 根据操作类型处理
            if action == "accept":
                result = await state_machine.handle_action(
                    "accept", 
                    user_id=UUID(user_id),
                    user_email=user_email
                )
            elif action == "decline":
                result = await state_machine.handle_action(
                    "decline",
                    user_id=UUID(user_id),
                    user_email=user_email
                )
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
            
            if result["success"]:
                return {
                    "success": True,
                    "action": action,
                    "invitation": invitation,
                    "message": f"Invitation {action}ed successfully"
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Invitation response failed: {e}")
            return {"success": False, "error": f"Failed to {input_data.get('action', 'process')} invitation: {str(e)}"}


class RefactoredInvitationService:
    """
    重构后的邀请服务 - 使用设计模式统一处理
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.creation_process = InvitationCreationProcess()
        self.response_process = InvitationResponseProcess()
    
    async def create_invitation(
        self,
        project_id: str,
        inviter_id: str,
        invitee_email: str,
        role: str = ProjectRole.member.value,
        message: Optional[str] = None,
        days_valid: int = 7
    ) -> Dict[str, Any]:
        """
        创建项目邀请 - 使用业务流程模板
        
        Args:
            project_id: 项目ID
            inviter_id: 邀请人ID
            invitee_email: 被邀请人邮箱
            role: 角色
            message: 邀请消息
            days_valid: 有效天数
            
        Returns:
            创建结果
        """
        input_data = {
            "project_id": project_id,
            "invitee_email": invitee_email,
            "role": role,
            "message": message,
            "days_valid": days_valid
        }
        
        result = await self.creation_process.execute_process(
            db=self.db,
            input_data=input_data,
            user_id=inviter_id
        )
        
        if result["success"]:
            # 记录邀请发送审计日志
            await UnifiedAuditService.log_action(
                db=self.db,
                user_id=inviter_id,
                action="send_invitation",
                entity_type="project_invitation",
                entity_id=result.get("invitation_id"),
                success=True,
                changes={
                    "project_id": project_id,
                    "invitee_email": invitee_email,
                    "role": role
                }
            )
        
        return result
    
    async def accept_invitation(
        self,
        invitation_token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        接受邀请 - 使用状态机处理
        
        Args:
            invitation_token: 邀请令牌
            user_id: 用户ID
            
        Returns:
            处理结果
        """
        # 获取用户邮箱
        user_result = await self.db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = user_result.scalar_one_or_none()
        user_email = user.email if user else None
        
        input_data = {
            "invitation_token": invitation_token,
            "action": "accept"
        }
        
        context = {"user_email": user_email}
        
        return await self.response_process.execute_process(
            db=self.db,
            input_data=input_data,
            user_id=user_id,
            context=context
        )
    
    async def decline_invitation(
        self,
        invitation_token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        拒绝邀请 - 使用状态机处理
        
        Args:
            invitation_token: 邀请令牌
            user_id: 用户ID
            
        Returns:
            处理结果
        """
        # 获取用户邮箱
        user_result = await self.db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = user_result.scalar_one_or_none()
        user_email = user.email if user else None
        
        input_data = {
            "invitation_token": invitation_token,
            "action": "decline"
        }
        
        context = {"user_email": user_email}
        
        return await self.response_process.execute_process(
            db=self.db,
            input_data=input_data,
            user_id=user_id,
            context=context
        )
    
    async def get_pending_invitations_for_user(self, user_email: str) -> List[ProjectInvitation]:
        """
        获取用户的待处理邀请
        
        Args:
            user_email: 用户邮箱
            
        Returns:
            待处理邀请列表
        """
        result = await self.db.execute(
            select(ProjectInvitation)
            .where(
                and_(
                    ProjectInvitation.invitee_email == user_email,
                    ProjectInvitation.status == InvitationStatus.pending.value,
                    ProjectInvitation.expires_at > datetime.now(timezone.utc)
                )
            )
            .options(
                selectinload(ProjectInvitation.project),
                selectinload(ProjectInvitation.inviter)
            )
        )
        return result.scalars().all()
    
    async def get_project_members(self, project_id: str) -> List[ProjectMember]:
        """
        获取项目成员列表
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目成员列表
        """
        try:
            project_uuid = UUID(project_id)
            result = await self.db.execute(
                select(ProjectMember)
                .where(ProjectMember.project_id == project_uuid)
                .options(selectinload(ProjectMember.user))
            )
            return result.scalars().all()
        except ValueError:
            return []
    
    async def get_user_project_memberships(self, user_id: str) -> List[ProjectMember]:
        """
        获取用户的项目成员资格
        
        Args:
            user_id: 用户ID
            
        Returns:
            项目成员资格列表
        """
        try:
            user_uuid = UUID(user_id)
            result = await self.db.execute(
                select(ProjectMember)
                .where(ProjectMember.user_id == user_uuid)
                .options(selectinload(ProjectMember.project))
            )
            return result.scalars().all()
        except ValueError:
            return []
    
    async def cleanup_expired_invitations(self) -> int:
        """
        清理过期邀请 - 使用状态机批量处理
        
        Returns:
            清理的邀请数量
        """
        try:
            # 获取所有过期的待处理邀请
            result = await self.db.execute(
                select(ProjectInvitation).where(
                    and_(
                        ProjectInvitation.status == InvitationStatus.pending.value,
                        ProjectInvitation.expires_at <= datetime.now(timezone.utc)
                    )
                )
            )
            expired_invitations = result.scalars().all()
            
            cleaned_count = 0
            
            for invitation in expired_invitations:
                try:
                    # 使用状态机处理过期
                    state_machine = state_machine_factory.create_invitation_state_machine(self.db, invitation)
                    result = await state_machine.transition_to("expired")
                    
                    if result["success"]:
                        cleaned_count += 1
                    else:
                        logger.warning(f"Failed to expire invitation {invitation.id}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error expiring invitation {invitation.id}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} expired invitations")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Cleanup expired invitations failed: {e}")
            return 0
    
    async def has_project_access(self, user_id: str, project_id: str) -> bool:
        """
        检查用户是否有项目访问权限
        
        Args:
            user_id: 用户ID
            project_id: 项目ID
            
        Returns:
            是否有访问权限
        """
        try:
            user_uuid = UUID(user_id)
            project_uuid = UUID(project_id)
            
            # 检查是否是项目所有者
            project_result = await self.db.execute(
                select(Project).where(
                    and_(
                        Project.id == project_uuid,
                        Project.owner_id == user_uuid
                    )
                )
            )
            if project_result.scalar_one_or_none():
                return True
            
            # 检查是否是项目成员
            member_result = await self.db.execute(
                select(ProjectMember).where(
                    and_(
                        ProjectMember.project_id == project_uuid,
                        ProjectMember.user_id == user_uuid
                    )
                )
            )
            return member_result.scalar_one_or_none() is not None
            
        except ValueError:
            return False
        except Exception as e:
            logger.error(f"Access check failed: {e}")
            return False


# ========================================================================
# 工厂方法
# ========================================================================

def create_invitation_service(db: AsyncSession) -> RefactoredInvitationService:
    """
    创建邀请服务实例
    
    Args:
        db: 数据库会话
        
    Returns:
        邀请服务实例
    """
    return RefactoredInvitationService(db)