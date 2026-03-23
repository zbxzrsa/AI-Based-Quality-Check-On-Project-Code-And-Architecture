"""
数据库错误分类器
分析和分类数据库相关错误
"""

import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from .error_types import DatabaseErrorCategory, DatabaseErrorInfo, ErrorStatistics


class DatabaseErrorClassifier:
    """数据库错误分类器"""
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.statistics = ErrorStatistics()
    
    def _initialize_error_patterns(self) -> Dict[DatabaseErrorCategory, List[str]]:
        """初始化错误模式"""
        return {
            DatabaseErrorCategory.CONNECTION_TIMEOUT: [
                r'connection.*timeout',
                r'timeout.*connection',
                r'connection.*timed out',
                r'server.*timeout',
                r'read timeout',
                r'connect timeout'
            ],
            
            DatabaseErrorCategory.AUTHENTICATION_FAILURE: [
                r'authentication.*failed',
                r'login.*failed',
                r'invalid.*credentials',
                r'access.*denied',
                r'permission.*denied',
                r'unauthorized',
                r'invalid.*password',
                r'invalid.*username'
            ],
            
            DatabaseErrorCategory.ENCODING_ERROR: [
                r'encoding.*error',
                r'character.*encoding',
                r'unicode.*error',
                r'decode.*error',
                r'invalid.*encoding',
                r'charset.*error'
            ],
            
            DatabaseErrorCategory.COMPATIBILITY_ERROR: [
                r'version.*mismatch',
                r'incompatible.*version',
                r'protocol.*error',
                r'unsupported.*version',
                r'driver.*version',
                r'client.*version'
            ],
            
            DatabaseErrorCategory.POOL_EXHAUSTION: [
                r'pool.*exhausted',
                r'connection.*pool.*full',
                r'too many.*connections',
                r'max.*connections',
                r'pool.*timeout',
                r'no.*available.*connections'
            ],
            
            DatabaseErrorCategory.NETWORK_ERROR: [
                r'network.*error',
                r'connection.*refused',
                r'host.*unreachable',
                r'network.*unreachable',
                r'connection.*reset',
                r'broken.*pipe',
                r'socket.*error'
            ],
            
            DatabaseErrorCategory.CONFIGURATION_ERROR: [
                r'configuration.*error',
                r'invalid.*configuration',
                r'missing.*configuration',
                r'config.*error',
                r'parameter.*error',
                r'setting.*error'
            ],
            
            DatabaseErrorCategory.MIGRATION_ERROR: [
                r'migration.*failed',
                r'schema.*error',
                r'table.*not.*found',
                r'column.*not.*found',
                r'constraint.*violation',
                r'foreign.*key.*constraint'
            ],
            
            DatabaseErrorCategory.HEALTH_CHECK_ERROR: [
                r'health.*check.*failed',
                r'ping.*failed',
                r'database.*not.*responding',
                r'service.*unavailable',
                r'database.*down'
            ]
        }
    
    def classify_error(
        self, 
        error_message: str, 
        component: str = "unknown",
        details: Optional[Dict[str, Any]] = None
    ) -> DatabaseErrorInfo:
        """
        分类数据库错误
        
        Args:
            error_message: 错误消息
            component: 组件名称
            details: 额外的错误详情
            
        Returns:
            分类后的错误信息
        """
        if not error_message:
            error_message = "Unknown error"
        
        if details is None:
            details = {}
        
        # 尝试匹配错误模式
        category = self._match_error_pattern(error_message.lower())
        
        # 创建错误信息
        error_info = DatabaseErrorInfo(
            category=category,
            component=component,
            message=error_message,
            details=details,
            timestamp=datetime.now(timezone.utc)
        )
        
        # 更新统计信息
        self.statistics.add_error(category, error_info.timestamp)
        
        return error_info
    
    def _match_error_pattern(self, error_message: str) -> DatabaseErrorCategory:
        """匹配错误模式"""
        for category, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return category
        
        # 默认分类
        return DatabaseErrorCategory.CONFIGURATION_ERROR
    
    def get_error_statistics(self) -> ErrorStatistics:
        """获取错误统计信息"""
        return self.statistics
    
    def reset_statistics(self):
        """重置统计信息"""
        self.statistics = ErrorStatistics()
    
    def add_custom_pattern(self, category: DatabaseErrorCategory, pattern: str):
        """添加自定义错误模式"""
        if category not in self.error_patterns:
            self.error_patterns[category] = []
        self.error_patterns[category].append(pattern)
    
    def get_category_description(self, category: DatabaseErrorCategory) -> str:
        """获取错误分类描述"""
        descriptions = {
            DatabaseErrorCategory.CONNECTION_TIMEOUT: "连接超时错误",
            DatabaseErrorCategory.AUTHENTICATION_FAILURE: "认证失败错误",
            DatabaseErrorCategory.ENCODING_ERROR: "编码错误",
            DatabaseErrorCategory.COMPATIBILITY_ERROR: "兼容性错误",
            DatabaseErrorCategory.POOL_EXHAUSTION: "连接池耗尽错误",
            DatabaseErrorCategory.NETWORK_ERROR: "网络错误",
            DatabaseErrorCategory.CONFIGURATION_ERROR: "配置错误",
            DatabaseErrorCategory.MIGRATION_ERROR: "迁移错误",
            DatabaseErrorCategory.HEALTH_CHECK_ERROR: "健康检查错误"
        }
        return descriptions.get(category, "未知错误类型")
    
    def get_troubleshooting_tips(self, category: DatabaseErrorCategory) -> List[str]:
        """获取故障排除建议"""
        tips = {
            DatabaseErrorCategory.CONNECTION_TIMEOUT: [
                "检查网络连接",
                "增加连接超时时间",
                "检查防火墙设置",
                "验证数据库服务是否运行"
            ],
            DatabaseErrorCategory.AUTHENTICATION_FAILURE: [
                "验证用户名和密码",
                "检查用户权限",
                "确认数据库用户存在",
                "检查认证配置"
            ],
            DatabaseErrorCategory.ENCODING_ERROR: [
                "检查字符编码设置",
                "验证数据库字符集",
                "检查客户端编码配置",
                "确认数据格式正确"
            ],
            DatabaseErrorCategory.POOL_EXHAUSTION: [
                "增加连接池大小",
                "检查连接泄漏",
                "优化查询性能",
                "实施连接池监控"
            ],
            DatabaseErrorCategory.NETWORK_ERROR: [
                "检查网络连接",
                "验证主机名和端口",
                "检查DNS解析",
                "确认网络路由"
            ]
        }
        return tips.get(category, ["联系系统管理员"])
    
    def format_error_report(self, error_info: DatabaseErrorInfo) -> str:
        """格式化错误报告"""
        report = f"""
数据库错误报告
================
时间: {error_info.timestamp.isoformat()}
组件: {error_info.component}
分类: {self.get_category_description(error_info.category)}
消息: {error_info.message}

故障排除建议:
{chr(10).join(f"- {tip}" for tip in self.get_troubleshooting_tips(error_info.category))}

详细信息:
{error_info.details}
"""
        return report.strip()