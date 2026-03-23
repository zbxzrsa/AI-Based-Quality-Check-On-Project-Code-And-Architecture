"""
Celery task queue enhancements with priority support

Provides priority-based task routing and execution for Celery tasks.

Validates Requirements: 10.6
"""

from enum import Enum
from typing import Dict, Any
from celery import Task


class TaskPriority(int, Enum):
    """Task priority levels"""
    CRITICAL = 0  # Security issues, critical errors
    HIGH = 3  # Important analysis tasks
    NORMAL = 5  # Regular tasks
    LOW = 7  # Background tasks, cleanup
    VERY_LOW = 9  # Non-urgent maintenance


class PriorityTaskRouter:
    """
    Routes tasks to appropriate queues based on priority.
    
    Validates Requirements: 10.6
    """
    
    # Map priorities to queue names
    PRIORITY_QUEUES = {
        TaskPriority.CRITICAL: "critical",
        TaskPriority.HIGH: "high_priority",
        TaskPriority.NORMAL: "default",
        TaskPriority.LOW: "low_priority",
        TaskPriority.VERY_LOW: "background",
    }
    
    # Task name to priority mapping
    TASK_PRIORITIES = {
        # Security and critical tasks
        "security_scan": TaskPriority.CRITICAL,
        "vulnerability_check": TaskPriority.CRITICAL,
        "auth_failure_alert": TaskPriority.CRITICAL,
        
        # High priority analysis
        "code_review": TaskPriority.HIGH,
        "pr_analysis": TaskPriority.HIGH,
        "graph_analysis": TaskPriority.HIGH,
        
        # Normal priority
        "ai_reasoning": TaskPriority.NORMAL,
        "code_suggestion": TaskPriority.NORMAL,
        "metrics_calculation": TaskPriority.NORMAL,
        
        # Low priority
        "drift_detection": TaskPriority.LOW,
        "pattern_analysis": TaskPriority.LOW,
        "report_generation": TaskPriority.LOW,
        
        # Very low priority
        "cleanup": TaskPriority.VERY_LOW,
        "archive": TaskPriority.VERY_LOW,
        "statistics": TaskPriority.VERY_LOW,
    }
    
    @classmethod
    def route_for_task(cls, task_name: str, args=None, kwargs=None) -> Dict[str, Any]:
        """
        Determine routing for a task based on its name and priority.
        
        Args:
            task_name: Name of the task
            args: Task positional arguments
            kwargs: Task keyword arguments
            
        Returns:
            Routing configuration dictionary
        """
        # Extract base task name (remove module prefix)
        base_name = task_name.split('.')[-1]
        
        # Get priority from task name or use default
        priority = cls.TASK_PRIORITIES.get(base_name, TaskPriority.NORMAL)
        
        # Check if priority is overridden in kwargs
        if kwargs and 'priority' in kwargs:
            priority = TaskPriority(kwargs['priority'])
        
        # Get queue for priority
        queue = cls.PRIORITY_QUEUES.get(priority, "default")
        
        return {
            'queue': queue,
            'priority': priority.value,
            'routing_key': f"{queue}.{base_name}",
        }
    
    @classmethod
    def get_queue_for_priority(cls, priority: TaskPriority) -> str:
        """Get queue name for a priority level"""
        return cls.PRIORITY_QUEUES.get(priority, "default")
    
    @classmethod
    def get_priority_for_task(cls, task_name: str) -> TaskPriority:
        """Get priority for a task name"""
        base_name = task_name.split('.')[-1]
        return cls.TASK_PRIORITIES.get(base_name, TaskPriority.NORMAL)


class PriorityTask(Task):
    """
    Base task class with priority support.
    
    Usage:
        @celery_app.task(base=PriorityTask, priority=TaskPriority.HIGH)
        def my_task():
            pass
    """
    
    def __init__(self):
        super().__init__()
        self.priority = TaskPriority.NORMAL
    
    def apply_async(self, args=None, kwargs=None, **options):
        """Override apply_async to inject priority"""
        if not options.get('priority'):
            options['priority'] = self.priority.value
        
        if not options.get('queue'):
            options['queue'] = PriorityTaskRouter.get_queue_for_priority(self.priority)
        
        return super().apply_async(args, kwargs, **options)


def get_celery_config_with_priorities() -> Dict[str, Any]:
    """
    Get Celery configuration with priority queue support.
    
    Returns:
        Celery configuration dictionary
    """
    return {
        # Task routing
        'task_routes': (PriorityTaskRouter.route_for_task,),
        
        # Queue definitions
        'task_queues': {
            'critical': {
                'exchange': 'critical',
                'routing_key': 'critical.*',
            },
            'high_priority': {
                'exchange': 'high_priority',
                'routing_key': 'high_priority.*',
            },
            'default': {
                'exchange': 'default',
                'routing_key': 'default.*',
            },
            'low_priority': {
                'exchange': 'low_priority',
                'routing_key': 'low_priority.*',
            },
            'background': {
                'exchange': 'background',
                'routing_key': 'background.*',
            },
        },
        
        # Worker configuration
        'worker_prefetch_multiplier': 1,
        'worker_max_tasks_per_child': 1000,
        
        # Task execution
        'task_acks_late': True,
        'task_reject_on_worker_lost': True,
        
        # Priority support
        'task_inherit_parent_priority': True,
        'task_default_priority': TaskPriority.NORMAL.value,
    }


def create_priority_task(
    func: callable,
    priority: TaskPriority = TaskPriority.NORMAL,
    **task_kwargs
) -> Task:
    """
    Create a Celery task with priority.
    
    Args:
        func: Function to wrap as task
        priority: Task priority level
        **task_kwargs: Additional task configuration
        
    Returns:
        Celery task
    """
    task_kwargs['base'] = PriorityTask
    task_kwargs['priority'] = priority
    
    # Set queue based on priority
    if 'queue' not in task_kwargs:
        task_kwargs['queue'] = PriorityTaskRouter.get_queue_for_priority(priority)
    
    return Task.bind(func, **task_kwargs)
