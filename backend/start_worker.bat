@echo off
REM Celery worker startup script for Windows

REM Start Celery worker
celery -A app.celery_config worker ^
    --loglevel=info ^
    --concurrency=4 ^
    --queues=high_priority,low_priority,default ^
    --max-tasks-per-child=1000 ^
    --pool=solo

REM Note: Windows requires --pool=solo for proper operation
