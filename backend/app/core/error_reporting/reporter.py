"""
Error Reporter Module

Handles database error detection, classification, reporting, and tracking.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .types import DatabaseErrorCategory, DatabaseErrorInfo
from .masking import MASKING_RULES
from .statistics_manager import error_stats


from .statistics import ErrorStatistics


class ErrorReporter:
    """
    Comprehensive error reporting system for database operations.
    
    Features:
    - Error classification and categorization
    - Sensitive data masking
    - Error statistics tracking
    - Recent error history
    - Configurable alerting thresholds
    """
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self._alert_thresholds: Dict[DatabaseErrorCategory, int] = {
            DatabaseErrorCategory.CONNECTION_TIMEOUT: 5,
            DatabaseErrorCategory.AUTHENTICATION_FAILURE: 3,
            DatabaseErrorCategory.POOL_EXHAUSTION: 2,
        }
    
    def classify_error(self, error: Exception) -> DatabaseErrorCategory:
        """
        Classify an error into appropriate category.
        
        Args:
            error: The exception to classify
            
        Returns:
            DatabaseErrorCategory for the error
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Connection timeout
        if 'timeout' in error_str or 'timed out' in error_str:
            return DatabaseErrorCategory.CONNECTION_TIMEOUT
        
        # Authentication failure
        if 'auth' in error_str or 'access denied' in error_str or 'permission' in error_str:
            return DatabaseErrorCategory.AUTHENTICATION_FAILURE
        
        # Encoding error
        if 'encoding' in error_str or 'decode' in error_str or 'unicode' in error_str:
            return DatabaseErrorCategory.ENCODING_ERROR
        
        # Compatibility error
        if 'version' in error_str or 'compatibility' in error_str or 'unsupported' in error_str:
            return DatabaseErrorCategory.COMPATIBILITY_ERROR
        
        # Pool exhaustion
        if 'pool' in error_str or 'exhausted' in error_str or 'connection limit' in error_str:
            return DatabaseErrorCategory.POOL_EXHAUSTION
        
        # Network error
        if 'network' in error_str or 'connection refused' in error_str or 'unreachable' in error_str:
            return DatabaseErrorCategory.NETWORK_ERROR
        
        # Configuration error
        if 'config' in error_str or 'setting' in error_str or 'invalid' in error_str:
            return DatabaseErrorCategory.CONFIGURATION_ERROR
        
        # Migration error
        if 'migration' in error_str or 'schema' in error_str or 'alembic' in error_str:
            return DatabaseErrorCategory.MIGRATION_ERROR
        
        # Health check error
        if 'health' in error_str or 'ping' in error_str or 'check' in error_str:
            return DatabaseErrorCategory.HEALTH_CHECK_ERROR
        
        return DatabaseErrorCategory.NETWORK_ERROR
    
    def mask_sensitive_data(self, data: str) -> str:
        """
        Mask sensitive data in error messages.
        
        Args:
            data: String that may contain sensitive data
            
        Returns:
            String with sensitive data masked
        """
        masked_data = data
        for rule in MASKING_RULES:
            try:
                masked_data = rule.pattern.sub(rule.replacement, masked_data)
            except Exception:
                pass
        return masked_data
    
    def extract_error_details(self, error: Exception) -> Dict[str, Any]:
        """
        Extract relevant details from an exception.
        
        Args:
            error: The exception to extract details from
            
        Returns:
            Dictionary containing error details
        """
        details = {
            "error_type": type(error).__name__,
            "error_message": self.mask_sensitive_data(str(error)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if hasattr(error, '__dict__'):
            for key, value in error.__dict__.items():
                if not key.startswith('_'):
                    details[key] = self.mask_sensitive_data(str(value))
        
        return details
    
    def generate_resolution_steps(self, error: Exception, category: DatabaseErrorCategory) -> List[str]:
        """
        Generate suggested resolution steps based on error category.
        
        Args:
            error: The exception
            category: Error category
            
        Returns:
            List of suggested resolution steps
        """
        steps = []
        
        if category == DatabaseErrorCategory.CONNECTION_TIMEOUT:
            steps = [
                "Check database server status",
                "Verify network connectivity",
                "Review connection pool settings",
                "Consider increasing connection timeout",
            ]
        elif category == DatabaseErrorCategory.AUTHENTICATION_FAILURE:
            steps = [
                "Verify credentials are correct",
                "Check user permissions",
                "Review authentication configuration",
                "Check if account is locked",
            ]
        elif category == DatabaseErrorCategory.POOL_EXHAUSTION:
            steps = [
                "Review pool size configuration",
                "Check for connection leaks",
                "Monitor connection usage patterns",
                "Consider increasing pool size",
            ]
        elif category == DatabaseErrorCategory.NETWORK_ERROR:
            steps = [
                "Verify network connectivity",
                "Check firewall rules",
                "Review network configuration",
                "Check DNS resolution",
            ]
        else:
            steps = [
                "Review error details",
                "Check application logs",
                "Verify configuration",
                "Contact system administrator",
            ]
        
        return steps
    
    def report_error(
        self,
        error: Exception,
        component: str,
        context: Optional[Dict[str, Any]] = None,
        connection_params: Optional[Dict[str, str]] = None,
    ) -> DatabaseErrorInfo:
        """
        Report a database error with full context.
        
        Args:
            error: The exception that occurred
            component: Component where error occurred
            context: Additional context information
            connection_params: Connection parameters (masked)
            
        Returns:
            DatabaseErrorInfo object
        """
        category = self.classify_error(error)
        
        # Mask connection parameters
        masked_params = None
        if connection_params:
            masked_params = {
                k: self.mask_sensitive_data(str(v))
                for k, v in connection_params.items()
            }
        
        error_info = DatabaseErrorInfo(
            category=category,
            component=component,
            message=self.mask_sensitive_data(str(error)),
            details=self.extract_error_details(error),
            timestamp=datetime.now(timezone.utc),
            resolution_steps=self.generate_resolution_steps(error, category),
            connection_params=masked_params,
        )
        
        # Update statistics
        error_stats.add_error(error_info)
        
        # Log the error
        self._log_error(error_info, error)
        
        # Check alert threshold
        self._check_alert_threshold(category)
        
        return error_info
    
    def _log_error(self, error_info: DatabaseErrorInfo, original_error: Exception) -> None:
        """Log error with appropriate level based on category."""
        log_message = f"[{error_info.category.value}] {error_info.component}: {error_info.message}"
        
        if error_info.category in [
            DatabaseErrorCategory.AUTHENTICATION_FAILURE,
            DatabaseErrorCategory.CONFIGURATION_ERROR,
        ]:
            self.logger.error(log_message, exc_info=original_error)
        else:
            self.logger.warning(log_message, exc_info=original_error)
    
    def _check_alert_threshold(self, category: DatabaseErrorCategory) -> None:
        """Check if error count exceeds alert threshold."""
        threshold = self._alert_thresholds.get(category)
        if threshold:
            count = error_stats.get_error_count_by_category(category)
            if count >= threshold:
                self.logger.warning(
                    f"Alert: {category.value} errors ({count}) exceeded threshold ({threshold})"
                )
    
    def get_statistics(self) -> ErrorStatistics:
        """Get current error statistics."""
        return error_stats.get_statistics()
    
    def get_recent_errors(self, limit: int = 10) -> List[DatabaseErrorInfo]:
        """Get recent errors."""
        return error_stats.get_recent_errors(limit)
    
    def set_alert_threshold(self, category: DatabaseErrorCategory, threshold: int) -> None:
        """Set alert threshold for a category."""
        self._alert_thresholds[category] = threshold
    
    def get_error_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive error report.
        
        Returns:
            Dictionary containing error report
        """
        stats = self.get_statistics()
        return {
            "summary": {
                "total_errors": sum(stats.error_counts.values()),
                "categories": dict(stats.error_counts),
                "components": dict(stats.component_errors),
            },
            "recent_errors": [e.to_dict() for e in self.get_recent_errors(20)],
            "first_error": stats.first_seen.isoformat() if stats.first_seen else None,
            "last_error": stats.last_seen.isoformat() if stats.last_seen else None,
        }


# Global error reporter instance
error_reporter = ErrorReporter()
