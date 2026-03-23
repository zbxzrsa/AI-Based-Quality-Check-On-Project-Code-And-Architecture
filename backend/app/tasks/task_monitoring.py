"""
Task monitoring for Celery tasks

This module provides monitoring capabilities for Celery tasks:
- Progress tracking for long-running tasks
- Failure handling with detailed error information
- Timeout detection and handling
- Task status API endpoints for polling

Validates Requirements: 12.7 (Timeout handling for all external API calls)
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum
import traceback
import logging

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery.result import AsyncResult

from app.celery_config import celery_app


logger = logging.getLogger(__name__)


# ========================================
# TASK STATUS ENUMS
# ========================================

class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    TIMEOUT = "TIMEOUT"
    REVOKED = "REVOKED"


class TaskProgressStage(str, Enum):
    """Task progress stages for PR analysis workflow"""
    INITIALIZING = "initializing"
    PARSING_FILES = "parsing_files"
    BUILDING_GRAPH = "building_graph"
    ANALYZING_LLM = "analyzing_llm"
    POSTING_COMMENTS = "posting_comments"
    COMPLETED = "completed"
    FAILED = "failed"


# ========================================
# TASK MONITORING BASE CLASS
# ========================================

class MonitoredTask(Task):
    """
    Base task class with built-in monitoring capabilities
    
    Features:
    - Automatic progress tracking
    - Failure handling with detailed error logging
    - Timeout detection and handling
    - Retry tracking
    
    Usage:
        @celery_app.task(base=MonitoredTask, bind=True)
        def my_task(self, arg1, arg2):
            self.update_progress(50, "Processing data...")
            # Task logic here
            return result
    """
    
    def __call__(self, *args, **kwargs):
        """Override call to add monitoring wrapper"""
        try:
            # Record task start
            self.update_state(
                state=TaskStatus.STARTED,
                meta={
                    'started_at': datetime.now(timezone.utc).isoformat(),
                    'args': str(args)[:200],  # Truncate for safety
                    'kwargs': str(kwargs)[:200],
                    'progress': 0,
                    'stage': TaskProgressStage.INITIALIZING,
                    'message': 'Task started'
                }
            )
            
            # Execute task
            result = super().__call__(*args, **kwargs)
            
            # Record success
            self.update_state(
                state=TaskStatus.SUCCESS,
                meta={
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                    'progress': 100,
                    'stage': TaskProgressStage.COMPLETED,
                    'message': 'Task completed successfully',
                    'result': result
                }
            )
            
            return result
            
        except SoftTimeLimitExceeded as e:
            # Soft timeout - task can still clean up
            logger.warning(
                f"Task {self.name} [{self.request.id}] soft timeout exceeded",
                extra={
                    'task_id': self.request.id,
                    'task_name': self.name,
                    'task_args': str(args)[:200],
                    'task_kwargs': str(kwargs)[:200]
                }
            )
            
            self.update_state(
                state=TaskStatus.TIMEOUT,
                meta={
                    'failed_at': datetime.now(timezone.utc).isoformat(),
                    'error_type': 'SoftTimeLimitExceeded',
                    'error_message': 'Task exceeded soft time limit',
                    'stage': TaskProgressStage.FAILED,
                    'traceback': traceback.format_exc()
                }
            )
            
            raise
            
        except TimeLimitExceeded as e:
            # Hard timeout - task is killed
            logger.error(
                f"Task {self.name} [{self.request.id}] hard timeout exceeded",
                extra={
                    'task_id': self.request.id,
                    'task_name': self.name,
                    'task_args': str(args)[:200],
                    'task_kwargs': str(kwargs)[:200]
                }
            )
            
            self.update_state(
                state=TaskStatus.TIMEOUT,
                meta={
                    'failed_at': datetime.now(timezone.utc).isoformat(),
                    'error_type': 'TimeLimitExceeded',
                    'error_message': 'Task exceeded hard time limit',
                    'stage': TaskProgressStage.FAILED,
                    'traceback': traceback.format_exc()
                }
            )
            
            raise
            
        except Exception as e:
            # General failure
            logger.error(
                f"Task {self.name} [{self.request.id}] failed: {e}",
                exc_info=True,
                extra={
                    'task_id': self.request.id,
                    'task_name': self.name,
                    'task_args': str(args)[:200],
                    'task_kwargs': str(kwargs)[:200],
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            
            # Check if this is a retry
            retry_count = self.request.retries
            max_retries = self.max_retries
            
            self.update_state(
                state=TaskStatus.RETRY if retry_count < max_retries else TaskStatus.FAILURE,
                meta={
                    'failed_at': datetime.now(timezone.utc).isoformat(),
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'traceback': traceback.format_exc(),
                    'retry_count': retry_count,
                    'max_retries': max_retries,
                    'stage': TaskProgressStage.FAILED,
                    'will_retry': retry_count < max_retries
                }
            )
            
            raise
    
    def update_progress(
        self,
        progress: int,
        message: str,
        stage: Optional[TaskProgressStage] = None,
        **extra_meta
    ):
        """
        Update task progress
        
        Args:
            progress: Progress percentage (0-100)
            message: Progress message
            stage: Current task stage
            **extra_meta: Additional metadata to store
        """
        meta = {
            'progress': progress,
            'message': message,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            **extra_meta
        }
        
        if stage:
            meta['stage'] = stage
        
        self.update_state(
            state=TaskStatus.PROGRESS,
            meta=meta
        )
        
        logger.info(
            f"Task {self.name} [{self.request.id}] progress: {progress}% - {message}",
            extra={
                'task_id': self.request.id,
                'task_name': self.name,
                'progress': progress,
                'stage': stage,
                'message': message
            }
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(
            f"Task {self.name} [{task_id}] retry {self.request.retries}/{self.max_retries}",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'retry_count': self.request.retries,
                'max_retries': self.max_retries,
                'error': str(exc)
            }
        )
        
        self.update_state(
            state=TaskStatus.RETRY,
            meta={
                'retry_at': datetime.now(timezone.utc).isoformat(),
                'retry_count': self.request.retries,
                'max_retries': self.max_retries,
                'error_type': type(exc).__name__,
                'error_message': str(exc),
                'message': f'Retrying task (attempt {self.request.retries + 1}/{self.max_retries + 1})'
            }
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails permanently"""
        logger.error(
            f"Task {self.name} [{task_id}] failed permanently",
            exc_info=exc,
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'error_type': type(exc).__name__,
                'error_message': str(exc)
            }
        )
        
        self.update_state(
            state=TaskStatus.FAILURE,
            meta={
                'failed_at': datetime.now(timezone.utc).isoformat(),
                'error_type': type(exc).__name__,
                'error_message': str(exc),
                'traceback': str(einfo),
                'stage': TaskProgressStage.FAILED,
                'message': 'Task failed permanently after all retries'
            }
        )


# ========================================
# TASK STATUS QUERY FUNCTIONS
# ========================================

def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get detailed status of a task
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Dict with task status, progress, and metadata
        
    Example:
        >>> status = get_task_status("abc-123-def")
        >>> logger.info(str(status['state']))  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
        >>> logger.info(str(status['progress']))  # 0-100
        >>> logger.info(str(status['message']))  # Current status message
    """
    result = AsyncResult(task_id, app=celery_app)
    
    response = {
        'task_id': task_id,
        'state': result.state,
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None,
        'failed': result.failed() if result.ready() else None,
    }
    
    # Add metadata if available
    if result.info:
        if isinstance(result.info, dict):
            response.update(result.info)
        elif isinstance(result.info, Exception):
            response['error'] = str(result.info)
            response['error_type'] = type(result.info).__name__
    
    # Add result if completed
    if result.ready() and result.successful():
        response['result'] = result.result
    
    # Add traceback if failed
    if result.failed():
        response['traceback'] = result.traceback
    
    return response


def get_task_progress(task_id: str) -> Dict[str, Any]:
    """
    Get task progress information
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Dict with progress percentage, stage, and message
    """
    status = get_task_status(task_id)
    
    return {
        'task_id': task_id,
        'state': status.get('state'),
        'progress': status.get('progress', 0),
        'stage': status.get('stage'),
        'message': status.get('message', ''),
        'updated_at': status.get('updated_at')
    }


def get_task_result(task_id: str, timeout: Optional[float] = None) -> Any:
    """
    Get task result (blocking)
    
    Args:
        task_id: Celery task ID
        timeout: Maximum time to wait in seconds (None = wait forever)
        
    Returns:
        Task result
        
    Raises:
        TimeoutError: If timeout is exceeded
        Exception: If task failed
    """
    result = AsyncResult(task_id, app=celery_app)
    return result.get(timeout=timeout)


def revoke_task(task_id: str, terminate: bool = False) -> Dict[str, Any]:
    """
    Revoke (cancel) a task
    
    Args:
        task_id: Celery task ID
        terminate: If True, terminate the task immediately (SIGKILL)
                  If False, task will finish current operation
        
    Returns:
        Dict with revocation status
    """
    result = AsyncResult(task_id, app=celery_app)
    result.revoke(terminate=terminate)
    
    logger.info(
        f"Task {task_id} revoked (terminate={terminate})",
        extra={'task_id': task_id, 'terminate': terminate}
    )
    
    return {
        'task_id': task_id,
        'revoked': True,
        'terminated': terminate,
        'message': 'Task revoked successfully'
    }


def get_active_tasks() -> List[Dict[str, Any]]:
    """
    Get list of currently active tasks across all workers
    
    Returns:
        List of active task info dicts
    """
    inspect = celery_app.control.inspect()
    active_tasks = inspect.active()
    
    if not active_tasks:
        return []
    
    # Flatten tasks from all workers
    all_tasks = []
    for worker, tasks in active_tasks.items():
        for task in tasks:
            all_tasks.append({
                'task_id': task['id'],
                'task_name': task['name'],
                'worker': worker,
                'args': task['args'],
                'kwargs': task['kwargs'],
                'time_start': task.get('time_start')
            })
    
    return all_tasks


def get_scheduled_tasks() -> List[Dict[str, Any]]:
    """
    Get list of scheduled (queued) tasks across all workers
    
    Returns:
        List of scheduled task info dicts
    """
    inspect = celery_app.control.inspect()
    scheduled_tasks = inspect.scheduled()
    
    if not scheduled_tasks:
        return []
    
    # Flatten tasks from all workers
    all_tasks = []
    for worker, tasks in scheduled_tasks.items():
        for task in tasks:
            all_tasks.append({
                'task_id': task['request']['id'],
                'task_name': task['request']['name'],
                'worker': worker,
                'eta': task.get('eta'),
                'priority': task['request'].get('priority')
            })
    
    return all_tasks


def get_worker_stats() -> Dict[str, Any]:
    """
    Get statistics from all Celery workers
    
    Returns:
        Dict with worker statistics
    """
    inspect = celery_app.control.inspect()
    stats = inspect.stats()
    
    if not stats:
        return {'workers': [], 'total_workers': 0}
    
    workers = []
    for worker_name, worker_stats in stats.items():
        workers.append({
            'name': worker_name,
            'pool': worker_stats.get('pool', {}).get('implementation'),
            'max_concurrency': worker_stats.get('pool', {}).get('max-concurrency'),
            'total_tasks': worker_stats.get('total', {}),
            'rusage': worker_stats.get('rusage')
        })
    
    return {
        'workers': workers,
        'total_workers': len(workers)
    }


# ========================================
# TIMEOUT HANDLING UTILITIES
# ========================================

class TaskTimeoutError(Exception):
    """Raised when a task operation times out"""
    pass


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout handling to async task operations
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Usage:
        @with_timeout(30)
        async def call_external_api():
            # API call here
            pass
            
    Note: Only works with async functions
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            import asyncio
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                raise TaskTimeoutError(
                    f"Operation {func.__name__} timed out after {timeout_seconds}s"
                )
        
        # Return wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            raise TypeError(f"with_timeout decorator only works with async functions, got {type(func)}")
    
    return decorator


# ========================================
# FAILURE HANDLING UTILITIES
# ========================================

class TaskFailureHandler:
    """
    Centralized failure handling for tasks
    
    Features:
    - Structured error logging
    - Error categorization
    - Retry decision logic
    - Failure notifications
    """
    
    @staticmethod
    def should_retry(exc: Exception, retry_count: int, max_retries: int) -> bool:
        """
        Determine if task should be retried based on exception type
        
        Args:
            exc: Exception that occurred
            retry_count: Current retry count
            max_retries: Maximum allowed retries
            
        Returns:
            True if task should be retried
        """
        # Don't retry if max retries reached
        if retry_count >= max_retries:
            return False
        
        # Retry on transient errors
        transient_errors = (
            ConnectionError,
            TimeoutError,
            TaskTimeoutError,
        )
        
        if isinstance(exc, transient_errors):
            return True
        
        # Don't retry on validation errors
        validation_errors = (
            ValueError,
            TypeError,
            KeyError,
        )
        
        if isinstance(exc, validation_errors):
            return False
        
        # Retry on other exceptions
        return True
    
    @staticmethod
    def get_retry_delay(retry_count: int, base_delay: int = 60) -> int:
        """
        Calculate retry delay with exponential backoff
        
        Args:
            retry_count: Current retry count
            base_delay: Base delay in seconds
            
        Returns:
            Delay in seconds
        """
        import random
        
        # Exponential backoff: base_delay * 2^retry_count
        delay = base_delay * (2 ** retry_count)
        
        # Add jitter (±20%)
        jitter = random.uniform(0.8, 1.2)
        delay = int(delay * jitter)
        
        # Cap at 10 minutes
        return min(delay, 600)
    
    @staticmethod
    def log_failure(
        task_name: str,
        task_id: str,
        exc: Exception,
        args: tuple,
        kwargs: dict,
        retry_count: int
    ):
        """
        Log task failure with structured information
        
        Args:
            task_name: Name of the task
            task_id: Task ID
            exc: Exception that occurred
            args: Task arguments
            kwargs: Task keyword arguments
            retry_count: Current retry count
        """
        logger.error(
            f"Task {task_name} [{task_id}] failed",
            exc_info=exc,
            extra={
                'task_id': task_id,
                'task_name': task_name,
                'error_type': type(exc).__name__,
                'error_message': str(exc),
                'task_args': str(args)[:200],
                'task_kwargs': str(kwargs)[:200],
                'retry_count': retry_count,
                'traceback': traceback.format_exc()
            }
        )


# ========================================
# HEALTH CHECK TASK
# ========================================

@celery_app.task(
    bind=True,
    base=MonitoredTask,
    name='app.tasks.task_monitoring.health_check',
    queue='default'
)
def health_check(self) -> Dict[str, Any]:
    """
    Health check task for monitoring worker health
    
    Returns:
        Dict with health status
    """
    return {
        'status': 'healthy',
        'task_id': self.request.id,
        'worker': self.request.hostname,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
