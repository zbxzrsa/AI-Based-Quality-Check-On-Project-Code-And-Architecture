"""
Error Reporting Module

A refactored, modular error reporting system with:
- Error classification
- Sensitive data masking
- Statistics tracking
- Alerting capabilities
"""

from .types import DatabaseErrorCategory, DatabaseErrorInfo
from .masking import MaskingRule, mask_sensitive_data, MASKING_RULES
from .statistics import ErrorStatistics
from .statistics_manager import ErrorStatisticsManager, error_stats
from .reporter import ErrorReporter, error_reporter

__all__ = [
    "DatabaseErrorCategory",
    "DatabaseErrorInfo",
    "MaskingRule",
    "mask_sensitive_data",
    "MASKING_RULES",
    "ErrorStatistics",
    "ErrorStatisticsManager",
    "error_stats",
    "ErrorReporter",
    "error_reporter",
]
