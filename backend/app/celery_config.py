"""
Celery configuration
"""
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

from app.core.config import settings


# Create Celery app
celery_app = Celery(
    "ai_code_review",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend
    result_expires=3600,  # 1 hour
    
    # Task routing - sends tasks to specific queues
    task_routes={
        'app.tasks.pull_request_analysis.analyze_pull_request': {'queue': 'high_priority'},
        'app.tasks.architectural_drift.detect_architectural_drift': {'queue': 'low_priority'},
        'app.tasks.architectural_drift.detect_cyclic_dependencies': {'queue': 'low_priority'},
        'app.tasks.architectural_drift.detect_layer_violations': {'queue': 'low_priority'},
        'app.tasks.generate_project_documentation': {'queue': 'low_priority'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Rate limiting
    task_default_rate_limit='10/m',
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # Weekly drift detection - Every Monday at 2 AM UTC
        'detect-drift-weekly': {
            'task': 'app.tasks.architectural_drift.detect_architectural_drift',
            'schedule': crontab(day_of_week='monday', hour=2, minute=0),
            'args': ('*',),  # Analyze all projects
            'kwargs': {'baseline_version': 'latest'},
            'options': {'queue': 'low_priority', 'expires': 86400}
        },
        
        # Daily cycle detection - Every day at 3 AM UTC
        'detect-cycles-daily': {
            'task': 'app.tasks.architectural_drift.detect_cyclic_dependencies',
            'schedule': crontab(hour=3, minute=0),
            'args': ('*',),
            'options': {'queue': 'low_priority', 'expires': 86400}
        },
        
        # Twice weekly layer violation check - Monday and Thursday at 4 AM UTC
        'detect-violations-twice-weekly': {
            'task': 'app.tasks.architectural_drift.detect_layer_violations',
            'schedule': crontab(day_of_week='monday,thursday', hour=4, minute=0),
            'args': ('*',),
            'options': {'queue': 'low_priority', 'expires': 86400}
        },
        
        # Health check task - Every hour
        'celery-health-check': {
            'task': 'app.tasks.debug_task',
            'schedule': timedelta(hours=1),
            'options': {'queue': 'default', 'expires': 3600}
        },
    },
)

# Load tasks from specified modules
celery_app.autodiscover_tasks([
    'app.tasks.pull_request_analysis',
    'app.tasks.architectural_drift'
])


# Task error handling
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for monitoring"""
    print(f'Celery task request: {self.request!r}')
    return {'status': 'ok', 'task_id': self.request.id}

