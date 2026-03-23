"""
Prometheus metrics collection for monitoring API performance and business metrics.

This module implements Requirement 7.3: Collect metrics for API response times, 
error rates, and throughput.

Metrics collected:
- HTTP request duration (histogram)
- HTTP request count (counter)
- HTTP requests in progress (gauge)
- Error count by type (counter)
- Custom business metrics (counter, gauge)
"""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from typing import Optional
import time


# Create a custom registry for better control
REGISTRY = CollectorRegistry()

# HTTP Metrics - API response times and throughput (Requirement 7.3)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY,
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method', 'endpoint'],
    registry=REGISTRY
)

# Error Metrics - Error rates (Requirement 7.3)
http_errors_total = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['method', 'endpoint', 'status_code', 'error_type'],
    registry=REGISTRY
)

exception_count = Counter(
    'exception_count',
    'Total exceptions raised',
    ['exception_type', 'endpoint'],
    registry=REGISTRY
)

# Database Metrics - Custom business metrics
database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['database', 'operation'],
    registry=REGISTRY,
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections',
    ['database'],
    registry=REGISTRY
)

database_operations_total = Counter(
    'database_operations_total',
    'Total database operations',
    ['database', 'operation', 'status'],
    registry=REGISTRY
)

# Analysis Metrics - Custom business metrics
code_analysis_duration_seconds = Histogram(
    'code_analysis_duration_seconds',
    'Code analysis duration in seconds',
    ['analysis_type'],
    registry=REGISTRY,
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
)

code_analysis_total = Counter(
    'code_analysis_total',
    'Total code analyses performed',
    ['analysis_type', 'status'],
    registry=REGISTRY
)

code_entities_processed = Counter(
    'code_entities_processed',
    'Total code entities processed',
    ['entity_type'],
    registry=REGISTRY
)

circular_dependencies_detected = Counter(
    'circular_dependencies_detected',
    'Total circular dependencies detected',
    ['severity'],
    registry=REGISTRY
)

# LLM Metrics - Custom business metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['provider', 'model', 'status'],
    registry=REGISTRY
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM API request duration in seconds',
    ['provider', 'model'],
    registry=REGISTRY,
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)
)

llm_tokens_used = Counter(
    'llm_tokens_used',
    'Total LLM tokens used',
    ['provider', 'model', 'token_type'],
    registry=REGISTRY
)

llm_circuit_breaker_state = Gauge(
    'llm_circuit_breaker_state',
    'LLM circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['provider'],
    registry=REGISTRY
)

# Cache Metrics - Custom business metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'status'],
    registry=REGISTRY
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio (0-1)',
    registry=REGISTRY
)

# Task Queue Metrics - Custom business metrics
celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status'],
    registry=REGISTRY
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name'],
    registry=REGISTRY,
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0)
)

celery_queue_length = Gauge(
    'celery_queue_length',
    'Number of tasks in Celery queue',
    ['queue_name'],
    registry=REGISTRY
)

# Authentication Metrics - Custom business metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['method', 'status'],
    registry=REGISTRY
)

active_sessions = Gauge(
    'active_sessions',
    'Number of active user sessions',
    registry=REGISTRY
)

# GitHub Integration Metrics - Custom business metrics
github_webhook_events_total = Counter(
    'github_webhook_events_total',
    'Total GitHub webhook events received',
    ['event_type', 'status'],
    registry=REGISTRY
)

github_api_requests_total = Counter(
    'github_api_requests_total',
    'Total GitHub API requests',
    ['operation', 'status'],
    registry=REGISTRY
)

github_api_rate_limit_remaining = Gauge(
    'github_api_rate_limit_remaining',
    'GitHub API rate limit remaining',
    registry=REGISTRY
)

# Application Metrics - Application info and health
from prometheus_client import Info

app_info = Info(
    'app',
    'Application information',
    registry=REGISTRY
)

health_check_duration_seconds = Histogram(
    'health_check_duration_seconds',
    'Duration of health checks in seconds',
    ['check_type'],
    registry=REGISTRY,
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

dependency_status = Gauge(
    'dependency_status',
    'Status of each dependency (1=healthy, 0=unhealthy)',
    ['dependency_name'],
    registry=REGISTRY
)


def get_metrics() -> bytes:
    """
    Generate Prometheus metrics in text format.
    
    Returns:
        bytes: Prometheus metrics in text format
    """
    return generate_latest(REGISTRY)


def get_content_type() -> str:
    """
    Get the content type for Prometheus metrics.
    
    Returns:
        str: Content type string
    """
    return CONTENT_TYPE_LATEST


class MetricsTimer:
    """
    Context manager for timing operations and recording to Prometheus histogram.
    
    Example:
        with MetricsTimer(http_request_duration_seconds, method='GET', endpoint='/api/users'):
            # ... operation to time ...
            pass
    """
    
    def __init__(self, histogram, **labels):
        """
        Initialize the timer.
        
        Args:
            histogram: Prometheus Histogram metric
            **labels: Labels to apply to the metric
        """
        self.histogram = histogram
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        """Start the timer."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer and record the duration."""
        duration = time.time() - self.start_time
        self.histogram.labels(**self.labels).observe(duration)
        return False


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """
    Record HTTP request metrics.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        status_code: HTTP status code
        duration: Request duration in seconds
    """
    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    ).observe(duration)
    
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    ).inc()
    
    # Record errors
    if status_code >= 400:
        error_type = 'client_error' if status_code < 500 else 'server_error'
        http_errors_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            error_type=error_type
        ).inc()


def record_exception(exception_type: str, endpoint: Optional[str] = None):
    """
    Record exception occurrence.
    
    Args:
        exception_type: Type of exception
        endpoint: API endpoint where exception occurred (optional)
    """
    exception_count.labels(
        exception_type=exception_type,
        endpoint=endpoint or 'unknown'
    ).inc()


def record_database_operation(database: str, operation: str, duration: float, status: str = 'success'):
    """
    Record database operation metrics.
    
    Args:
        database: Database name (postgresql, neo4j, redis)
        operation: Operation type (query, insert, update, delete)
        duration: Operation duration in seconds
        status: Operation status (success, error)
    """
    database_query_duration_seconds.labels(
        database=database,
        operation=operation
    ).observe(duration)
    
    database_operations_total.labels(
        database=database,
        operation=operation,
        status=status
    ).inc()


def record_code_analysis(analysis_type: str, duration: float, status: str = 'success'):
    """
    Record code analysis metrics.
    
    Args:
        analysis_type: Type of analysis (ast_parsing, dependency_graph, llm_review)
        duration: Analysis duration in seconds
        status: Analysis status (success, error)
    """
    code_analysis_duration_seconds.labels(
        analysis_type=analysis_type
    ).observe(duration)
    
    code_analysis_total.labels(
        analysis_type=analysis_type,
        status=status
    ).inc()


def record_llm_request(provider: str, model: str, duration: float, status: str = 'success',
                       prompt_tokens: int = 0, completion_tokens: int = 0):
    """
    Record LLM API request metrics.
    
    Args:
        provider: LLM provider (openai, anthropic)
        model: Model name
        duration: Request duration in seconds
        status: Request status (success, error, rate_limited)
        prompt_tokens: Number of prompt tokens used
        completion_tokens: Number of completion tokens used
    """
    llm_requests_total.labels(
        provider=provider,
        model=model,
        status=status
    ).inc()
    
    llm_request_duration_seconds.labels(
        provider=provider,
        model=model
    ).observe(duration)
    
    if prompt_tokens > 0:
        llm_tokens_used.labels(
            provider=provider,
            model=model,
            token_type='prompt'
        ).inc(prompt_tokens)
    
    if completion_tokens > 0:
        llm_tokens_used.labels(
            provider=provider,
            model=model,
            token_type='completion'
        ).inc(completion_tokens)


def record_cache_operation(operation: str, status: str = 'hit'):
    """
    Record cache operation metrics.
    
    Args:
        operation: Operation type (get, set, delete)
        status: Operation status (hit, miss, success, error)
    """
    cache_operations_total.labels(
        operation=operation,
        status=status
    ).inc()


def record_celery_task(task_name: str, duration: float, status: str = 'success'):
    """
    Record Celery task metrics.
    
    Args:
        task_name: Name of the Celery task
        duration: Task duration in seconds
        status: Task status (success, failure, retry)
    """
    celery_tasks_total.labels(
        task_name=task_name,
        status=status
    ).inc()
    
    celery_task_duration_seconds.labels(
        task_name=task_name
    ).observe(duration)


def record_auth_attempt(method: str, status: str):
    """
    Record authentication attempt metrics.
    
    Args:
        method: Authentication method (login, register, refresh)
        status: Attempt status (success, failure)
    """
    auth_attempts_total.labels(
        method=method,
        status=status
    ).inc()


def record_github_webhook(event_type: str, status: str = 'success'):
    """
    Record GitHub webhook event metrics.
    
    Args:
        event_type: Type of webhook event (pull_request, push, etc.)
        status: Processing status (success, error)
    """
    github_webhook_events_total.labels(
        event_type=event_type,
        status=status
    ).inc()


def record_github_api_request(operation: str, status: str = 'success'):
    """
    Record GitHub API request metrics.
    
    Args:
        operation: API operation (get_pr, post_comment, etc.)
        status: Request status (success, error, rate_limited)
    """
    github_api_requests_total.labels(
        operation=operation,
        status=status
    ).inc()


def set_app_info(version: str, environment: str):
    """
    Set application information metric.
    
    Args:
        version: Application version
        environment: Environment name (production, staging, development)
    """
    app_info.info({
        'version': version,
        'environment': environment
    })


def record_health_check(check_type: str, duration: float):
    """
    Record health check duration.
    
    Args:
        check_type: Type of health check (health, readiness, liveness, dependency)
        duration: Duration in seconds
    """
    health_check_duration_seconds.labels(
        check_type=check_type
    ).observe(duration)


def set_dependency_status(dependency_name: str, is_healthy: bool):
    """
    Set dependency health status.
    
    Args:
        dependency_name: Name of the dependency (PostgreSQL, Neo4j, Redis, etc.)
        is_healthy: True if healthy, False if unhealthy
    """
    dependency_status.labels(
        dependency_name=dependency_name
    ).set(1 if is_healthy else 0)
