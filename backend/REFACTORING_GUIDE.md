"""
重构指南 - 将现有服务重构为依赖注入模式

本文档展示了如何将现有服务重构为使用依赖注入，以提高可测试性和可维护性。

## 重构示例

### 重构前（高耦合）:

```python
# app/services/repository_service.py
class RepositoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.github_token = settings.GITHUB_TOKEN  # 直接依赖配置
        self.cache = Redis()  # 直接依赖具体实现
    
    async def validate_repository(self, url: str):
        # 业务逻辑...
        async with aiohttp.ClientSession() as session:  # 直接创建客户端
            # ...
```

### 重构后（依赖注入）:

```python
# 1. 定义接口 (domain/services/__init__.py)
class IGitHubService(ABC):
    @abstractmethod
    async def get_repository(self, repo_url: str) -> Dict[str, Any]:
        pass

class ICacheService(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        pass

# 2. 创建基础设施层实现 (infrastructure/external/)
class GitHubService(IGitHubService):
    def __init__(self, token: str):
        self.token = token
    
    async def get_repository(self, repo_url: str):
        # 使用 aiohttp...

class RedisCacheService(ICacheService):
    def __init__(self, redis_client):
        self._client = redis_client
    
    async def get(self, key: str):
        return await self._client.get(key)

# 3. 在服务中使用接口 (domain/services/)
class RepositoryService:
    def __init__(
        self,
        db: AsyncSession,
        github_service: IGitHubService,  # 依赖抽象接口
        cache_service: ICacheService,   # 依赖抽象接口
    ):
        self.db = db
        self.github = github_service
        self.cache = cache_service
    
    async def validate_repository(self, url: str):
        # 使用注入的依赖，不直接创建
        repo_data = await self.github.get_repository(url)
        # ...
```

## 重构步骤

### 步骤 1: 识别依赖
找出服务中直接实例化的外部依赖：
- HTTP 客户端 (aiohttp, httpx)
- 数据库客户端
- 缓存服务
- 第三方 SDK

### 步骤 2: 定义接口
在 domain/services/ 中定义抽象接口：
```python
class IExternalService(ABC):
    @abstractmethod
    async def do_something(self, param: str) -> Result:
        pass
```

### 步骤 3: 创建实现
在 infrastructure/ 中创建具体实现：
```python
class ConcreteExternalService(IExternalService):
    def __init__(self, config: dict):
        self._config = config
    
    async def do_something(self, param: str) -> Result:
        # 实现...
```

### 步骤 4: 重构服务
修改服务构造函数，接受接口而非具体实现：
```python
class MyService:
    def __init__(
        self,
        external_service: IExternalService,  # 接口
    ):
        self._external = external_service
```

### 步骤 5: 设置依赖注入容器
在应用启动时注册依赖：
```python
# infrastructure/container.py
container = DIContainer()
container.register(IGitHubService, GitHubService)
container.register(ICacheService, RedisCacheService)

# 解析
service = container.resolve(MyService)
```

## 迁移策略

### 渐进式迁移
1. 不需要一次性重构所有服务
2. 每次重构一个服务
3. 确保重构后的服务通过测试
4. 保持向后兼容

### 测试优势
重构后，可以轻松使用 Mock：
```python
# 测试时注入 Mock
mock_github = Mock(spec=IGitHubService)
mock_github.get_repository.return_value = {"name": "test-repo"}

service = MyService(github_service=mock_github)
# 测试...
```

## 验证

每次重构后运行测试确保：
1. 单元测试通过
2. 集成测试通过
3. 功能保持一致
"""
