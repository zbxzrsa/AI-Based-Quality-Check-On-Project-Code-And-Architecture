"""
Celery configuration with Redis backend for asynchronous task processing.

This module configures Celery with:
- Redis as message broker and result backend
- Task routing with priority queues (high, default, low)
- Task execution settings with retries and timeouts
- Periodic task scheduling with Celery Beat
- Result backend configuration for task tracking

Validates Requirements: 10.7 (Asynchronous task processing using Celery)
"""
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
from kombu import Queue, Exchange
import os

from app.core.config import settings


# Create Celery app with Redis broker and result backend
celery_app = Celery(
    "ai_code_review",
    broker=settings.celery_broker_url_value,
    backend=settings.celery_result_backend_url
)

# Define task exchanges and queues for priority routing
default_exchange = Exchange('default', type='direct')
high_priority_exchange = Exchange('high_priority', type='direct')
low_priority_exchange = Exchange('low_priority', type='direct')

# Configuration
celery_app.conf.update(
    # ========================================
    # BROKER SETTINGS (Redis)
    # ========================================
    broker_url=settings.celery_broker_url_value,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # ========================================
    # RESULT BACKEND SETTINGS (Redis)
    # ========================================
    result_backend=settings.celery_result_backend_url,
    result_backend_transport_options={
        'master_name': 'mymaster',  # For Redis Sentinel in production
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {
            1: 1,  # TCP_KEEPIDLE
            2: 1,  # TCP_KEEPINTVL
            3: 5,  # TCP_KEEPCNT
        },
    },
    result_expires=1800,  # 减少到30分钟过期时间
    result_persistent=True,  # Persist results to disk
    result_compression='gzip',  # Compress results to save memory
    result_extended=False,  # 禁用扩展元数据以节省内存
    
    # ========================================
    # SERIALIZATION
    # ========================================
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # ========================================
    # TIMEZONE
    # ========================================
    timezone='UTC',
    enable_utc=True,
    
    # ========================================
    # TASK EXECUTION SETTINGS - 内存优化
    # ========================================
    task_acks_late=True,  # Acknowledge tasks after execution (not before)
    task_reject_on_worker_lost=True,  # Requeue tasks if worker crashes
    task_track_started=True,  # Track when tasks start execution
    task_time_limit=1800,  # 减少到30分钟硬限制
    task_soft_time_limit=1500,  # 减少到25分钟软限制
    task_ignore_result=False,  # Store task results
    task_store_errors_even_if_ignored=True,  # Store errors even if result is ignored
    task_compression='gzip',  # 启用任务压缩节省内存
    
    # ========================================
    # TASK ROUTING AND PRIORITY QUEUES
    # ========================================
    task_queues=(
        # High priority queue for urgent tasks (PR analysis, webhook responses)
        Queue(
            'high_priority',
            exchange=high_priority_exchange,
            routing_key='high_priority',
            priority=10,
            queue_arguments={'x-max-priority': 10}
        ),
        # Default queue for normal tasks
        Queue(
            'default',
            exchange=default_exchange,
            routing_key='default',
            priority=5,
            queue_arguments={'x-max-priority': 10}
        ),
        # Low priority queue for background tasks (drift detection, cleanup)
        Queue(
            'low_priority',
            exchange=low_priority_exchange,
            routing_key='low_priority',
            priority=1,
            queue_arguments={'x-max-priority': 10}
        ),
    ),
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Task routing - map tasks to specific queues
    task_routes={
        # High priority: PR analysis and webhook handling
        'app.tasks.pull_request_analysis.analyze_pull_request': {
            'queue': 'high_priority',
            'routing_key': 'high_priority',
            'priority': 10
        },
        'app.tasks.pull_request_analysis.parse_pull_request_files': {
            'queue': 'high_priority',
            'routing_key': 'high_priority',
            'priority': 9
        },
        'app.tasks.pull_request_analysis.post_review_comments': {
            'queue': 'high_priority',
            'routing_key': 'high_priority',
            'priority': 8
        },
        
        # Default priority: AST parsing, graph building, LLM analysis
        'app.tasks.ast_parsing.*': {
            'queue': 'default',
            'routing_key': 'default',
            'priority': 5
        },
        'app.tasks.graph_building.*': {
            'queue': 'default',
            'routing_key': 'default',
            'priority': 5
        },
        'app.tasks.llm_analysis.*': {
            'queue': 'default',
            'routing_key': 'default',
            'priority': 5
        },
        
        # Low priority: Architectural drift, cleanup, periodic tasks
        'app.tasks.architectural_drift.detect_architectural_drift': {
            'queue': 'low_priority',
            'routing_key': 'low_priority',
            'priority': 2
        },
        'app.tasks.architectural_drift.detect_cyclic_dependencies': {
            'queue': 'low_priority',
            'routing_key': 'low_priority',
            'priority': 2
        },
        'app.tasks.architectural_drift.detect_layer_violations': {
            'queue': 'low_priority',
            'routing_key': 'low_priority',
            'priority': 2
        },
        'app.tasks.cleanup.*': {
            'queue': 'low_priority',
            'routing_key': 'low_priority',
            'priority': 1
        },
        'app.tasks.generate_project_documentation': {
            'queue': 'low_priority',
            'routing_key': 'low_priority',
            'priority': 1
        },
    },
    
    # ========================================
    # WORKER CONFIGURATION - 内存优化
    # ========================================
    worker_prefetch_multiplier=1,  # Fetch one task at a time for fair distribution
    worker_max_tasks_per_child=500,  # 减少到500个任务后重启worker (防止内存泄漏)
    worker_max_memory_per_child=200000,  # 限制每个worker最大内存200MB
    worker_concurrency=2,  # 限制并发worker数量
    worker_disable_rate_limits=False,  # Enable rate limiting
    worker_send_task_events=False,  # 禁用事件发送以节省内存
    
    # ========================================
    # RETRY CONFIGURATION
    # ========================================
    task_default_retry_delay=60,  # 1 minute delay between retries
    task_max_retries=3,  # Maximum 3 retry attempts
    task_autoretry_for=(Exception,),  # Auto-retry on any exception
    task_retry_backoff=True,  # Use exponential backoff
    task_retry_backoff_max=600,  # Maximum 10 minutes backoff
    task_retry_jitter=True,  # Add random jitter to prevent thundering herd
    
    # ========================================
    # RATE LIMITING
    # ========================================
    task_default_rate_limit='10/m',  # 10 tasks per minute by default
    task_annotations={
        'app.tasks.pull_request_analysis.analyze_pull_request': {'rate_limit': '5/m'},
        'app.tasks.llm_analysis.*': {'rate_limit': '10/m'},  # LLM API rate limits
        'app.tasks.architectural_drift.*': {'rate_limit': '2/m'},
    },
    
    # ========================================
    # MONITORING AND EVENTS
    # ========================================
    task_send_sent_event=True,  # Send event when task is sent
    
    # ========================================
    # BEAT SCHEDULE (Periodic Tasks)
    # ========================================
    beat_schedule={
        # Weekly drift detection - Every Monday at 2 AM UTC
        'detect-drift-weekly': {
            'task': 'app.tasks.architectural_drift.detect_architectural_drift',
            'schedule': crontab(day_of_week='monday', hour=2, minute=0),
            'args': ('*',),  # Analyze all projects
            'kwargs': {'baseline_version': 'latest'},
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 2,
                'expires': 86400  # Expire after 24 hours
            }
        },
        
        # Daily cycle detection - Every day at 3 AM UTC
        'detect-cycles-daily': {
            'task': 'app.tasks.architectural_drift.detect_cyclic_dependencies',
            'schedule': crontab(hour=3, minute=0),
            'args': ('*',),
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 2,
                'expires': 86400
            }
        },
        
        # Twice weekly layer violation check - Monday and Thursday at 4 AM UTC
        'detect-violations-twice-weekly': {
            'task': 'app.tasks.architectural_drift.detect_layer_violations',
            'schedule': crontab(day_of_week='monday,thursday', hour=4, minute=0),
            'args': ('*',),
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 2,
                'expires': 86400
            }
        },
        
        # Data cleanup - Daily at 2 AM UTC
        'cleanup-old-analysis-results': {
            'task': 'app.tasks.data_cleanup.cleanup_old_analysis_results',
            'schedule': crontab(hour=2, minute=0),
            'kwargs': {'dry_run': False},
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 1,
                'expires': 86400
            }
        },
        
        # Cleanup expired sessions - Daily at 2:30 AM UTC
        'cleanup-expired-sessions': {
            'task': 'app.tasks.data_cleanup.cleanup_expired_sessions',
            'schedule': crontab(hour=2, minute=30),
            'kwargs': {'dry_run': False},
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 1,
                'expires': 86400
            }
        },
        
        # Cleanup old architectural baselines - Weekly on Sunday at 3 AM UTC
        'cleanup-old-baselines': {
            'task': 'app.tasks.data_cleanup.cleanup_old_architectural_baselines',
            'schedule': crontab(day_of_week='sunday', hour=3, minute=0),
            'kwargs': {'dry_run': False, 'keep_current': True},
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 1,
                'expires': 86400
            }
        },
        
        # Verify audit log retention - Weekly on Monday at 1 AM UTC
        'verify-audit-retention': {
            'task': 'app.tasks.data_cleanup.verify_audit_log_retention',
            'schedule': crontab(day_of_week='monday', hour=1, minute=0),
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 1,
                'expires': 86400
            }
        },
        
        # Health check task - Every 5 minutes
        'celery-health-check': {
            'task': 'app.tasks.debug_task',
            'schedule': timedelta(minutes=5),
            'options': {
                'queue': 'default',
                'routing_key': 'default',
                'priority': 5,
                'expires': 300  # Expire after 5 minutes
            }
        },
        
        # Infrastructure metrics collection - Every minute (Requirement 7.4)
        'collect-infrastructure-metrics': {
            'task': 'collect_infrastructure_metrics',
            'schedule': timedelta(minutes=1),
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 1,
                'expires': 120  # Expire after 2 minutes
            }
        },
        
        # Database pool metrics - Every 2 minutes (Requirement 7.4)
        'collect-database-pool-metrics': {
            'task': 'collect_database_pool_metrics',
            'schedule': timedelta(minutes=2),
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 1,
                'expires': 240  # Expire after 4 minutes
            }
        },
        
        # Cache metrics - Every 2 minutes (Requirement 7.4)
        'collect-cache-metrics': {
            'task': 'collect_cache_metrics',
            'schedule': timedelta(minutes=2),
            'options': {
                'queue': 'low_priority',
                'routing_key': 'low_priority',
                'priority': 1,
                'expires': 240  # Expire after 4 minutes
            }
        },
    },
)

# Load tasks from specified modules
celery_app.autodiscover_tasks([
    'app.tasks.pull_request_analysis',
    'app.tasks.architectural_drift',
    'app.tasks.ast_parsing',
    'app.tasks.graph_building',
    'app.tasks.llm_analysis',
    'app.tasks.data_cleanup',
    'app.tasks.infrastructure_metrics_task'
])


# ========================================
# TASK ERROR HANDLING AND MONITORING
# ========================================

@celery_app.task(bind=True)
def debug_task(self):
    """
    Debug task for health monitoring.
    
    This task is executed periodically to verify Celery workers are healthy.
    """
    return {
        'status': 'ok',
        'task_id': self.request.id,
        'hostname': self.request.hostname,
        'worker_pid': os.getpid()
    }


# Task event handlers for logging and monitoring
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks after Celery is configured."""
    pass  # Beat schedule is already configured above


@celery_app.on_after_finalize.connect
def setup_task_routes(sender, **kwargs):
    """Setup task routes after Celery is finalized."""
    pass  # Task routes are already configured above

