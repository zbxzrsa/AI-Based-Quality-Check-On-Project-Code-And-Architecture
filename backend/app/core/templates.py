"""
模板方法模式实现 - 统一处理具有固定流程但细节不同的算法步骤

包含以下模板：
1. Repository验证模板
2. Invitation状态转换模板
3. 代码审查流程模板
4. 通用业务流程模板
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timezone
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Repository验证模板
# ============================================================================

class RepositoryValidationTemplate(ABC):
    """
    Repository验证模板方法
    
    固定流程：
    1. 设置API headers
    2. 检查仓库存在性
    3. 获取分支列表
    4. 获取标签列表
    5. 验证特定分支
    6. 返回验证结果
    """
    
    async def validate_repository(
        self, 
        repo_info: Dict[str, Any], 
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        模板方法 - 定义验证流程
        
        Args:
            repo_info: 仓库信息
            branch: 可选的分支名称
            
        Returns:
            验证结果
        """
        try:
            logger.info(f"Starting repository validation for {repo_info.get('owner')}/{repo_info.get('name')}")
            
            # 步骤1: 设置API headers
            headers = await self.setup_api_headers()
            
            # 步骤2: 检查仓库存在性
            repo_exists, repo_data = await self.check_repository_existence(repo_info, headers)
            if not repo_exists:
                return self.create_failure_result("Repository not found or inaccessible")
            
            # 步骤3: 获取分支列表
            branches = await self.fetch_branches(repo_info, headers)
            
            # 步骤4: 获取标签列表
            tags = await self.fetch_tags(repo_info, headers)
            
            # 步骤5: 验证特定分支（如果提供）
            branch_validation = await self.validate_specific_branch(repo_info, branch, branches, headers)
            if not branch_validation["valid"]:
                return self.create_failure_result(branch_validation["error"])
            
            # 步骤6: 构建成功结果
            result = await self.build_success_result(repo_data, branches, tags, branch)
            
            logger.info(f"Repository validation completed successfully for {repo_info.get('owner')}/{repo_info.get('name')}")
            return result
            
        except Exception as e:
            logger.error(f"Repository validation failed: {e}")
            return self.create_failure_result(f"Validation error: {str(e)}")
    
    # 抽象方法 - 子类必须实现
    @abstractmethod
    async def setup_api_headers(self) -> Dict[str, str]:
        """设置API请求头"""
        pass
    
    @abstractmethod
    async def check_repository_existence(
        self, 
        repo_info: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """检查仓库是否存在"""
        pass
    
    @abstractmethod
    async def fetch_branches(
        self, 
        repo_info: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> List[str]:
        """获取分支列表"""
        pass
    
    @abstractmethod
    async def fetch_tags(
        self, 
        repo_info: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> List[str]:
        """获取标签列表"""
        pass
    
    # 可选的钩子方法 - 子类可以重写
    async def validate_specific_branch(
        self, 
        repo_info: Dict[str, Any], 
        branch: Optional[str], 
        branches: List[str],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """验证特定分支"""
        if branch and branch not in branches:
            return {"valid": False, "error": f"Branch '{branch}' not found"}
        return {"valid": True}
    
    async def build_success_result(
        self, 
        repo_data: Dict[str, Any], 
        branches: List[str], 
        tags: List[str],
        branch: Optional[str]
    ) -> Dict[str, Any]:
        """构建成功结果"""
        return {
            "is_valid": True,
            "is_accessible": True,
            "exists": True,
            "default_branch": repo_data.get("default_branch", "main"),
            "available_branches": branches[:10],  # 限制返回数量
            "available_tags": tags[:10],
            "validated_branch": branch,
            "metadata": repo_data
        }
    
    def create_failure_result(self, error_message: str) -> Dict[str, Any]:
        """创建失败结果"""
        return {
            "is_valid": False,
            "is_accessible": False,
            "exists": False,
            "error_message": error_message
        }


class GitHubRepositoryValidator(RepositoryValidationTemplate):
    """GitHub仓库验证器实现"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.api_base = "https://api.github.com"
    
    async def setup_api_headers(self) -> Dict[str, str]:
        """设置GitHub API请求头"""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers
    
    async def check_repository_existence(
        self, 
        repo_info: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """检查GitHub仓库是否存在"""
        import aiohttp
        
        owner = repo_info.get("owner")
        name = repo_info.get("name")
        repo_url = f"{self.api_base}/repos/{owner}/{name}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(repo_url, headers=headers) as response:
                if response.status == 200:
                    repo_data = await response.json()
                    return True, repo_data
                elif response.status == 404:
                    return False, None
                elif response.status == 403:
                    return False, None  # Access denied
                else:
                    return False, None
    
    async def fetch_branches(
        self, 
        repo_info: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> List[str]:
        """获取GitHub仓库分支列表"""
        import aiohttp
        
        owner = repo_info.get("owner")
        name = repo_info.get("name")
        branches_url = f"{self.api_base}/repos/{owner}/{name}/branches"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(branches_url, headers=headers) as response:
                    if response.status == 200:
                        branches_data = await response.json()
                        return [b["name"] for b in branches_data]
        except Exception as e:
            logger.warning(f"Failed to fetch branches: {e}")
        
        return []
    
    async def fetch_tags(
        self, 
        repo_info: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> List[str]:
        """获取GitHub仓库标签列表"""
        import aiohttp
        
        owner = repo_info.get("owner")
        name = repo_info.get("name")
        tags_url = f"{self.api_base}/repos/{owner}/{name}/tags"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(tags_url, headers=headers) as response:
                    if response.status == 200:
                        tags_data = await response.json()
                        return [t["name"] for t in tags_data[:50]]  # 限制标签数量
        except Exception as e:
            logger.warning(f"Failed to fetch tags: {e}")
        
        return []


# ============================================================================
# Invitation状态转换模板
# ============================================================================

class InvitationStateTransitionTemplate(ABC):
    """
    Invitation状态转换模板方法
    
    固定流程：
    1. 验证当前状态
    2. 检查转换条件
    3. 执行前置操作
    4. 更新状态
    5. 执行后置操作
    6. 记录审计日志
    """
    
    async def transition_state(
        self,
        db: AsyncSession,
        invitation_id: str,
        new_state: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        模板方法 - 定义状态转换流程
        
        Args:
            db: 数据库会话
            invitation_id: 邀请ID
            new_state: 新状态
            user_id: 操作用户ID
            context: 额外上下文
            
        Returns:
            转换结果
        """
        try:
            logger.info(f"Starting invitation state transition to {new_state} for {invitation_id}")
            
            # 步骤1: 验证当前状态
            invitation = await self.validate_current_state(db, invitation_id)
            if not invitation:
                return {"success": False, "error": "Invitation not found"}
            
            # 步骤2: 检查转换条件
            can_transition, reason = await self.check_transition_conditions(
                invitation, new_state, user_id, context
            )
            if not can_transition:
                return {"success": False, "error": reason}
            
            # 步骤3: 执行前置操作
            pre_result = await self.execute_pre_transition_actions(
                db, invitation, new_state, user_id, context
            )
            if not pre_result["success"]:
                return pre_result
            
            # 步骤4: 更新状态
            old_state = invitation.status
            await self.update_invitation_state(db, invitation, new_state, user_id)
            
            # 步骤5: 执行后置操作
            post_result = await self.execute_post_transition_actions(
                db, invitation, old_state, new_state, user_id, context
            )
            if not post_result["success"]:
                # 如果后置操作失败，可能需要回滚
                logger.warning(f"Post-transition actions failed: {post_result['error']}")
            
            # 步骤6: 记录审计日志
            await self.log_state_transition(
                db, invitation_id, old_state, new_state, user_id, context
            )
            
            logger.info(f"Invitation state transition completed: {old_state} -> {new_state}")
            return {
                "success": True,
                "old_state": old_state,
                "new_state": new_state,
                "invitation": invitation
            }
            
        except Exception as e:
            logger.error(f"Invitation state transition failed: {e}")
            await db.rollback()
            return {"success": False, "error": f"Transition failed: {str(e)}"}
    
    # 抽象方法 - 子类必须实现
    @abstractmethod
    async def validate_current_state(self, db: AsyncSession, invitation_id: str) -> Optional[Any]:
        """验证当前状态"""
        pass
    
    @abstractmethod
    async def check_transition_conditions(
        self, 
        invitation: Any, 
        new_state: str, 
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """检查状态转换条件"""
        pass
    
    @abstractmethod
    async def update_invitation_state(
        self, 
        db: AsyncSession, 
        invitation: Any, 
        new_state: str, 
        user_id: str
    ) -> None:
        """更新邀请状态"""
        pass
    
    # 可选的钩子方法 - 子类可以重写
    async def execute_pre_transition_actions(
        self,
        db: AsyncSession,
        invitation: Any,
        new_state: str,
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行前置操作"""
        return {"success": True}
    
    async def execute_post_transition_actions(
        self,
        db: AsyncSession,
        invitation: Any,
        old_state: str,
        new_state: str,
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行后置操作"""
        return {"success": True}
    
    async def log_state_transition(
        self,
        db: AsyncSession,
        invitation_id: str,
        old_state: str,
        new_state: str,
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> None:
        """记录状态转换审计日志"""
        from app.core.audit_service import UnifiedAuditService
        
        await UnifiedAuditService.log_action(
            db=db,
            user_id=user_id,
            action="state_transition",
            entity_type="invitation",
            entity_id=invitation_id,
            success=True,
            changes={
                "old_state": old_state,
                "new_state": new_state,
                "context": context or {}
            }
        )


class ProjectInvitationTransition(InvitationStateTransitionTemplate):
    """项目邀请状态转换实现"""
    
    async def validate_current_state(self, db: AsyncSession, invitation_id: str) -> Optional[Any]:
        """验证当前状态"""
        from app.models import ProjectInvitation
        from sqlalchemy import select
        from uuid import UUID
        
        try:
            invitation_uuid = UUID(invitation_id)
            result = await db.execute(
                select(ProjectInvitation).where(ProjectInvitation.id == invitation_uuid)
            )
            return result.scalar_one_or_none()
        except ValueError:
            return None
    
    async def check_transition_conditions(
        self, 
        invitation: Any, 
        new_state: str, 
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """检查状态转换条件"""
        from app.models import InvitationStatus
        
        current_state = invitation.status
        
        # 定义允许的状态转换
        allowed_transitions = {
            InvitationStatus.pending.value: [
                InvitationStatus.accepted.value,
                InvitationStatus.declined.value,
                InvitationStatus.expired.value
            ],
            InvitationStatus.accepted.value: [],  # 已接受的邀请不能再转换
            InvitationStatus.declined.value: [],  # 已拒绝的邀请不能再转换
            InvitationStatus.expired.value: []    # 已过期的邀请不能再转换
        }
        
        if new_state not in allowed_transitions.get(current_state, []):
            return False, f"Cannot transition from {current_state} to {new_state}"
        
        # 检查邀请是否过期
        if invitation.is_expired() and new_state != InvitationStatus.expired.value:
            return False, "Invitation has expired"
        
        # 检查用户权限
        if new_state in [InvitationStatus.accepted.value, InvitationStatus.declined.value]:
            # 只有被邀请人可以接受或拒绝
            user_email = context.get("user_email") if context else None
            if user_email != invitation.invitee_email:
                return False, "Only the invitee can accept or decline the invitation"
        
        return True, ""
    
    async def update_invitation_state(
        self, 
        db: AsyncSession, 
        invitation: Any, 
        new_state: str, 
        user_id: str
    ) -> None:
        """更新邀请状态"""
        from app.models import InvitationStatus
        
        invitation.status = new_state
        
        # 设置相关时间戳
        if new_state == InvitationStatus.accepted.value:
            invitation.accepted_at = datetime.now(timezone.utc)
            invitation.invitee_id = user_id
        
        await db.commit()
        await db.refresh(invitation)
    
    async def execute_post_transition_actions(
        self,
        db: AsyncSession,
        invitation: Any,
        old_state: str,
        new_state: str,
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行后置操作"""
        from app.models import InvitationStatus, ProjectMember
        
        try:
            # 如果邀请被接受，创建项目成员记录
            if new_state == InvitationStatus.accepted.value:
                member = ProjectMember(
                    project_id=invitation.project_id,
                    user_id=user_id,
                    role=invitation.role
                )
                db.add(member)
                await db.commit()
                
                logger.info(f"Created project membership for user {user_id}")
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Post-transition action failed: {e}")
            return {"success": False, "error": str(e)}


# ============================================================================
# 代码审查流程模板
# ============================================================================

class CodeReviewPipelineTemplate(ABC):
    """
    代码审查流程模板方法
    
    固定流程：
    1. 解析diff获取变更文件
    2. 初始化审查结果
    3. 并行分析每个文件
    4. 聚合结果
    5. 执行架构分析
    6. 返回审查结果
    """
    
    async def review_code_changes(
        self,
        diff_content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        模板方法 - 定义代码审查流程
        
        Args:
            diff_content: Git diff内容
            context: 审查上下文
            
        Returns:
            审查结果
        """
        try:
            logger.info("Starting code review pipeline")
            
            # 步骤1: 解析diff获取变更文件
            changed_files = await self.parse_diff_files(diff_content)
            if not changed_files:
                return {"success": False, "error": "No changed files found"}
            
            # 步骤2: 初始化审查结果
            review_result = await self.initialize_review_result(changed_files, context)
            
            # 步骤3: 并行分析每个文件
            file_analyses = await self.analyze_files_parallel(changed_files, context)
            
            # 步骤4: 聚合结果
            aggregated_result = await self.aggregate_file_results(file_analyses, review_result)
            
            # 步骤5: 执行架构分析
            architecture_analysis = await self.perform_architecture_analysis(
                changed_files, aggregated_result, context
            )
            
            # 步骤6: 构建最终结果
            final_result = await self.build_final_result(
                aggregated_result, architecture_analysis, context
            )
            
            logger.info("Code review pipeline completed successfully")
            return final_result
            
        except Exception as e:
            logger.error(f"Code review pipeline failed: {e}")
            return {"success": False, "error": f"Review failed: {str(e)}"}
    
    # 抽象方法 - 子类必须实现
    @abstractmethod
    async def parse_diff_files(self, diff_content: str) -> List[Dict[str, Any]]:
        """解析diff文件"""
        pass
    
    @abstractmethod
    async def analyze_single_file(
        self, 
        file_info: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析单个文件"""
        pass
    
    @abstractmethod
    async def perform_architecture_analysis(
        self,
        changed_files: List[Dict[str, Any]],
        file_results: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行架构分析"""
        pass
    
    # 可选的钩子方法 - 子类可以重写
    async def initialize_review_result(
        self, 
        changed_files: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """初始化审查结果"""
        return {
            "total_files": len(changed_files),
            "files_analyzed": 0,
            "issues": [],
            "suggestions": [],
            "metrics": {}
        }
    
    async def analyze_files_parallel(
        self, 
        changed_files: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """并行分析文件"""
        tasks = [
            self.analyze_single_file(file_info, context)
            for file_info in changed_files
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def aggregate_file_results(
        self, 
        file_analyses: List[Dict[str, Any]], 
        review_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """聚合文件分析结果"""
        all_issues = []
        all_suggestions = []
        
        for analysis in file_analyses:
            if isinstance(analysis, dict) and not isinstance(analysis, Exception):
                all_issues.extend(analysis.get("issues", []))
                all_suggestions.extend(analysis.get("suggestions", []))
        
        review_result["issues"] = all_issues
        review_result["suggestions"] = all_suggestions
        review_result["files_analyzed"] = len([a for a in file_analyses if not isinstance(a, Exception)])
        
        return review_result
    
    async def build_final_result(
        self,
        aggregated_result: Dict[str, Any],
        architecture_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建最终结果"""
        return {
            "success": True,
            "summary": {
                "total_files": aggregated_result["total_files"],
                "files_analyzed": aggregated_result["files_analyzed"],
                "total_issues": len(aggregated_result["issues"]),
                "total_suggestions": len(aggregated_result["suggestions"])
            },
            "file_analysis": aggregated_result,
            "architecture_analysis": architecture_analysis,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ============================================================================
# 通用业务流程模板
# ============================================================================

class BusinessProcessTemplate(ABC):
    """
    通用业务流程模板
    
    提供标准的业务流程框架：
    1. 输入验证
    2. 权限检查
    3. 业务逻辑执行
    4. 结果处理
    5. 审计日志记录
    """
    
    async def execute_process(
        self,
        db: AsyncSession,
        input_data: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        模板方法 - 定义业务流程
        
        Args:
            db: 数据库会话
            input_data: 输入数据
            user_id: 用户ID
            context: 额外上下文
            
        Returns:
            处理结果
        """
        process_name = self.get_process_name()
        
        try:
            logger.info(f"Starting business process: {process_name}")
            
            # 步骤1: 输入验证
            validation_result = await self.validate_input(input_data, user_id, context)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
            
            # 步骤2: 权限检查
            permission_result = await self.check_permissions(db, input_data, user_id, context)
            if not permission_result["allowed"]:
                return {"success": False, "error": permission_result["reason"]}
            
            # 步骤3: 执行业务逻辑
            business_result = await self.execute_business_logic(db, input_data, user_id, context)
            if not business_result["success"]:
                return business_result
            
            # 步骤4: 处理结果
            processed_result = await self.process_result(db, business_result, user_id, context)
            
            # 步骤5: 记录审计日志
            await self.log_process_execution(
                db, process_name, input_data, processed_result, user_id, context
            )
            
            logger.info(f"Business process completed: {process_name}")
            return processed_result
            
        except Exception as e:
            logger.error(f"Business process failed: {process_name} - {e}")
            await db.rollback()
            
            # 记录失败的审计日志
            await self.log_process_failure(db, process_name, input_data, str(e), user_id, context)
            
            return {"success": False, "error": f"Process failed: {str(e)}"}
    
    # 抽象方法 - 子类必须实现
    @abstractmethod
    def get_process_name(self) -> str:
        """获取流程名称"""
        pass
    
    @abstractmethod
    async def validate_input(
        self, 
        input_data: Dict[str, Any], 
        user_id: str, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """验证输入数据"""
        pass
    
    @abstractmethod
    async def check_permissions(
        self,
        db: AsyncSession,
        input_data: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """检查权限"""
        pass
    
    @abstractmethod
    async def execute_business_logic(
        self,
        db: AsyncSession,
        input_data: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行业务逻辑"""
        pass
    
    # 可选的钩子方法 - 子类可以重写
    async def process_result(
        self,
        db: AsyncSession,
        business_result: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """处理结果"""
        return business_result
    
    async def log_process_execution(
        self,
        db: AsyncSession,
        process_name: str,
        input_data: Dict[str, Any],
        result: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> None:
        """记录流程执行审计日志"""
        from app.core.audit_service import UnifiedAuditService
        
        await UnifiedAuditService.log_action(
            db=db,
            user_id=user_id,
            action="business_process",
            entity_type=process_name,
            success=result.get("success", False),
            changes={
                "input": input_data,
                "result": result,
                "context": context or {}
            }
        )
    
    async def log_process_failure(
        self,
        db: AsyncSession,
        process_name: str,
        input_data: Dict[str, Any],
        error: str,
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> None:
        """记录流程失败审计日志"""
        from app.core.audit_service import UnifiedAuditService
        
        await UnifiedAuditService.log_action(
            db=db,
            user_id=user_id,
            action="business_process",
            entity_type=process_name,
            success=False,
            changes={
                "input": input_data,
                "error": error,
                "context": context or {}
            }
        )