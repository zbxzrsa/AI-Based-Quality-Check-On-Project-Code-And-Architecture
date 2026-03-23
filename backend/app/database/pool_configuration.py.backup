"""
优化后的数据库连接池配置 - 内存优化版本
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime

import asyncpg
from app.database.models import HealthState

logger = logging.getLogger(__name__)


@dataclass
class PoolConfiguration:
    """内存优化的数据库连接池配置"""
    min_size: int = 1  # 减少最小连接数
    max_size: int = 5  # 减少最大连接数
    connection_timeout: float = 10.0
    command_timeout: float = 10.0
    max_queries: int = 5000  # 减少查询缓存
    max_inactive_connection_lifetime: float = 120.0
    pool_recycle_time: float = 900.0  # 15分钟回收
    health_check_interval: float = 180.0  # 3分钟检查
    
    def __post_init__(self):
        """验证连接池配置"""
        if self.min_size < 0:
            raise ValueError("min_size must be non-negative")
        if self.max_size <= 0:
            raise ValueError("max_size must be positive")
        if self.max_size < self.min_size:
            raise ValueError("max_size must be >= min_size")
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")


@dataclass
class PoolStats:
    """连接池统计信息"""
    service: str
    size: int = 0
    freesize: int = 0
    max_size: int = 0
    min_size: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_connections_created: int = 0
    total_connections_closed: int = 0
    pool_hits: int = 0
    pool_misses: int = 0
    connection_timeouts: int = 0
    failed_connections: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    health_status: HealthState = HealthState.UNKNOWN
    
    def update_from_asyncpg_pool(self, pool: asyncpg.Pool):
        """从asyncpg连接池更新统计信息"""
        self.size = pool.get_size()
        self.freesize = pool.get_idle_size()
        self.active_connections = self.size - self.freesize
        self.idle_connections = self.freesize
        self.last_updated = datetime.now()
        
        # 基于连接池使用率确定健康状态
        utilization = self.active_connections / self.max_size if self.max_size > 0 else 0
        if utilization < 0.6:  # 降低阈值
            self.health_status = HealthState.HEALTHY
        elif utilization < 0.8:  # 降低阈值
            self.health_status = HealthState.DEGRADED
        else:
            self.health_status = HealthState.UNHEALTHY
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'service': self.service,
            'size': self.size,
            'freesize': self.freesize,
            'max_size': self.max_size,
            'min_size': self.min_size,
            'active_connections': self.active_connections,
            'idle_connections': self.idle_connections,
            'total_connections_created': self.total_connections_created,
            'total_connections_closed': self.total_connections_closed,
            'pool_hits': self.pool_hits,
            'pool_misses': self.pool_misses,
            'connection_timeouts': self.connection_timeouts,
            'failed_connections': self.failed_connections,
            'last_updated': self.last_updated.isoformat(),
            'health_status': self.health_status.value,
            'utilization_percent': round((self.active_connections / self.max_size * 100) if self.max_size > 0 else 0, 1)
        }
