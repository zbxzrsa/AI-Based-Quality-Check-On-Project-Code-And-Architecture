#!/bin/bash
# Celery worker startup script

# Source environment variables
if [[ -f .env ]]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start Celery worker
celery -A app.celery_config worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=high_priority,low_priority,default \
    --max-tasks-per-child=1000 \
    --time-limit=3600 \
    --soft-time-limit=3300

# For development with auto-reload:
# celery -A app.celery_config worker --loglevel=info --pool=solo --autoreload
