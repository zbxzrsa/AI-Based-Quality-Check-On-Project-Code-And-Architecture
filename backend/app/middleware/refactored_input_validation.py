"""
重构后的输入验证中间件 - 使用策略模式消除条件分支

应用的改进：
1. 使用ContentTypeProcessor策略模式处理不同内容类型
2. 消除重复的if-else条件分支
3. 统一错误处理
4. 更好的可扩展性
"""
import re
import logging
from typing import Any, Dict, List, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.strategies import strategy_factory
from app.core.logging import get_logger

logger = get_logger(__name__)


class RefactoredInputValidationMiddleware:
    """
    重构后的输入验证中间件
    
    使用策略模式处理不同的内容类型，消除重复的条件分支
    """
    
    # 危险模式 - 保持原有的安全检查
    DANGEROUS_PATTERNS = [
        # SQL injection patterns
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        
        # XSS patterns
        r"(<script[^>]*>.*?</script>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        
        # Command injection patterns
        r"(;|\||&|`|\$\(|\${)",
        r"(\b(rm|del|format|shutdown|reboot)\b)",
        
        # Path traversal patterns
        r"(\.\./|\.\.\\)",
        r"(/etc/passwd|/etc/shadow)",
        
        # NoSQL injection patterns
        r"(\$where|\$ne|\$gt|\$lt|\$regex)",
    ]
    
    # 编译模式以提高性能
    COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]
    
    # 最大长度限制
    MAX_LENGTHS = {
        "email": 254,
        "username": 50,
        "password": 128,
        "name": 100,
        "description": 1000,
        "url": 2048,
        "default": 500
    }
    
    def __init__(self):
        """初始化验证中间件"""
        self.blocked_requests = 0
        self.validated_requests = 0
        self.content_processor = strategy_factory.get_content_processor()
    
    async def __call__(self, request: Request, call_next):
        """处理请求通过验证中间件"""
        try:
            # 跳过某些端点的验证
            if self._should_skip_validation(request):
                return await call_next(request)
            
            # 验证请求
            await self._validate_request(request)
            
            # 处理请求
            response = await call_next(request)
            
            self.validated_requests += 1
            return response
            
        except HTTPException:
            self.blocked_requests += 1
            raise
        except Exception as e:
            logger.error(f"Input validation middleware error: {e}", exc_info=True)
            self.blocked_requests += 1
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request validation failed"
            )
    
    def _should_skip_validation(self, request: Request) -> bool:
        """检查是否应该跳过验证"""
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        ]
        
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    async def _validate_request(self, request: Request) -> None:
        """验证传入请求数据"""
        # 验证URL路径
        self._validate_path(request.url.path)
        
        # 验证查询参数
        for key, value in request.query_params.items():
            self._validate_string(value, f"query parameter '{key}'")
        
        # 验证请求头（选定的）
        safe_headers = ["user-agent", "referer", "accept", "content-type"]
        for header_name in safe_headers:
            if header_name in request.headers:
                self._validate_string(request.headers[header_name], f"header '{header_name}'")
        
        # 验证请求体（如果存在）
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_body(request)
    
    def _validate_path(self, path: str) -> None:
        """验证URL路径中的危险模式"""
        if self._contains_dangerous_pattern(path):
            logger.warning(f"Dangerous pattern detected in path: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid characters in request path"
            )
        
        # 检查路径遍历
        if "../" in path or "..\\" in path:
            logger.warning(f"Path traversal attempt detected: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path traversal not allowed"
            )
    
    async def _validate_body(self, request: Request) -> None:
        """
        验证请求体内容 - 使用策略模式
        
        这里使用ContentTypeProcessor来处理不同的内容类型，
        消除了原有的重复if-else条件分支
        """
        try:
            # 使用策略模式处理不同的内容类型
            validation_result = await self.content_processor.process_request(request)
            
            if not validation_result.get("valid", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request body validation failed"
                )
            
            # 如果有数据需要进一步验证
            if "data" in validation_result:
                await self._validate_form_data(validation_result["data"])
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Body validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request body format"
            )
    
    async def _validate_form_data(self, form_data: Dict[str, Any]) -> None:
        """验证表单数据中的字符串字段"""
        for key, value in form_data.items():
            if isinstance(value, str):
                self._validate_string(value, f"form field '{key}'")
    
    def _validate_string(self, value: str, field_name: str) -> None:
        """验证字符串值中的危险模式"""
        if not isinstance(value, str):
            return
        
        # 检查长度
        max_length = self.MAX_LENGTHS.get(field_name.lower(), self.MAX_LENGTHS["default"])
        if len(value) > max_length:
            logger.warning(f"Field '{field_name}' exceeds maximum length: {len(value)} > {max_length}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field '{field_name}' is too long"
            )
        
        # 检查危险模式
        if self._contains_dangerous_pattern(value):
            logger.warning(f"Dangerous pattern detected in field '{field_name}': {value[:100]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid characters in field '{field_name}'"
            )
    
    def _contains_dangerous_pattern(self, value: str) -> bool:
        """检查值是否包含危险模式"""
        for pattern in self.COMPILED_PATTERNS:
            if pattern.search(value):
                return True
        return False
    
    def sanitize_html(self, html_content: str) -> str:
        """清理HTML内容以防止XSS"""
        try:
            import bleach
            
            # 允许的安全HTML标签和属性
            allowed_tags = [
                'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote',
                'code', 'pre'
            ]
            
            allowed_attributes = {
                '*': ['class'],
                'a': ['href', 'title'],
                'img': ['src', 'alt', 'width', 'height']
            }
            
            return bleach.clean(
                html_content,
                tags=allowed_tags,
                attributes=allowed_attributes,
                strip=True
            )
        except ImportError:
            logger.warning("bleach not available, skipping HTML sanitization")
            return html_content
    
    def get_stats(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        total_requests = self.validated_requests + self.blocked_requests
        block_rate = (self.blocked_requests / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "validated_requests": self.validated_requests,
            "blocked_requests": self.blocked_requests,
            "total_requests": total_requests,
            "block_rate_percent": round(block_rate, 2)
        }


# 全局实例
refactored_input_validator = RefactoredInputValidationMiddleware()


def get_refactored_input_validator() -> RefactoredInputValidationMiddleware:
    """获取重构后的输入验证中间件实例"""
    return refactored_input_validator


# ========================================================================
# 使用示例和迁移指南
# ========================================================================

class ValidationMigrationGuide:
    """
    验证中间件迁移指南
    
    展示如何从原有的条件分支迁移到策略模式
    """
    
    @staticmethod
    def old_approach_example():
        """
        旧方法示例 - 使用重复的if-else条件分支
        
        这是原有代码的简化版本，展示了重复的模式
        """
        async def old_validate_body(request):
            content_type = request.headers.get("content-type", "")
            
            # 重复的条件分支 - 这是我们要消除的
            if "application/json" in content_type:
                # JSON处理逻辑
                try:
                    # JSON验证
                    pass
                except Exception:
                    raise HTTPException(400, "Invalid JSON")
                    
            elif "application/x-www-form-urlencoded" in content_type:
                # 表单处理逻辑
                try:
                    form_data = await request.form()
                    # 表单验证
                    pass
                except Exception:
                    raise HTTPException(400, "Invalid form data")
                    
            elif "multipart/form-data" in content_type:
                # 多部分表单处理逻辑
                try:
                    form_data = await request.form()
                    # 多部分表单验证
                    pass
                except Exception:
                    raise HTTPException(400, "Invalid multipart data")
            else:
                raise HTTPException(415, "Unsupported content type")
    
    @staticmethod
    def new_approach_example():
        """
        新方法示例 - 使用策略模式
        
        展示如何使用策略模式消除重复的条件分支
        """
        async def new_validate_body(request):
            # 使用策略模式 - 消除了重复的条件分支
            content_processor = strategy_factory.get_content_processor()
            
            try:
                # 策略模式自动选择合适的处理器
                result = await content_processor.process_request(request)
                
                if not result.get("valid"):
                    raise HTTPException(400, "Validation failed")
                    
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(400, f"Processing failed: {e}")
    
    @staticmethod
    def benefits():
        """
        重构的好处
        """
        return {
            "code_reduction": "消除了重复的if-else条件分支",
            "maintainability": "新的内容类型只需添加新策略，无需修改现有代码",
            "testability": "每个策略可以独立测试",
            "extensibility": "易于扩展支持新的内容类型",
            "separation_of_concerns": "每个策略专注于一种内容类型的处理",
            "single_responsibility": "每个类只有一个职责"
        }