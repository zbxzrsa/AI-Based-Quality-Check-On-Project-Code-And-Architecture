"""
Response model converter utilities.

This module provides reusable functions to convert database models to response models.
"""
from typing import Optional, List
from datetime import datetime

from app.models import User, Project, PullRequest


def convert_datetime(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert datetime to ISO format string.
    
    Args:
        dt: Datetime object or None
        
    Returns:
        ISO format string or None
    """
    return dt.isoformat() if dt else None


def user_to_response(user: User) -> dict:
    """
    Convert User model to response dictionary.
    
    Args:
        user: User model instance
        
    Returns:
        Dictionary with user response data
    """
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
        "is_active": user.is_active,
        "email_confirmed": user.email_confirmed,
        "created_at": convert_datetime(user.created_at),
        "updated_at": convert_datetime(user.updated_at),
        "last_login": convert_datetime(user.last_login) if hasattr(user, 'last_login') else None
    }


def project_to_response(project: Project) -> dict:
    """
    Convert Project model to response dictionary.
    
    Args:
        project: Project model instance
        
    Returns:
        Dictionary with project response data
    """
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "repository_url": project.repository_url,
        "owner_id": project.owner_id,
        "created_at": convert_datetime(project.created_at),
        "updated_at": convert_datetime(project.updated_at)
    }


def pull_request_to_response(pr: PullRequest) -> dict:
    """
    Convert PullRequest model to response dictionary.
    
    Args:
        pr: PullRequest model instance
        
    Returns:
        Dictionary with pull request response data
    """
    return {
        "id": pr.id,
        "title": pr.title,
        "description": pr.description,
        "pr_number": pr.pr_number,
        "status": pr.status,
        "project_id": pr.project_id,
        "author_id": pr.author_id,
        "created_at": convert_datetime(pr.created_at),
        "updated_at": convert_datetime(pr.updated_at)
    }


def users_to_response_list(users: List[User]) -> List[dict]:
    """
    Convert list of User models to response list.
    
    Args:
        users: List of User model instances
        
    Returns:
        List of user response dictionaries
    """
    return [user_to_response(user) for user in users]


def projects_to_response_list(projects: List[Project]) -> List[dict]:
    """
    Convert list of Project models to response list.
    
    Args:
        projects: List of Project model instances
        
    Returns:
        List of project response dictionaries
    """
    return [project_to_response(project) for project in projects]


def pull_requests_to_response_list(prs: List[PullRequest]) -> List[dict]:
    """
    Convert list of PullRequest models to response list.
    
    Args:
        prs: List of PullRequest model instances
        
    Returns:
        List of pull request response dictionaries
    """
    return [pull_request_to_response(pr) for pr in prs]
