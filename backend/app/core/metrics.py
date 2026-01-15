"""
Prometheus metrics configuration
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

# API Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed',
    ['method', 'endpoint']
)

# Database Metrics
db_connections_total = Gauge(
    'db_connections_total',
    'Total database connections',
    ['database']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['database', 'operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

db_errors_total = Counter(
    'db_errors_total',
    'Total database errors',
    ['database', 'error_type']
)

# Celery Task Metrics
celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name', 'status'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0]
)

celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

celery_queue_length = Gauge(
    'celery_queue_length',
    'Number of tasks in Celery queue',
    ['queue']
)

# LLM API Metrics
llm_api_requests_total = Counter(
    'llm_api_requests_total',
    'Total LLM API requests',
    ['provider', 'model', 'status']
)

llm_api_duration_seconds = Histogram(
    'llm_api_duration_seconds',
    'LLM API request duration in seconds',
    ['provider', 'model'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0]
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens used',
    ['provider', 'model', 'type']
)

llm_cost_total = Counter(
    'llm_cost_total',
    'Total LLM API cost in USD',
    ['provider', 'model']
)

# Application Info
app_info = Info('app_info', 'Application information')
app_info.info({
    'version': '1.0.0',
    'environment': 'production'
})


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint
        if request.url.path == '/metrics':
            return await call_next(request)
        
        method = request.method
        endpoint = request.url.path
        
        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        
        # Track request duration
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
            
            # Record metrics
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            return response
            
        except Exception as e:
            # Record error
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=500
            ).inc()
            raise
            
        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


# Utility functions for tracking metrics
def track_db_query(database: str, operation: str, duration: float, error: Exception = None):
    """Track database query metrics"""
    db_query_duration_seconds.labels(
        database=database,
        operation=operation
    ).observe(duration)
    
    if error:
        db_errors_total.labels(
            database=database,
            error_type=type(error).__name__
        ).inc()


def track_celery_task(task_name: str, status: str, duration: float):
    """Track Celery task metrics"""
    celery_tasks_total.labels(
        task_name=task_name,
        status=status
    ).inc()
    
    celery_task_duration_seconds.labels(
        task_name=task_name,
        status=status
    ).observe(duration)


def track_llm_request(provider: str, model: str, status: str, duration: float, 
                     prompt_tokens: int, completion_tokens: int, cost: float):
    """Track LLM API request metrics"""
    llm_api_requests_total.labels(
        provider=provider,
        model=model,
        status=status
    ).inc()
    
    llm_api_duration_seconds.labels(
        provider=provider,
        model=model
    ).observe(duration)
    
    llm_tokens_total.labels(
        provider=provider,
        model=model,
        type='prompt'
    ).inc(prompt_tokens)
    
    llm_tokens_total.labels(
        provider=provider,
        model=model,
        type='completion'
    ).inc(completion_tokens)
    
    llm_cost_total.labels(
        provider=provider,
        model=model
    ).inc(cost)


# Create Prometheus ASGI app
metrics_app = make_asgi_app()
