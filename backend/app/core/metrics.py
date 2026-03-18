"""
Prometheus metrics configuration.

This module re-exports metrics from prometheus_metrics for backward compatibility.
All metrics are now defined in app.core.prometheus_metrics for consistency.

NOTE: This module is kept for backward compatibility. New code should import
from app.core.prometheus_metrics directly.
"""

from app.core.prometheus_metrics import (
    MetricsTimer,
    app_info,
    celery_queue_length,
    celery_task_duration_seconds,
    celery_tasks_total,
    database_connections_active,
    database_operations_total,
    database_query_duration_seconds,
    dependency_status,
    get_content_type,
    get_metrics,
    health_check_duration_seconds,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
    llm_circuit_breaker_state,
    llm_request_duration_seconds,
    llm_requests_total,
    llm_tokens_used,
    record_auth_attempt,
    record_cache_operation,
    record_celery_task,
    record_code_analysis,
    record_database_operation,
    record_exception,
    record_github_api_request,
    record_github_webhook,
    record_health_check,
    record_http_request,
    record_llm_request,
    set_app_info,
    set_dependency_status,
)

__all__ = [
    "http_request_duration_seconds",
    "http_requests_total",
    "http_requests_in_progress",
    "database_connections_active",
    "database_query_duration_seconds",
    "database_operations_total",
    "celery_tasks_total",
    "celery_task_duration_seconds",
    "celery_queue_length",
    "llm_requests_total",
    "llm_request_duration_seconds",
    "llm_tokens_used",
    "llm_circuit_breaker_state",
    "app_info",
    "health_check_duration_seconds",
    "dependency_status",
    "MetricsTimer",
    "record_http_request",
    "record_exception",
    "record_database_operation",
    "record_code_analysis",
    "record_llm_request",
    "record_cache_operation",
    "record_celery_task",
    "record_auth_attempt",
    "record_github_webhook",
    "record_github_api_request",
    "set_app_info",
    "record_health_check",
    "set_dependency_status",
    "get_metrics",
    "get_content_type",
]
