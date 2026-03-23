"""
Audit Log Decorator

Automatically logs audit entries for service operations.
Eliminates repetitive audit logging code throughout the codebase.

Example:
    @with_audit_log("user.create")
    async def create_user(db: AsyncSession, user_data: UserCreate, user_id: str):
        user = User(**user_data.model_dump())
        db.add(user)
        await db.commit()
        return user
"""

from functools import wraps
from typing import Callable, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def with_audit_log(
    action: str,
    resource_type: Optional[str] = None
) -> Callable:
    """
    Decorator to automatically log audit entries for operations.
    
    Args:
        action: The audit action (e.g., "user.create", "project.delete")
        resource_type: Optional resource type override (defaults to function name)
    
    Returns:
        Decorated function
    
    Example:
        @with_audit_log("user.create")
        async def create_user(db: AsyncSession, user_data: UserCreate, user_id: str):
            user = User(**user_data.model_dump())
            db.add(user)
            await db.commit()
            return user
        
        @with_audit_log("project.delete", resource_type="project")
        async def delete_project(db: AsyncSession, project_id: str, user_id: str):
            project = await db.get(Project, project_id)
            await db.delete(project)
            await db.commit()
            return project
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract common parameters
            db = kwargs.get('db')
            user_id = kwargs.get('user_id') or kwargs.get('current_user_id')
            request = kwargs.get('request')
            
            # Get IP address from request if available
            ip_address = "unknown"
            if request and hasattr(request, 'client') and request.client:
                ip_address = request.client.host
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Log audit entry if we have the required parameters
            if db and user_id:
                try:
                    # Import here to avoid circular dependency
                    from app.models.audit_log import AuditLog
                    
                    audit_entry = AuditLog(
                        user_id=user_id,
                        action=action,
                        resource_type=resource_type or func.__name__,
                        resource_id=str(getattr(result, 'id', None)) if result else None,
                        ip_address=ip_address,
                        details={
                            'function': func.__name__,
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys()),
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    )
                    
                    db.add(audit_entry)
                    await db.commit()
                    
                    logger.debug(f"Audit log created: {action} by user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to create audit log: {e}")
                    # Don't fail the operation if audit logging fails
                    pass
            
            return result
        
        return wrapper
    return decorator


def with_audit_log_sync(action: str, resource_type: Optional[str] = None) -> Callable:
    """
    Synchronous version of the audit log decorator.
    
    Args:
        action: The audit action
        resource_type: Optional resource type override
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            db = kwargs.get('db')
            user_id = kwargs.get('user_id') or kwargs.get('current_user_id')
            request = kwargs.get('request')
            
            ip_address = "unknown"
            if request and hasattr(request, 'client') and request.client:
                ip_address = request.client.host
            
            result = func(*args, **kwargs)
            
            if db and user_id:
                try:
                    
                    audit_entry = AuditLog(
                        user_id=user_id,
                        action=action,
                        resource_type=resource_type or func.__name__,
                        resource_id=str(getattr(result, 'id', None)) if result else None,
                        ip_address=ip_address,
                        details={
                            'function': func.__name__,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    )
                    
                    db.add(audit_entry)
                    db.commit()
                    
                    logger.debug(f"Audit log created: {action} by user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to create audit log: {e}")
            
            return result
        
        return wrapper
    return decorator
