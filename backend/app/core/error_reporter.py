"""
重构后的错误报告器 - 主要协调器
整合敏感数据掩码和数据库错误分类功能
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from .error_types import DatabaseErrorCategory, DatabaseErrorInfo, ErrorStatistics
from .sensitive_data_masker import SensitiveDataMasker
from .database_error_classifier import DatabaseErrorClassifier

logger = logging.getLogger(__name__)


class ErrorReporter:
    """
    重构后的错误报告器
    提供敏感数据掩码和数据库错误分类功能
    """
    
    def __init__(self):
        self.masker = SensitiveDataMasker()
        self.classifier = DatabaseErrorClassifier()
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志记录"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 确保有处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    @staticmethod
    def classify_database_error(error: Exception, component: str = "database") -> DatabaseErrorCategory:
        """Static method for backward compatibility"""
        reporter = get_error_reporter()
        error_info = reporter.classifier.classify_error(str(error), component)
        return error_info.category
    
    @staticmethod
    def create_database_error_info(
        error: Exception,
        component: str = "database",
        error_code: Optional[str] = None,
        connection_params: Optional[Dict[str, Any]] = None
    ) -> DatabaseErrorInfo:
        """Static method for backward compatibility"""
        reporter = get_error_reporter()
        return reporter.classifier.classify_error(
            error_message=str(error),
            component=component,
            details={
                "error_type": type(error).__name__,
                "error_code": error_code,
                "connection_params": connection_params or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    @staticmethod
    def log_database_error(
        error_info: DatabaseErrorInfo,
        logger: Optional[logging.Logger] = None,
        include_details: bool = True
    ):
        """Static method for backward compatibility"""
        reporter = get_error_reporter()
        if logger:
            # Use provided logger
            log_data = {
                "error_id": id(error_info),
                "category": error_info.category.value,
                "component": error_info.component,
                "message": error_info.message,
                "timestamp": error_info.timestamp.isoformat(),
            }
            if include_details:
                log_data["details"] = error_info.details
            logger.error("Database error occurred", extra=log_data)
        else:
            # Use instance method
            reporter._log_error(error_info)
    
    @staticmethod
    def get_error_statistics() -> ErrorStatistics:
        """Static method for backward compatibility"""
        return get_error_reporter().get_error_statistics()
    
    @staticmethod
    def reset_error_statistics():
        """Static method for backward compatibility"""
        get_error_reporter().reset_statistics()
    
    @staticmethod
    def mask_sensitive_data(text: str) -> str:
        """Static method for backward compatibility"""
        return get_error_reporter().mask_text(text)
    
    @staticmethod
    def format_structured_error_message(
        error_info: DatabaseErrorInfo,
        include_resolution_steps: bool = False
    ) -> str:
        """Format structured error message"""
        reporter = get_error_reporter()
        message = reporter.get_error_report(error_info)
        
        if include_resolution_steps:
            tips = reporter.get_troubleshooting_tips(error_info.category)
            if tips:
                message += "\n\nResolution Steps:\n" + "\n".join(f"- {tip}" for tip in tips)
        
        return message
    
    @staticmethod
    def _get_resolution_steps(category: DatabaseErrorCategory, component: str) -> List[str]:
        """Get resolution steps for error category"""
        return get_error_reporter().get_troubleshooting_tips(category)
    
    def report_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        component: str = "unknown",
        mask_sensitive: bool = True
    ) -> DatabaseErrorInfo:
        """
        报告错误并进行分类和掩码处理
        
        Args:
            error: 异常对象
            context: 错误上下文信息
            component: 组件名称
            mask_sensitive: 是否掩码敏感数据
            
        Returns:
            分类后的错误信息
        """
        error_message = str(error)
        
        # 掩码敏感数据
        if mask_sensitive:
            error_message = self.masker.mask_sensitive_data(error_message)
            if context:
                context = self.masker.mask_dict(context)
        
        # 分类错误
        error_info = self.classifier.classify_error(
            error_message=error_message,
            component=component,
            details={
                "error_type": type(error).__name__,
                "context": context or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # 记录到日志
        self._log_error(error_info)
        
        return error_info
    
    def report_database_error(
        self,
        error_message: str,
        component: str = "database",
        details: Optional[Dict[str, Any]] = None,
        mask_sensitive: bool = True
    ) -> DatabaseErrorInfo:
        """
        报告数据库错误
        
        Args:
            error_message: 错误消息
            component: 组件名称
            details: 错误详情
            mask_sensitive: 是否掩码敏感数据
            
        Returns:
            分类后的错误信息
        """
        # 掩码敏感数据
        if mask_sensitive:
            error_message = self.masker.mask_sensitive_data(error_message)
            if details:
                details = self.masker.mask_dict(details)
        
        # 分类错误
        error_info = self.classifier.classify_error(
            error_message=error_message,
            component=component,
            details=details or {}
        )
        
        # 记录到日志
        self._log_error(error_info)
        
        return error_info
    
    def _log_error(self, error_info: DatabaseErrorInfo):
        """记录错误到日志"""
        log_data = {
            "error_id": id(error_info),
            "category": error_info.category.value,
            "component": error_info.component,
            "message": error_info.message,
            "timestamp": error_info.timestamp.isoformat(),
            "details": error_info.details
        }
        
        # 根据错误严重程度选择日志级别
        if error_info.category in [
            DatabaseErrorCategory.CONNECTION_TIMEOUT,
            DatabaseErrorCategory.POOL_EXHAUSTION,
            DatabaseErrorCategory.NETWORK_ERROR
        ]:
            self.logger.error("Database error occurred", extra=log_data)
        elif error_info.category in [
            DatabaseErrorCategory.AUTHENTICATION_FAILURE,
            DatabaseErrorCategory.CONFIGURATION_ERROR
        ]:
            self.logger.warning("Database configuration issue", extra=log_data)
        else:
            self.logger.info("Database event", extra=log_data)
    
    def get_error_statistics(self) -> ErrorStatistics:
        """获取错误统计信息"""
        return self.classifier.get_error_statistics()
    
    def reset_statistics(self):
        """重置错误统计"""
        self.classifier.reset_statistics()
    
    def get_error_report(self, error_info: DatabaseErrorInfo) -> str:
        """获取格式化的错误报告"""
        return self.classifier.format_error_report(error_info)
    
    def mask_text(self, text: str) -> str:
        """掩码文本中的敏感数据"""
        return self.masker.mask_sensitive_data(text)
    
    def mask_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """掩码字典中的敏感数据"""
        return self.masker.mask_dict(data)
    
    def add_masking_rule(self, pattern: str, replacement: str, description: str = ""):
        """添加自定义掩码规则"""
        from .error_types import MaskingRule, SensitiveDataType
        
        rule = MaskingRule(
            pattern=pattern,
            replacement=replacement,
            data_type=SensitiveDataType.TOKEN,  # 默认类型
            description=description
        )
        self.masker.add_custom_rule(rule)
    
    def add_error_pattern(self, category: DatabaseErrorCategory, pattern: str):
        """添加自定义错误模式"""
        self.classifier.add_custom_pattern(category, pattern)
    
    def get_troubleshooting_tips(self, category: DatabaseErrorCategory) -> List[str]:
        """获取故障排除建议"""
        return self.classifier.get_troubleshooting_tips(category)
    
    def health_check(self) -> Dict[str, Any]:
        """错误报告器健康检查"""
        stats = self.get_error_statistics()
        
        return {
            "status": "healthy",
            "total_errors": stats.total_errors,
            "error_rate": stats.error_rate_per_minute,
            "masking_rules": len(self.masker.masking_rules),
            "error_patterns": sum(len(patterns) for patterns in self.classifier.error_patterns.values()),
            "last_error": stats.last_error_time.isoformat() if stats.last_error_time else None
        }


# 全局错误报告器实例
_global_error_reporter = None


def get_error_reporter() -> ErrorReporter:
    """获取全局错误报告器实例"""
    global _global_error_reporter
    if _global_error_reporter is None:
        _global_error_reporter = ErrorReporter()
    return _global_error_reporter


def report_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    component: str = "unknown"
) -> DatabaseErrorInfo:
    """便捷函数：报告错误"""
    return get_error_reporter().report_error(error, context, component)


def report_database_error(
    error_message: str,
    component: str = "database",
    details: Optional[Dict[str, Any]] = None
) -> DatabaseErrorInfo:
    """便捷函数：报告数据库错误"""
    return get_error_reporter().report_database_error(error_message, component, details)


def mask_sensitive_data(text: str) -> str:
    """便捷函数：掩码敏感数据"""
    return get_error_reporter().mask_text(text)