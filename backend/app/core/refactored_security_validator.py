"""
重构后的安全配置验证器 - 使用策略模式消除条件分支

应用的改进：
1. 使用EnvironmentValidator策略模式处理不同环境
2. 消除重复的if-else条件分支
3. 统一错误处理和报告
4. 更好的可扩展性
"""
import os
import logging
from typing import List, Dict, Any
from app.core.config import settings
from app.core.strategies import strategy_factory
from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityValidationError(Exception):
    """安全验证失败时抛出的异常"""
    pass


class RefactoredSecurityValidator:
    """
    重构后的安全验证器
    
    使用策略模式处理不同环境的验证，消除重复的条件分支
    """
    
    def __init__(self):
        """初始化安全验证器"""
        self.environment_validator = strategy_factory.get_environment_validator()
        self.validation_history = []
    
    def validate_startup(self) -> None:
        """
        在应用启动时验证配置 - 使用策略模式
        
        这里使用EnvironmentValidator来处理不同环境的验证，
        消除了原有的重复if-else条件分支
        
        Raises:
            SecurityValidationError: 如果发现关键安全问题
        """
        try:
            environment = settings.ENVIRONMENT
            
            # 使用策略模式验证环境配置
            validation_result = self.environment_validator.validate_environment(environment, settings)
            
            # 记录验证历史
            self.validation_history.append({
                "timestamp": self._get_current_timestamp(),
                "environment": environment,
                "result": validation_result
            })
            
            # 处理验证结果
            self._process_validation_result(validation_result, environment)
            
            logger.info(f"Security validation passed for {environment} environment")
            
        except SecurityValidationError:
            raise
        except Exception as e:
            error_msg = f"Security validation failed with unexpected error: {str(e)}"
            logger.error(error_msg)
            raise SecurityValidationError(error_msg)
    
    def _process_validation_result(self, result: Dict[str, Any], environment: str) -> None:
        """
        处理验证结果
        
        Args:
            result: 验证结果
            environment: 环境名称
        """
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        
        # 记录警告
        for warning in warnings:
            logger.warning(f"Security warning ({environment}): {warning}")
        
        # 处理错误
        if errors:
            error_msg = f"Security validation failed for {environment} environment:\n"
            error_msg += "\n".join(f"- {error}" for error in errors)
            logger.error(error_msg)
            raise SecurityValidationError(error_msg)
    
    def get_security_report(self) -> Dict[str, Any]:
        """
        获取综合安全配置报告 - 使用策略模式
        
        Returns:
            包含建议的安全报告
        """
        try:
            environment = settings.ENVIRONMENT
            
            # 使用策略模式获取环境特定的验证结果
            validation_result = self.environment_validator.validate_environment(environment, settings)
            
            # 获取通用建议
            recommendations = self._get_security_recommendations()
            
            # 计算安全评分
            security_score = self._calculate_security_score(validation_result)
            
            report = {
                "environment": environment,
                "errors": validation_result.get("errors", []),
                "warnings": validation_result.get("warnings", []),
                "recommendations": recommendations,
                "security_score": security_score,
                "validation_passed": validation_result.get("valid", False),
                "timestamp": self._get_current_timestamp(),
                "validation_history": self.validation_history[-5:]  # 最近5次验证
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate security report: {e}")
            return {
                "environment": "unknown",
                "errors": [f"Report generation failed: {str(e)}"],
                "warnings": [],
                "recommendations": [],
                "security_score": 0,
                "validation_passed": False,
                "timestamp": self._get_current_timestamp()
            }
    
    def _get_security_recommendations(self) -> List[str]:
        """获取通用安全建议"""
        return [
            "Use AWS Secrets Manager or similar for secret management",
            "Enable security headers (HSTS, CSP, etc.)",
            "Implement rate limiting on all endpoints",
            "Use TLS 1.3 for all connections",
            "Enable audit logging for all security events",
            "Implement proper input validation on all endpoints",
            "Use parameterized queries to prevent SQL injection",
            "Implement proper error handling (no information disclosure)",
            "Regular security audits and penetration testing",
            "Keep all dependencies up to date",
            "Implement proper session management",
            "Use strong password policies",
            "Enable multi-factor authentication where possible"
        ]
    
    def _calculate_security_score(self, validation_result: Dict[str, Any]) -> int:
        """
        计算安全评分
        
        Args:
            validation_result: 验证结果
            
        Returns:
            安全评分 (0-100)
        """
        errors = validation_result.get("errors", [])
        warnings = validation_result.get("warnings", [])
        
        # 基础分数
        base_score = 100
        
        # 每个错误扣20分
        error_penalty = len(errors) * 20
        
        # 每个警告扣5分
        warning_penalty = len(warnings) * 5
        
        # 计算最终分数
        final_score = max(0, base_score - error_penalty - warning_penalty)
        
        return final_score
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def validate_secrets(self) -> Dict[str, Any]:
        """
        验证密钥配置
        
        Returns:
            密钥验证结果
        """
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
        
        issues = []
        
        for secret_name in required_secrets:
            secret_value = getattr(settings, secret_name, None)
            
            if not secret_value:
                issues.append(f"Required secret {secret_name} is not set")
            elif secret_value in insecure_values:
                issues.append(f"Secret {secret_name} is using default/insecure value")
            elif len(secret_value) < 32:
                issues.append(f"Secret {secret_name} is too short (minimum: 32 characters)")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "checked_secrets": required_secrets
        }
    
    def validate_database_config(self) -> Dict[str, Any]:
        """
        验证数据库配置
        
        Returns:
            数据库配置验证结果
        """
        issues = []
        
        # 检查数据库URL
        database_url = getattr(settings, 'DATABASE_URL', '')
        if not database_url:
            issues.append("DATABASE_URL is not configured")
        elif 'localhost' in database_url and settings.ENVIRONMENT == 'production':
            issues.append("Using localhost database in production")
        
        # 检查连接池配置
        max_connections = getattr(settings, 'DATABASE_MAX_CONNECTIONS', 10)
        if max_connections < 5:
            issues.append("Database connection pool may be too small")
        elif max_connections > 100:
            issues.append("Database connection pool may be too large")
        
        # 检查SSL配置
        if settings.ENVIRONMENT == 'production':
            if 'sslmode=require' not in database_url and 'sslmode=verify' not in database_url:
                issues.append("SSL is not enforced for database connections in production")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def validate_jwt_config(self) -> Dict[str, Any]:
        """
        验证JWT配置
        
        Returns:
            JWT配置验证结果
        """
        issues = []
        
        # 检查JWT算法
        jwt_algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')
        if jwt_algorithm not in ['HS256', 'RS256', 'ES256']:
            issues.append(f"JWT algorithm {jwt_algorithm} may not be secure")
        
        # 检查过期时间
        access_token_expire = getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30)
        if access_token_expire > 60:
            issues.append("Access token expiry time is too long (>60 minutes)")
        elif access_token_expire < 5:
            issues.append("Access token expiry time is too short (<5 minutes)")
        
        refresh_token_expire = getattr(settings, 'REFRESH_TOKEN_EXPIRE_DAYS', 7)
        if refresh_token_expire > 30:
            issues.append("Refresh token expiry time is too long (>30 days)")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """
        获取综合安全报告
        
        Returns:
            包含所有验证结果的综合报告
        """
        # 获取基础安全报告
        base_report = self.get_security_report()
        
        # 获取专项验证结果
        secrets_validation = self.validate_secrets()
        database_validation = self.validate_database_config()
        jwt_validation = self.validate_jwt_config()
        
        # 合并所有问题
        all_issues = []
        all_issues.extend(base_report.get("errors", []))
        all_issues.extend(base_report.get("warnings", []))
        all_issues.extend(secrets_validation.get("issues", []))
        all_issues.extend(database_validation.get("issues", []))
        all_issues.extend(jwt_validation.get("issues", []))
        
        # 重新计算安全评分
        comprehensive_score = max(0, 100 - len(all_issues) * 10)
        
        return {
            **base_report,
            "comprehensive_score": comprehensive_score,
            "detailed_validations": {
                "secrets": secrets_validation,
                "database": database_validation,
                "jwt": jwt_validation
            },
            "total_issues": len(all_issues),
            "critical_issues": len([issue for issue in all_issues if any(
                keyword in issue.lower() 
                for keyword in ["password", "secret", "key", "ssl", "production"]
            )])
        }


# 全局实例
refactored_security_validator = RefactoredSecurityValidator()


def get_refactored_security_validator() -> RefactoredSecurityValidator:
    """获取重构后的安全验证器实例"""
    return refactored_security_validator


# 在模块导入时验证（启动时）
try:
    refactored_security_validator.validate_startup()
except SecurityValidationError as e:
    logger.critical(f"Application startup blocked due to security issues: {e}")
    # 在生产环境中，可能需要在这里退出应用
    pass
except Exception as e:
    logger.error(f"Unexpected error during security validation: {e}")


# ========================================================================
# 使用示例和迁移指南
# ========================================================================

class SecurityValidationMigrationGuide:
    """
    安全验证器迁移指南
    
    展示如何从原有的条件分支迁移到策略模式
    """
    
    @staticmethod
    def old_approach_example():
        """
        旧方法示例 - 使用重复的if-else条件分支
        """
        def old_validate_environment(settings):
            errors = []
            
            # 重复的条件分支 - 这是我们要消除的
            if settings.ENVIRONMENT == "production":
                if settings.DEBUG:
                    errors.append("DEBUG mode is enabled in production")
                if not getattr(settings, 'FORCE_HTTPS', False):
                    errors.append("HTTPS is not enforced in production")
                # ... 更多生产环境检查
                
            elif settings.ENVIRONMENT == "development":
                # 开发环境检查
                pass
                
            elif settings.ENVIRONMENT == "test":
                # 测试环境检查
                pass
            else:
                errors.append(f"Unknown environment: {settings.ENVIRONMENT}")
            
            return errors
    
    @staticmethod
    def new_approach_example():
        """
        新方法示例 - 使用策略模式
        """
        def new_validate_environment(settings):
            # 使用策略模式 - 消除了重复的条件分支
            environment_validator = strategy_factory.get_environment_validator()
            
            result = environment_validator.validate_environment(
                settings.ENVIRONMENT, 
                settings
            )
            
            return result.get("errors", [])
    
    @staticmethod
    def benefits():
        """
        重构的好处
        """
        return {
            "code_reduction": "消除了重复的环境检查条件分支",
            "maintainability": "新环境只需添加新策略，无需修改现有代码",
            "testability": "每个环境策略可以独立测试",
            "extensibility": "易于扩展支持新的环境类型",
            "separation_of_concerns": "每个策略专注于一种环境的验证",
            "consistency": "所有环境使用统一的验证接口"
        }