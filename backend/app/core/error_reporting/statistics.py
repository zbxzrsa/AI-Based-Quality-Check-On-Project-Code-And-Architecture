"""
Error Statistics Module

Tracks error patterns and statistics for monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .types import DatabaseErrorCategory, DatabaseErrorInfo


@dataclass
class ErrorStatistics:
    """Error statistics for pattern identification"""
    error_counts: Dict[DatabaseErrorCategory, int] = field(default_factory=dict)
    component_errors: Dict[str, int] = field(default_factory=dict)
    recent_errors: List[DatabaseErrorInfo] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    def add_error(self, error_info: DatabaseErrorInfo) -> None:
        """Add error to statistics"""
        self.error_counts[error_info.category] = self.error_counts.get(error_info.category, 0) + 1
        self.component_errors[error_info.component] = self.component_errors.get(error_info.component, 0) + 1

        if self.first_seen is None:
            self.first_seen = error_info.timestamp
        self.last_seen = error_info.timestamp

        self.recent_errors.append(error_info)
        if len(self.recent_errors) > 50:
            self.recent_errors.pop(0)

    def get_most_frequent_category(self) -> Optional[DatabaseErrorCategory]:
        """Get the most frequent error category"""
        if not self.error_counts:
            return None
        return max(self.error_counts.items(), key=lambda x: x[1])[0]

    def get_most_problematic_component(self) -> Optional[str]:
        """Get the component with most errors"""
        if not self.component_errors:
            return None
        return max(self.component_errors.items(), key=lambda x: x[1])[0]

    def to_dict(self) -> Dict[str, Any]:
        """Export statistics as dictionary"""
        return {
            "error_counts": {k.value: v for k, v in self.error_counts.items()},
            "component_errors": dict(self.component_errors),
            "recent_errors_count": len(self.recent_errors),
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
