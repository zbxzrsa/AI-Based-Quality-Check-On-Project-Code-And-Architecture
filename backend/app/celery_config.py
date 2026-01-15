"""
Celery configuration
"""
from celery import Celery
from celery.schedules import crontab

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
    
    # Task routing
    task_routes={
        'app.tasks.analyze_pull_request': {'queue': 'high_priority'},
        'app.tasks.detect_architectural_drift': {'queue': 'low_priority'},
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
        'detect-drift-weekly': {
            'task': 'app.tasks.detect_architectural_drift',
            'schedule': crontab(day_of_week='monday', hour=2, minute=0),
            'args': ()
        },
    },
)

# Load tasks
celery_app.autodiscover_tasks(['app.tasks'])
