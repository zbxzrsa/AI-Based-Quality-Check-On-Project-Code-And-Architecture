"""
重构后的Repository服务 - 使用设计模式消除重复代码

应用的设计模式：
1. 继承BaseCRUDService消除CRUD重复
2. 使用GitHubRepositoryValidator模板方法
3. 使用RepositoryStateMachine管理状态
4. 使用GitHubConnectionProcessor策略模式
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.base_crud import BaseCRUDService, ValidationError
from app.core.templates import GitHubRepositoryValidator
from app.core.states import RepositoryStateMachine, state_machine_factory
from app.core.strategies import strategy_factory
from app.core.logging import get_logger
from app.models.repository import Repository
from app.schemas.repository import (
    AddRepositoryRequest,
    RepositoryUpdateRequest,
    RepositoryResponse,
    RepositoryInfo,
    RepositoryURLFormat
)

logger = get_logger(__name__)


class RefactoredRepositoryService(BaseCRUDService[Repository, AddRepositoryRequest, RepositoryUpdateRequest, RepositoryResponse]):
    """
    重构后的Repository服务
    
    使用基类消除CRUD重复，使用设计模式处理业务逻辑
    """
    
    def __init__(self, db: AsyncSession, github_token: Optional[str] = None):
        super().__init__(db, Repository)
        self.github_token = github_token
        self.validator = GitHubRepositoryValidator(github_token)
        self.github_processor = strategy_factory.get_github_processor()
    
    @property
    def entity_name(self) -> str:
        return "Repository"
    
    @property
    def owner_field(self) -> str:
        return "created_by"
    
    # ========================================================================
    # CRUD验证方法 - 实现基类抽象方法
    # ========================================================================
    
    async def validate_create_data(self, create_data: AddRepositoryRequest, user_id: str) -> None:
        """验证创建数据"""
        # 解析仓库URL
        repo_info = self.parse_repository_url(create_data.repository_url)
        
        # 验证GitHub连接配置
        connection_config = {
            "github_repo_url": create_data.repository_url,
            "github_ssh_key_id": getattr(create_data, 'ssh_key_id', None),
            "github_cli_token": getattr(create_data, 'cli_token', None)
        }
        
        connection_type = getattr(create_data, 'connection_type', 'https')
        validation_result = await self.github_processor.validate_connection(
            connection_type, connection_config
        )
        
        if not validation_result["valid"]:
            raise ValidationError(validation_result["error"])
        
        # 验证仓库可访问性
        repo_validation = await self.validator.validate_repository(
            repo_info.__dict__, create_data.branch
        )
        
        if not repo_validation["is_valid"]:
            raise ValidationError(repo_validation.get("error_message", "Repository validation failed"))
    
    async def validate_update_data(self, update_data: RepositoryUpdateRequest, entity: Repository, user_id: str) -> None:
        """验证更新数据"""
        # 基本验证 - 可以根据需要扩展
        if hasattr(update_data, 'auto_update') and update_data.auto_update is not None:
            # 验证自动更新设置
            pass
    
    async def validate_delete(self, entity: Repository, user_id: str) -> None:
        """验证删除操作"""
        # 检查是否有依赖关系
        if entity.status == "active":
            # 可以添加额外的检查，比如是否有正在进行的任务
            pass
    
    # ========================================================================
    # 预处理方法 - 重写基类钩子方法
    # ========================================================================
    
    async def preprocess_create_data(self, create_dict: Dict[str, Any], user_id: str, **kwargs) -> Dict[str, Any]:
        """预处理创建数据"""
        # 解析仓库信息
        repo_info = self.parse_repository_url(create_dict["repository_url"])
        
        # 设置仓库基本信息
        create_dict.update({
            "owner": repo_info.owner,
            "name": repo_info.name,
            "status": "pending",  # 初始状态
            "url_format": repo_info.url_format.value,
            "clone_url": repo_info.clone_url
        })
        
        # 获取依赖信息
        dependencies = await self.fetch_dependencies(repo_info, create_dict.get("branch", "main"))
        if dependencies:
            create_dict["metadata"] = {
                "dependencies": dependencies.__dict__,
                "url_format": repo_info.url_format.value,
                "clone_url": repo_info.clone_url
            }
        
        return create_dict
    
    async def preprocess_update_data(self, update_dict: Dict[str, Any], entity: Repository, user_id: str, **kwargs) -> Dict[str, Any]:
        """预处理更新数据"""
        # 如果更新了仓库URL，需要重新验证
        if "repository_url" in update_dict:
            repo_info = self.parse_repository_url(update_dict["repository_url"])
            update_dict.update({
                "owner": repo_info.owner,
                "name": repo_info.name,
                "clone_url": repo_info.clone_url
            })
        
        return update_dict
    
    # ========================================================================
    # 业务逻辑方法
    # ========================================================================
    
    def parse_repository_url(self, url: str) -> RepositoryInfo:
        """
        解析仓库URL - 使用策略模式的简化版本
        
        Args:
            url: GitHub仓库URL
            
        Returns:
            解析后的仓库信息
        """
        import re
        
        # HTTPS格式
        https_match = re.match(r'^https://github\.com/([\w\-\.]+)/([\w\-\.]+?)(?:\.git)?/?$', url)
        if https_match:
            owner, name = https_match.groups()
            return RepositoryInfo(
                owner=owner,
                name=name,
                url_format=RepositoryURLFormat.HTTPS,
                full_url=url,
                clone_url=f"https://github.com/{owner}/{name}.git"
            )
        
        # SSH格式
        ssh_match = re.match(r'^git@github\.com:([\w\-\.]+)/([\w\-\.]+?)(?:\.git)?/?$', url)
        if ssh_match:
            owner, name = ssh_match.groups()
            return RepositoryInfo(
                owner=owner,
                name=name,
                url_format=RepositoryURLFormat.SSH,
                full_url=url,
                clone_url=f"git@github.com:{owner}/{name}.git"
            )
        
        raise ValidationError("Invalid GitHub repository URL format")
    
    async def validate_repository_access(self, repo_info: RepositoryInfo, branch: Optional[str] = None) -> Dict[str, Any]:
        """
        验证仓库访问 - 使用模板方法模式
        
        Args:
            repo_info: 仓库信息
            branch: 可选分支
            
        Returns:
            验证结果
        """
        return await self.validator.validate_repository(repo_info.__dict__, branch)
    
    async def fetch_dependencies(self, repo_info: RepositoryInfo, branch: str = "main") -> Optional[Any]:
        """
        获取依赖信息 - 保持原有逻辑
        
        Args:
            repo_info: 仓库信息
            branch: 分支名称
            
        Returns:
            依赖信息
        """
        # 这里保持原有的依赖获取逻辑
        # 可以进一步重构为策略模式处理不同的包管理器
        import aiohttp
        import base64
        import json
        
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        headers["Accept"] = "application/vnd.github.v3+json"
        
        api_base = "https://api.github.com"
        
        try:
            async with aiohttp.ClientSession() as session:
                # 尝试获取package.json
                package_json_url = f"{api_base}/repos/{repo_info.owner}/{repo_info.name}/contents/package.json?ref={branch}"
                
                async with session.get(package_json_url, headers=headers) as response:
                    if response.status == 200:
                        content_data = await response.json()
                        content = base64.b64decode(content_data["content"]).decode("utf-8")
                        package_data = json.loads(content)
                        
                        from app.schemas.repository import DependencyInfo
                        return DependencyInfo(
                            package_manager="npm",
                            dependencies=package_data.get("dependencies", {}),
                            dev_dependencies=package_data.get("devDependencies", {}),
                            peer_dependencies=package_data.get("peerDependencies", {})
                        )
                
                # 尝试获取requirements.txt
                requirements_url = f"{api_base}/repos/{repo_info.owner}/{repo_info.name}/contents/requirements.txt?ref={branch}"
                
                async with session.get(requirements_url, headers=headers) as response:
                    if response.status == 200:
                        content_data = await response.json()
                        content = base64.b64decode(content_data["content"]).decode("utf-8")
                        
                        dependencies = {}
                        for line in content.split("\n"):
                            line = line.strip()
                            if line and not line.startswith("#"):
                                if "==" in line:
                                    pkg, ver = line.split("==", 1)
                                    dependencies[pkg.strip()] = ver.strip()
                                else:
                                    dependencies[line] = "*"
                        
                        from app.schemas.repository import DependencyInfo
                        return DependencyInfo(
                            package_manager="pip",
                            dependencies=dependencies,
                            dev_dependencies={},
                            peer_dependencies={}
                        )
                
        except Exception as e:
            logger.warning(f"Failed to fetch dependencies: {e}")
        
        return None
    
    async def sync_repository(self, repository_id: str, user_id: str) -> Dict[str, Any]:
        """
        同步仓库 - 使用状态机管理状态
        
        Args:
            repository_id: 仓库ID
            user_id: 用户ID
            
        Returns:
            同步结果
        """
        try:
            # 获取仓库
            repository = await self.get_by_id(repository_id, user_id, check_ownership=True)
            
            # 创建状态机
            state_machine = state_machine_factory.create_repository_state_machine(self.db, repository)
            
            # 如果是活跃状态，执行同步操作
            if state_machine.get_current_state_name() == "active":
                result = await state_machine.handle_action("sync", user_id=user_id)
                if result["success"]:
                    # 重新验证仓库
                    repo_info = RepositoryInfo(
                        owner=repository.owner,
                        name=repository.name,
                        url_format=RepositoryURLFormat(repository.url_format),
                        full_url=repository.repository_url,
                        clone_url=repository.clone_url
                    )
                    
                    validation_result = await self.validate_repository_access(repo_info, repository.branch)
                    
                    if validation_result["is_valid"]:
                        # 更新元数据
                        if validation_result.get("metadata"):
                            repository.metadata = validation_result["metadata"]
                            await self.db.commit()
                        
                        return {
                            "success": True,
                            "message": "Repository synced successfully",
                            "repository": repository
                        }
                    else:
                        # 验证失败，转换到失败状态
                        await state_machine.transition_to("failed", 
                                                        error=validation_result.get("error_message"),
                                                        user_id=user_id)
                        return {
                            "success": False,
                            "error": f"Repository validation failed: {validation_result.get('error_message')}"
                        }
                else:
                    return result
            else:
                return {
                    "success": False,
                    "error": f"Repository is in {state_machine.get_current_state_name()} state and cannot be synced"
                }
                
        except Exception as e:
            logger.error(f"Repository sync failed: {e}")
            return {"success": False, "error": f"Sync failed: {str(e)}"}
    
    async def archive_repository(self, repository_id: str, user_id: str) -> Dict[str, Any]:
        """
        归档仓库 - 使用状态机管理状态转换
        
        Args:
            repository_id: 仓库ID
            user_id: 用户ID
            
        Returns:
            归档结果
        """
        try:
            # 获取仓库
            repository = await self.get_by_id(repository_id, user_id, check_ownership=True)
            
            # 创建状态机
            state_machine = state_machine_factory.create_repository_state_machine(self.db, repository)
            
            # 转换到归档状态
            result = await state_machine.transition_to("archived", user_id=user_id)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Repository archived successfully",
                    "repository": repository
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Repository archive failed: {e}")
            return {"success": False, "error": f"Archive failed: {str(e)}"}
    
    async def reactivate_repository(self, repository_id: str, user_id: str) -> Dict[str, Any]:
        """
        重新激活仓库
        
        Args:
            repository_id: 仓库ID
            user_id: 用户ID
            
        Returns:
            激活结果
        """
        try:
            # 获取仓库
            repository = await self.get_by_id(repository_id, user_id, check_ownership=True)
            
            # 创建状态机
            state_machine = state_machine_factory.create_repository_state_machine(self.db, repository)
            
            # 根据当前状态决定操作
            current_state = state_machine.get_current_state_name()
            
            if current_state == "archived":
                result = await state_machine.handle_action("reactivate", user_id=user_id)
            elif current_state == "failed":
                result = await state_machine.handle_action("retry", user_id=user_id)
            else:
                return {
                    "success": False,
                    "error": f"Repository is in {current_state} state and cannot be reactivated"
                }
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Repository reactivation started",
                    "repository": repository
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Repository reactivation failed: {e}")
            return {"success": False, "error": f"Reactivation failed: {str(e)}"}
    
    async def get_repository_status(self, repository_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取仓库状态信息
        
        Args:
            repository_id: 仓库ID
            user_id: 用户ID
            
        Returns:
            状态信息
        """
        try:
            # 获取仓库
            repository = await self.get_by_id(repository_id, user_id, check_ownership=True)
            
            # 创建状态机
            state_machine = state_machine_factory.create_repository_state_machine(self.db, repository)
            
            return {
                "success": True,
                "repository_id": repository_id,
                "current_state": state_machine.get_current_state_name(),
                "allowed_transitions": list(state_machine.get_allowed_transitions()),
                "last_updated": repository.updated_at.isoformat() if repository.updated_at else None,
                "last_synced": repository.last_synced.isoformat() if repository.last_synced else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get repository status: {e}")
            return {"success": False, "error": f"Status check failed: {str(e)}"}


# ========================================================================
# 工厂方法
# ========================================================================

def create_repository_service(db: AsyncSession, github_token: Optional[str] = None) -> RefactoredRepositoryService:
    """
    创建Repository服务实例
    
    Args:
        db: 数据库会话
        github_token: GitHub访问令牌
        
    Returns:
        Repository服务实例
    """
    return RefactoredRepositoryService(db, github_token)