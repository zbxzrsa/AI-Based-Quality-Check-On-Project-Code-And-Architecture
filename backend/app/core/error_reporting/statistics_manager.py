"""
Statistics Manager Module

Global error statistics management.
"""

from typing import Dict, List

from .types import DatabaseErrorCategory, DatabaseErrorInfo
from .statistics import ErrorStatistics


class ErrorStatisticsManager:
    """Manages global error statistics"""

    def __init__(self):
        self._stats = ErrorStatistics()

    def add_error(self, error_info: DatabaseErrorInfo) -> None:
        """Add an error to statistics"""
        self._stats.add_error(error_info)

    def get_statistics(self) -> ErrorStatistics:
        """Get current error statistics"""
        return self._stats

    def get_error_count_by_category(self, category: DatabaseErrorCategory) -> int:
        """Get error count for a specific category"""
        return self._stats.error_counts.get(category, 0)

    def get_error_count_by_component(self, component: str) -> int:
        """Get error count for a specific component"""
        return self._stats.component_errors.get(component, 0)

    def get_recent_errors(self, limit: int = 10) -> List[DatabaseErrorInfo]:
        """Get most recent errors"""
        return self._stats.recent_errors[-limit:]

    def clear_statistics(self) -> None:
        """Clear all statistics"""
        self._stats = ErrorStatistics()

    def to_dict(self) -> Dict:
        """Export statistics as dictionary"""
        return self._stats.to_dict()


# Global instance
error_stats = ErrorStatisticsManager()
