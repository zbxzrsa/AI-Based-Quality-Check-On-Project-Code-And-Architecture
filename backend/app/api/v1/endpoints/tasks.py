"""
Task monitoring API endpoints

Provides REST API endpoints for:
- Querying task status and progress
- Retrieving task results
- Canceling tasks
- Monitoring worker health

Validates Requirements: 12.7 (Timeout handling for all external API calls)
"""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.tasks.task_monitoring import (
    get_active_tasks,
    get_scheduled_tasks,
    get_task_progress,
    get_task_result,
    get_task_status,
    get_worker_stats,
    revoke_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ========================================
# REQUEST/RESPONSE MODELS
# ========================================


class TaskStatusResponse(BaseModel):
    """Task status response model"""

    task_id: str = Field(..., description="Celery task ID")
    state: str = Field(..., description="Task state (PENDING, STARTED, PROGRESS, SUCCESS, FAILURE)")
    ready: bool = Field(..., description="Whether task has completed")
    successful: bool | None = Field(None, description="Whether task completed successfully")
    failed: bool | None = Field(None, description="Whether task failed")
    progress: int | None = Field(None, description="Progress percentage (0-100)")
    stage: str | None = Field(None, description="Current task stage")
    message: str | None = Field(None, description="Status message")
    result: Any | None = Field(None, description="Task result (if completed)")
    error: str | None = Field(None, description="Error message (if failed)")
    error_type: str | None = Field(None, description="Error type (if failed)")
    traceback: str | None = Field(None, description="Error traceback (if failed)")
    retry_count: int | None = Field(None, description="Number of retries")
    max_retries: int | None = Field(None, description="Maximum retries allowed")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc-123-def-456",
                "state": "PROGRESS",
                "ready": False,
                "successful": None,
                "failed": None,
                "progress": 50,
                "stage": "analyzing_llm",
                "message": "Analyzing code with LLM...",
            }
        }


class TaskProgressResponse(BaseModel):
    """Task progress response model"""

    task_id: str = Field(..., description="Celery task ID")
    state: str = Field(..., description="Task state")
    progress: int = Field(..., description="Progress percentage (0-100)")
    stage: str | None = Field(None, description="Current task stage")
    message: str = Field(..., description="Progress message")
    updated_at: str | None = Field(None, description="Last update timestamp")


class TaskRevokeRequest(BaseModel):
    """Task revoke request model"""

    terminate: bool = Field(
        False, description="If True, terminate task immediately. If False, let it finish current operation."
    )


class TaskRevokeResponse(BaseModel):
    """Task revoke response model"""

    task_id: str = Field(..., description="Celery task ID")
    revoked: bool = Field(..., description="Whether task was revoked")
    terminated: bool = Field(..., description="Whether task was terminated")
    message: str = Field(..., description="Revocation message")


class ActiveTaskInfo(BaseModel):
    """Active task information"""

    task_id: str = Field(..., description="Celery task ID")
    task_name: str = Field(..., description="Task name")
    worker: str = Field(..., description="Worker hostname")
    args: str = Field(..., description="Task arguments")
    kwargs: str = Field(..., description="Task keyword arguments")
    time_start: float | None = Field(None, description="Task start time")


class ScheduledTaskInfo(BaseModel):
    """Scheduled task information"""

    task_id: str = Field(..., description="Celery task ID")
    task_name: str = Field(..., description="Task name")
    worker: str = Field(..., description="Worker hostname")
    eta: str | None = Field(None, description="Estimated time of arrival")
    priority: int | None = Field(None, description="Task priority")


class WorkerInfo(BaseModel):
    """Worker information"""

    name: str = Field(..., description="Worker name")
    pool: str | None = Field(None, description="Worker pool implementation")
    max_concurrency: int | None = Field(None, description="Maximum concurrency")
    total_tasks: dict[str, Any] | None = Field(None, description="Total tasks executed")
    rusage: dict[str, Any] | None = Field(None, description="Resource usage")


class WorkerStatsResponse(BaseModel):
    """Worker statistics response"""

    workers: list[WorkerInfo] = Field(..., description="List of workers")
    total_workers: int = Field(..., description="Total number of workers")


# ========================================
# API ENDPOINTS
# ========================================


@router.get(
    "/{task_id}/status",
    summary="Get task status",
    description="Get detailed status of a task including progress, state, and results",
)
async def get_status(task_id: Annotated[str, Path(..., description="Celery task ID")]) -> TaskStatusResponse:
    """
    Get detailed status of a task

    Returns task state, progress, results, and error information if available.

    **Task States:**
    - PENDING: Task is waiting to be executed
    - STARTED: Task has started execution
    - PROGRESS: Task is in progress (with progress updates)
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed permanently
    - RETRY: Task is being retried
    - TIMEOUT: Task exceeded time limit
    - REVOKED: Task was cancelled
    """
    try:
        status = get_task_status(task_id)
        return TaskStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving task status: {str(e)}")


@router.get(
    "/{task_id}/progress",
    summary="Get task progress",
    description="Get task progress information including percentage and current stage",
)
async def get_progress(task_id: Annotated[str, Path(..., description="Celery task ID")]) -> TaskProgressResponse:
    """
    Get task progress information

    Returns progress percentage (0-100), current stage, and status message.
    Useful for displaying progress bars and status updates in UI.
    """
    try:
        progress = get_task_progress(task_id)
        return TaskProgressResponse(**progress)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving task progress: {str(e)}")


@router.get(
    "/{task_id}/result",
    summary="Get task result",
    description="Get task result (blocking until task completes or timeout)",
)
async def get_result(
    task_id: Annotated[str, Path(..., description="Celery task ID")],
    timeout: float | None = Query(None, description="Maximum time to wait in seconds (None = wait forever)"),
) -> dict[str, Any]:
    """
    Get task result (blocking)

    This endpoint will wait for the task to complete and return the result.
    Use the timeout parameter to avoid waiting indefinitely.

    **Note:** For long-running tasks, prefer polling the status endpoint instead.
    """
    try:
        result = get_task_result(task_id, timeout=timeout)
        return {"task_id": task_id, "result": result}
    except TimeoutError:
        raise HTTPException(status_code=408, detail=f"Task did not complete within {timeout} seconds")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving task result: {str(e)}")


@router.post(
    "/{task_id}/revoke",
    summary="Revoke (cancel) a task",
    description="Cancel a task. Can optionally terminate it immediately.",
)
async def revoke(
    task_id: Annotated[str, Path(..., description="Celery task ID")], request: TaskRevokeRequest = TaskRevokeRequest()
) -> TaskRevokeResponse:
    """
    Revoke (cancel) a task

    **Revoke modes:**
    - terminate=False: Task will finish its current operation and then stop
    - terminate=True: Task is terminated immediately (SIGKILL)

    **Note:** Terminated tasks may leave resources in inconsistent state.
    Use terminate=False unless absolutely necessary.
    """
    try:
        result = revoke_task(task_id, terminate=request.terminate)
        return TaskRevokeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error revoking task: {str(e)}")


@router.get(
    "/active",
    response_model=list[ActiveTaskInfo],
    summary="Get active tasks",
    description="Get list of currently executing tasks across all workers",
)
async def list_active_tasks() -> list[ActiveTaskInfo]:
    """
    Get list of currently active (executing) tasks

    Returns tasks that are currently being executed by workers.
    Useful for monitoring system load and debugging.
    """
    try:
        tasks = get_active_tasks()
        return [ActiveTaskInfo(**task) for task in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving active tasks: {str(e)}")


@router.get(
    "/scheduled",
    response_model=list[ScheduledTaskInfo],
    summary="Get scheduled tasks",
    description="Get list of scheduled (queued) tasks waiting to be executed",
)
async def list_scheduled_tasks() -> list[ScheduledTaskInfo]:
    """
    Get list of scheduled (queued) tasks

    Returns tasks that are waiting in queues to be executed.
    Useful for monitoring queue depth and task backlog.
    """
    try:
        tasks = get_scheduled_tasks()
        return [ScheduledTaskInfo(**task) for task in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving scheduled tasks: {str(e)}")


@router.get("/workers/stats", summary="Get worker statistics", description="Get statistics from all Celery workers")
async def get_stats() -> WorkerStatsResponse:
    """
    Get statistics from all Celery workers

    Returns information about all active workers including:
    - Worker names and pool types
    - Concurrency settings
    - Total tasks executed
    - Resource usage

    Useful for monitoring worker health and capacity.
    """
    try:
        stats = get_worker_stats()
        return WorkerStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving worker stats: {str(e)}")


@router.get("/health", summary="Health check", description="Check if task monitoring API is healthy")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint

    Returns 200 OK if the task monitoring API is operational.
    """
    return {"status": "healthy", "service": "task-monitoring"}
