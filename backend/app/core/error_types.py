"""
错误类型定义和数据结构
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


class SensitiveDataType(Enum):
    """需要掩码的敏感数据类型"""
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    CONNECTION_STRING = "connection_string"
    JWT_SECRET = "jwt_secret"
    DATABASE_URL = "database_url"
    WEBHOOK_SECRET = "webhook_secret"


class DatabaseErrorCategory(Enum):
    """数据库连接错误分类"""
    CONNECTION_TIMEOUT = "connection_timeout"
    AUTHENTICATION_FAILURE = "authentication_failure"
    ENCODING_ERROR = "encoding_error"
    COMPATIBILITY_ERROR = "compatibility_error"
    POOL_EXHAUSTION = "pool_exhaustion"
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"
    MIGRATION_ERROR = "migration_error"
    HEALTH_CHECK_ERROR = "health_check_error"


@dataclass
class DatabaseErrorInfo:
    """结构化数据库错误信息"""
    category: DatabaseErrorCategory
    component: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime


@dataclass
class ErrorStatistics:
    """错误统计信息"""
    error_counts: Dict[DatabaseErrorCategory, int] = field(default_factory=dict)
    total_errors: int = 0
    first_error_time: datetime = None
    last_error_time: datetime = None
    error_rate_per_minute: float = 0.0
    
    def add_error(self, category: DatabaseErrorCategory, timestamp: datetime):
        """添加错误统计"""
        self.error_counts[category] = self.error_counts.get(category, 0) + 1
        self.total_errors += 1
        
        if self.first_error_time is None:
            self.first_error_time = timestamp
        self.last_error_time = timestamp
        
        # 计算错误率
        if self.first_error_time and self.last_error_time:
            duration_minutes = (self.last_error_time - self.first_error_time).total_seconds() / 60
            if duration_minutes > 0:
                self.error_rate_per_minute = self.total_errors / duration_minutes


@dataclass
class MaskingRule:
    """敏感数据掩码规则"""
    pattern: str  # 匹配的正则表达式模式
    replacement: str  # 替换字符串
    data_type: SensitiveDataType  # 数据类型
    description: str  # 规则描述