"""
策略模式实现 - 消除重复的条件分支语句

包含以下策略：
1. 内容类型处理策略
2. GitHub连接类型策略
3. 环境验证策略
4. 审计事件类型策略
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import json
import logging
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


# ============================================================================
# 内容类型处理策略
# ============================================================================

class ContentTypeStrategy(ABC):
    """内容类型处理策略基类"""
    
    @abstractmethod
    async def validate(self, request: Request) -> Dict[str, Any]:
        """验证请求内容"""
        pass
    
    @abstractmethod
    def get_content_type(self) -> str:
        """获取支持的内容类型"""
        pass


class JSONContentStrategy(ContentTypeStrategy):
    """JSON内容类型策略"""
    
    async def validate(self, request: Request) -> Dict[str, Any]:
        """验证JSON内容"""
        try:
            # FastAPI会自动处理JSON解析
            return {"valid": True, "message": "JSON content validated"}
        except Exception as e:
            logger.warning(f"JSON validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format"
            )
    
    def get_content_type(self) -> str:
        return "application/json"


class FormDataStrategy(ContentTypeStrategy):
    """表单数据策略"""
    
    async def validate(self, request: Request) -> Dict[str, Any]:
        """验证表单数据"""
        try:
            form_data = await request.form()
            validated_data = {}
            
            for key, value in form_data.items():
                if isinstance(value, str):
                    # 基本的字符串验证
                    if len(value) > 10000:  # 限制字段长度
                        raise ValueError(f"Field '{key}' is too long")
                    validated_data[key] = value
                else:
                    # 文件上传等其他类型
                    validated_data[key] = value
            
            return {"valid": True, "data": validated_data}
            
        except Exception as e:
            logger.warning(f"Form data validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid form data"
            )
    
    def get_content_type(self) -> str:
        return "application/x-www-form-urlencoded"


class MultipartFormStrategy(ContentTypeStrategy):
    """多部分表单策略"""
    
    async def validate(self, request: Request) -> Dict[str, Any]:
        """验证多部分表单数据"""
        try:
            form_data = await request.form()
            validated_data = {}
            file_info = {}
            
            for key, value in form_data.items():
                if hasattr(value, 'filename'):  # 文件上传
                    # 验证文件类型和大小
                    if value.size > 10 * 1024 * 1024:  # 10MB限制
                        raise ValueError(f"File '{key}' is too large")
                    
                    file_info[key] = {
                        "filename": value.filename,
                        "content_type": value.content_type,
                        "size": value.size
                    }
                    validated_data[key] = value
                else:
                    # 普通字段
                    if isinstance(value, str) and len(value) > 10000:
                        raise ValueError(f"Field '{key}' is too long")
                    validated_data[key] = value
            
            return {
                "valid": True, 
                "data": validated_data,
                "files": file_info
            }
            
        except Exception as e:
            logger.warning(f"Multipart form validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid multipart form data"
            )
    
    def get_content_type(self) -> str:
        return "multipart/form-data"


class ContentTypeProcessor:
    """内容类型处理器 - 策略模式的上下文类"""
    
    def __init__(self):
        self.strategies = {
            "application/json": JSONContentStrategy(),
            "application/x-www-form-urlencoded": FormDataStrategy(),
            "multipart/form-data": MultipartFormStrategy()
        }
    
    async def process_request(self, request: Request) -> Dict[str, Any]:
        """
        根据内容类型处理请求
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            处理结果
        """
        content_type = request.headers.get("content-type", "")
        
        # 找到匹配的策略
        strategy = None
        for ct, strat in self.strategies.items():
            if ct in content_type:
                strategy = strat
                break
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported content type: {content_type}"
            )
        
        return await strategy.validate(request)


# ============================================================================
# GitHub连接类型策略
# ============================================================================

class GitHubConnectionStrategy(ABC):
    """GitHub连接策略基类"""
    
    @abstractmethod
    async def validate_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证连接配置"""
        pass
    
    @abstractmethod
    def get_connection_type(self) -> str:
        """获取连接类型"""
        pass


class HTTPSConnectionStrategy(GitHubConnectionStrategy):
    """HTTPS连接策略"""
    
    async def validate_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证HTTPS连接配置"""
        repo_url = config.get("github_repo_url")
        
        if not repo_url:
            return {"valid": False, "error": "GitHub repository URL is required"}
        
        if not repo_url.startswith("https://github.com/"):
            return {"valid": False, "error": "Invalid HTTPS GitHub URL format"}
        
        return {
            "valid": True,
            "connection_type": "https",
            "clone_url": repo_url
        }
    
    def get_connection_type(self) -> str:
        return "https"


class SSHConnectionStrategy(GitHubConnectionStrategy):
    """SSH连接策略"""
    
    async def validate_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证SSH连接配置"""
        repo_url = config.get("github_repo_url")
        ssh_key_id = config.get("github_ssh_key_id")
        
        if not repo_url:
            return {"valid": False, "error": "GitHub repository URL is required"}
        
        if not ssh_key_id:
            return {"valid": False, "error": "SSH key ID is required for SSH connections"}
        
        # 验证SSH URL格式
        if not (repo_url.startswith("git@github.com:") or repo_url.startswith("ssh://git@github.com/")):
            return {"valid": False, "error": "Invalid SSH GitHub URL format"}
        
        return {
            "valid": True,
            "connection_type": "ssh",
            "ssh_key_id": ssh_key_id,
            "clone_url": repo_url
        }
    
    def get_connection_type(self) -> str:
        return "ssh"


class CLIConnectionStrategy(GitHubConnectionStrategy):
    """CLI连接策略"""
    
    async def validate_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证CLI连接配置"""
        repo_url = config.get("github_repo_url")
        cli_token = config.get("github_cli_token")
        
        if not repo_url:
            return {"valid": False, "error": "GitHub repository URL is required"}
        
        if not cli_token:
            return {"valid": False, "error": "GitHub CLI token is required for CLI connections"}
        
        return {
            "valid": True,
            "connection_type": "cli",
            "cli_token": cli_token,
            "clone_url": repo_url
        }
    
    def get_connection_type(self) -> str:
        return "cli"


class GitHubConnectionProcessor:
    """GitHub连接处理器"""
    
    def __init__(self):
        self.strategies = {
            "https": HTTPSConnectionStrategy(),
            "ssh": SSHConnectionStrategy(),
            "cli": CLIConnectionStrategy()
        }
    
    async def validate_connection(self, connection_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证GitHub连接配置
        
        Args:
            connection_type: 连接类型
            config: 连接配置
            
        Returns:
            验证结果
        """
        strategy = self.strategies.get(connection_type.lower())
        
        if not strategy:
            return {
                "valid": False,
                "error": f"Unsupported connection type: {connection_type}. Must be 'https', 'ssh', or 'cli'"
            }
        
        return await strategy.validate_connection(config)


# ============================================================================
# 环境验证策略
# ============================================================================

class EnvironmentValidationStrategy(ABC):
    """环境验证策略基类"""
    
    @abstractmethod
    def validate(self, settings: Any) -> List[str]:
        """验证环境配置，返回错误列表"""
        pass
    
    @abstractmethod
    def get_environment(self) -> str:
        """获取环境名称"""
        pass


class ProductionValidationStrategy(EnvironmentValidationStrategy):
    """生产环境验证策略"""
    
    def validate(self, settings: Any) -> List[str]:
        """验证生产环境配置"""
        errors = []
        
        # Debug模式检查
        if getattr(settings, 'DEBUG', False):
            errors.append("DEBUG mode is enabled in production")
        
        # HTTPS检查
        if not getattr(settings, 'FORCE_HTTPS', False):
            errors.append("HTTPS is not enforced in production")
        
        # 安全Cookie检查
        if not getattr(settings, 'SECURE_COOKIES', False):
            errors.append("Secure cookies are not enabled in production")
        
        # Bcrypt轮数检查
        bcrypt_rounds = getattr(settings, 'AUTH_BCRYPT_ROUNDS', 12)
        if bcrypt_rounds < 14:
            errors.append(f"Bcrypt rounds ({bcrypt_rounds}) too low for production (minimum: 14)")
        
        # JWT算法检查
        jwt_algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')
        if jwt_algorithm not in ['HS256', 'RS256']:
            errors.append(f"JWT algorithm {jwt_algorithm} may not be secure")
        
        # 并发会话检查
        if getattr(settings, 'AUTH_ALLOW_CONCURRENT_SESSIONS', True):
            errors.append("Concurrent sessions are allowed (security risk)")
        
        return errors
    
    def get_environment(self) -> str:
        return "production"


class DevelopmentValidationStrategy(EnvironmentValidationStrategy):
    """开发环境验证策略"""
    
    def validate(self, settings: Any) -> List[str]:
        """验证开发环境配置"""
        warnings = []
        
        # 检查是否使用了生产级密钥
        required_secrets = [
            "AUTH_JWT_SECRET_KEY",
            "SECRET_KEY", 
            "SESSION_SECRET",
            "DATABASE_ENCRYPTION_KEY"
        ]
        
        insecure_values = [
            "CHANGE_ME_IN_PRODUCTION_USE_SECRETS_MANAGER",
            "dev-secret-key-change-in-production",
            "your-super-secure-256-bit-secret-key-here",
            "your-32-byte-encryption-key-here"
        ]
        
        for secret_name in required_secrets:
            secret_value = getattr(settings, secret_name, None)
            if (secret_value and 
                secret_value not in insecure_values and 
                len(secret_value) >= 32):
                warnings.append(f"Production-grade secret detected in development: {secret_name}")
        
        return warnings
    
    def get_environment(self) -> str:
        return "development"


class TestValidationStrategy(EnvironmentValidationStrategy):
    """测试环境验证策略"""
    
    def validate(self, settings: Any) -> List[str]:
        """验证测试环境配置"""
        warnings = []
        
        # 测试环境特定的检查
        if not getattr(settings, 'TESTING', False):
            warnings.append("TESTING flag is not set in test environment")
        
        # 数据库检查
        database_url = getattr(settings, 'DATABASE_URL', '')
        if 'test' not in database_url.lower():
            warnings.append("Database URL does not contain 'test' - may not be test database")
        
        return warnings
    
    def get_environment(self) -> str:
        return "test"


class EnvironmentValidator:
    """环境验证器"""
    
    def __init__(self):
        self.strategies = {
            "production": ProductionValidationStrategy(),
            "development": DevelopmentValidationStrategy(),
            "test": TestValidationStrategy()
        }
    
    def validate_environment(self, environment: str, settings: Any) -> Dict[str, Any]:
        """
        验证环境配置
        
        Args:
            environment: 环境名称
            settings: 设置对象
            
        Returns:
            验证结果
        """
        strategy = self.strategies.get(environment.lower())
        
        if not strategy:
            return {
                "valid": False,
                "errors": [f"Unknown environment: {environment}"],
                "warnings": []
            }
        
        issues = strategy.validate(settings)
        
        # 根据环境类型区分错误和警告
        if environment.lower() == "production":
            return {
                "valid": len(issues) == 0,
                "errors": issues,
                "warnings": []
            }
        else:
            return {
                "valid": True,  # 开发和测试环境的问题通常是警告
                "errors": [],
                "warnings": issues
            }


# ============================================================================
# 审计事件类型策略
# ============================================================================

class AuditEventStrategy(ABC):
    """审计事件策略基类"""
    
    @abstractmethod
    def get_event_type(self) -> str:
        """获取事件类型"""
        pass
    
    @abstractmethod
    def format_message(self, context: Dict[str, Any]) -> str:
        """格式化审计消息"""
        pass
    
    @abstractmethod
    def get_severity(self) -> str:
        """获取事件严重性"""
        pass


class AuthenticationEventStrategy(AuditEventStrategy):
    """认证事件策略"""
    
    def get_event_type(self) -> str:
        return "authentication"
    
    def format_message(self, context: Dict[str, Any]) -> str:
        action = context.get("action", "unknown")
        email = context.get("email", "unknown")
        success = context.get("success", False)
        
        if action == "login":
            status = "successful" if success else "failed"
            return f"User {email} {status} login attempt"
        elif action == "logout":
            return f"User {email} logged out"
        elif action == "password_change":
            return f"User {email} changed password"
        else:
            return f"Authentication event: {action} for {email}"
    
    def get_severity(self) -> str:
        return "info"


class AuthorizationEventStrategy(AuditEventStrategy):
    """授权事件策略"""
    
    def get_event_type(self) -> str:
        return "authorization"
    
    def format_message(self, context: Dict[str, Any]) -> str:
        email = context.get("email", "unknown")
        resource = context.get("resource_type", "resource")
        action = context.get("action", "access")
        
        return f"User {email} denied {action} to {resource}"
    
    def get_severity(self) -> str:
        return "warning"


class DataModificationEventStrategy(AuditEventStrategy):
    """数据修改事件策略"""
    
    def get_event_type(self) -> str:
        return "data_modification"
    
    def format_message(self, context: Dict[str, Any]) -> str:
        email = context.get("email", "unknown")
        action = context.get("action", "modified")
        resource = context.get("resource_type", "resource")
        resource_id = context.get("resource_id", "unknown")
        
        return f"User {email} {action} {resource} {resource_id}"
    
    def get_severity(self) -> str:
        return "info"


class AdminEventStrategy(AuditEventStrategy):
    """管理员事件策略"""
    
    def get_event_type(self) -> str:
        return "admin"
    
    def format_message(self, context: Dict[str, Any]) -> str:
        email = context.get("email", "unknown")
        action = context.get("action", "performed admin action")
        
        return f"Admin {email} {action}"
    
    def get_severity(self) -> str:
        return "info"


class AuditEventProcessor:
    """审计事件处理器"""
    
    def __init__(self):
        self.strategies = {
            "authentication": AuthenticationEventStrategy(),
            "authorization": AuthorizationEventStrategy(),
            "data_modification": DataModificationEventStrategy(),
            "admin": AdminEventStrategy()
        }
    
    def process_event(self, event_category: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理审计事件
        
        Args:
            event_category: 事件类别
            context: 事件上下文
            
        Returns:
            处理后的事件信息
        """
        strategy = self.strategies.get(event_category)
        
        if not strategy:
            # 默认处理
            return {
                "event_type": "unknown",
                "message": f"Unknown event: {event_category}",
                "severity": "info"
            }
        
        return {
            "event_type": strategy.get_event_type(),
            "message": strategy.format_message(context),
            "severity": strategy.get_severity()
        }


# ============================================================================
# 策略工厂
# ============================================================================

class StrategyFactory:
    """策略工厂类 - 统一管理所有策略"""
    
    def __init__(self):
        self.content_processor = ContentTypeProcessor()
        self.github_processor = GitHubConnectionProcessor()
        self.environment_validator = EnvironmentValidator()
        self.audit_processor = AuditEventProcessor()
    
    def get_content_processor(self) -> ContentTypeProcessor:
        """获取内容类型处理器"""
        return self.content_processor
    
    def get_github_processor(self) -> GitHubConnectionProcessor:
        """获取GitHub连接处理器"""
        return self.github_processor
    
    def get_environment_validator(self) -> EnvironmentValidator:
        """获取环境验证器"""
        return self.environment_validator
    
    def get_audit_processor(self) -> AuditEventProcessor:
        """获取审计事件处理器"""
        return self.audit_processor


# 全局策略工厂实例
strategy_factory = StrategyFactory()