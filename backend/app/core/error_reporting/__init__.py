"""
Error Reporting Module

A refactored, modular error reporting system with:
- Error classification
- Sensitive data masking
- Statistics tracking
- Alerting capabilities
"""

from .masking import MASKING_RULES, MaskingRule, mask_sensitive_data
from .reporter import ErrorReporter, error_reporter
from .statistics import ErrorStatistics
from .statistics_manager import ErrorStatisticsManager, error_stats
from .types import DatabaseErrorCategory, DatabaseErrorInfo

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
