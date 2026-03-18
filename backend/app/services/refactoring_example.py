"""
服务重构示例 - Repository Management

这个文件展示了如何将现有的高耦合服务重构为使用依赖注入的架构。

## 重构前后对比

### 重构前 (高耦合)
- 直接实例化 aiohttp.ClientSession
- 硬编码 GitHub API 端点
- 业务逻辑与 HTTP 客户端耦合
- 难以单元测试

### 重构后 (依赖注入)
- 通过接口注入 GitHub 服务
- 业务逻辑与 HTTP 客户端解耦
- 易于单元测试 Mock
- 可插拔的外部依赖
"""

# =============================================================================
# 第一步：定义领域服务接口 (domain/services/)
# =============================================================================
"""
# domain/services/repository.py (新文件)
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class RepositoryURLFormat(str, Enum):
    HTTPS = "https"
    SSH = "ssh"

@dataclass
class RepositoryInfo:
    owner: str
    name: str
    url_format: RepositoryURLFormat
    full_url: str
    clone_url: str

@dataclass
class RepositoryValidationResult:
    is_valid: bool
    is_accessible: bool
    exists: bool
    default_branch: Optional[str] = None
    available_branches: List[str] = None
    available_tags: List[str] = None
    error_message: Optional[str] = None

@dataclass
class DependencyInfo:
    package_manager: str
    dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str] = None
    peer_dependencies: Dict[str, str] = None

class IRepositoryService(ABC):
    '''仓储服务接口'''
    
    @abstractmethod
    async def parse_url(self, url: str) -> RepositoryInfo:
        '''解析仓库 URL'''
        pass
    
    @abstractmethod
    async def validate(
        self,
        repo_info: RepositoryInfo,
        branch: Optional[str] = None
    ) -> RepositoryValidationResult:
        '''验证仓库'''
        pass
    
    @abstractmethod
    async def fetch_dependencies(
        self,
        repo_info: RepositoryInfo,
        branch: str = "main"
    ) -> Optional[DependencyInfo]:
        '''获取依赖信息'''
        pass
"""

# =============================================================================
# 第二步：创建基础设施层实现 (infrastructure/)
# =============================================================================
"""
# infrastructure/external/github/repository_service.py
import re
import aiohttp
import base64
import json
from typing import Optional, Dict, Any, List

from domain.services.repository import (
    IRepositoryService,
    RepositoryInfo,
    RepositoryValidationResult,
    DependencyInfo,
    RepositoryURLFormat,
)

class GitHubRepositoryService(IRepositoryService):
    '''GitHub 仓储服务实现'''
    
    def __init__(self, token: str = None, api_base: str = "https://api.github.com"):
        self.token = token
        self.api_base = api_base
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers
    
    async def parse_url(self, url: str) -> RepositoryInfo:
        # HTTPS format: https://github.com/{owner}/{repo}.git
        https_match = re.match(
            r'^https://github\.com/([\w\-\.]+)/([\w\-\.]+?)(?:\.git)?$',
            url
        )
        
        # SSH format: git@github.com:{owner}/{repo}.git
        ssh_match = re.match(
            r'^git@github\.com:([\w\-\.]+)/([\w\-\.]+?)(?:\.git)?$',
            url
        )
        
        if https_match:
            owner, name = https_match.groups()
            url_format = RepositoryURLFormat.HTTPS
            clone_url = f"https://github.com/{owner}/{name}.git"
        elif ssh_match:
            owner, name = ssh_match.groups()
            url_format = RepositoryURLFormat.SSH
            clone_url = f"git@github.com:{owner}/{name}.git"
        else:
            raise ValueError("Invalid GitHub repository URL format")
        
        return RepositoryInfo(
            owner=owner,
            name=name,
            url_format=url_format,
            full_url=url,
            clone_url=clone_url
        )
    
    async def validate(
        self,
        repo_info: RepositoryInfo,
        branch: Optional[str] = None
    ) -> RepositoryValidationResult:
        async with aiohttp.ClientSession() as session:
            # Check repository existence
            repo_url = f"{self.api_base}/repos/{repo_info.owner}/{repo_info.name}"
            
            async with session.get(repo_url, headers=self._get_headers()) as response:
                if response.status == 404:
                    return RepositoryValidationResult(
                        is_valid=False,
                        is_accessible=False,
                        exists=False,
                        error_message="Repository not found"
                    )
                # ... more validation logic
            
            # Get branches and tags...
            
            return RepositoryValidationResult(
                is_valid=True,
                is_accessible=True,
                exists=True,
                default_branch="main",
                available_branches=["main", "develop"],
                available_tags=["v1.0.0"]
            )
    
    async def fetch_dependencies(
        self,
        repo_info: RepositoryInfo,
        branch: str = "main"
    ) -> Optional[DependencyInfo]:
        async with aiohttp.ClientSession() as session:
            # Fetch package.json or requirements.txt
            # ...
            pass
"""

# =============================================================================
# 第三步：创建应用层用例 (application/)
# =============================================================================
"""
# application/commands/add_repository.py
from dataclasses import dataclass
from typing import Optional

from application.base import Command, UseCaseResult
from domain.services.repository import (
    IRepositoryService,
    RepositoryInfo,
)

@dataclass
class AddRepositoryCommand:
    repository_url: str
    branch: Optional[str] = None
    user_id: str = ""

class AddRepositoryUseCase(Command):
    '''添加仓库用例'''
    
    def __init__(self, repository_service: IRepositoryService):
        self.repository_service = repository_service
    
    async def execute(self, command: AddRepositoryCommand) -> UseCaseResult:
        try:
            # 1. Parse URL (使用注入的服务)
            repo_info = await self.repository_service.parse_url(command.repository_url)
            
            # 2. Validate repository
            validation = await self.repository_service.validate(
                repo_info,
                command.branch
            )
            
            if not validation.is_valid:
                return UseCaseResult.err(validation.error_message)
            
            # 3. Fetch dependencies
            dependencies = await self.repository_service.fetch_dependencies(
                repo_info,
                command.branch or validation.default_branch
            )
            
            # 4. Return result
            return UseCaseResult.ok({
                "owner": repo_info.owner,
                "name": repo_info.name,
                "branch": command.branch or validation.default_branch,
                "dependencies": dependencies,
            })
            
        except Exception as e:
            return UseCaseResult.err(str(e))
"""

# =============================================================================
# 第四步：在 API 中使用用例 (api/)
# =============================================================================
"""
# api/v1/endpoints/repositories.py
from fastapi import APIRouter, Depends

from application.commands.add_repository import (
    AddRepositoryUseCase,
    AddRepositoryCommand,
)
from infrastructure.container import get_container

router = APIRouter()

def get_add_repository_use_case(
    container = Depends(get_container)
) -> AddRepositoryUseCase:
    '''依赖注入获取用例'''
    repo_service = container.resolve(IRepositoryService)
    return AddRepositoryUseCase(repository_service=repo_service)

@router.post("/repositories")
async def add_repository(
    request: AddRepositoryRequest,
    use_case: AddRepositoryUseCase = Depends(get_add_repository_use_case)
):
    command = AddRepositoryCommand(
        repository_url=request.repository_url,
        branch=request.branch,
        user_id=request.user_id,
    )
    
    result = await use_case.execute(command)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return result.data
"""

# =============================================================================
# 第五步：测试优势 (单元测试)
# =============================================================================
"""
# tests/test_add_repository_use_case.py
import pytest
from unittest.mock import Mock, AsyncMock

from application.commands.add_repository import AddRepositoryUseCase, AddRepositoryCommand
from domain.services.repository import RepositoryInfo, RepositoryValidationResult

@pytest.fixture
def mock_repository_service():
    service = Mock()
    service.parse_url = AsyncMock(return_value=RepositoryInfo(
        owner="test-owner",
        name="test-repo",
        url_format="https",
        full_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git"
    ))
    service.validate = AsyncMock(return_value=RepositoryValidationResult(
        is_valid=True,
        is_accessible=True,
        exists=True,
        default_branch="main",
    ))
    service.fetch_dependencies = AsyncMock(return_value=None)
    return service

@pytest.mark.asyncio
async def test_add_repository_success(mock_repository_service):
    # Arrange
    use_case = AddRepositoryUseCase(mock_repository_service)
    command = AddRepositoryCommand(
        repository_url="https://github.com/test-owner/test-repo",
        user_id="user-123",
    )
    
    # Act
    result = await use_case.execute(command)
    
    # Assert
    assert result.success
    assert result.data["owner"] == "test-owner"
    assert result.data["name"] == "test-repo"
    mock_repository_service.parse_url.assert_called_once()
    mock_repository_service.validate.assert_called_once()

@pytest.mark.asyncio
async def test_add_repository_invalid_url(mock_repository_service):
    # Arrange
    mock_repository_service.parse_url.side_effect = ValueError("Invalid URL")
    use_case = AddRepositoryUseCase(mock_repository_service)
    command = AddRepositoryCommand(
        repository_url="invalid-url",
    )
    
    # Act
    result = await use_case.execute(command)
    
    # Assert
    assert not result.success
    assert "Invalid URL" in result.error
"""

print(__doc__)
