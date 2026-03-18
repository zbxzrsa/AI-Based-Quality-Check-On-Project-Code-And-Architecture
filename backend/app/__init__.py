"""
Backend Application - Central Exports

This module provides centralized exports for the backend application.
Import from here instead of importing from individual modules.
"""

# Core utilities
from app.core import settings, get_logger

# Domain layer
from app.domain import (
    Entity,
    User,
    Project,
    PullRequest,
    CodeReview,
    IGitHubService,
    ILLMService,
    ICacheService,
    IGraphService,
)

# Infrastructure layer
from app.infrastructure import (
    DIContainer,
    get_container,
    GitHubService,
    RedisCacheService,
    LLMServiceImpl,
    get_db_session,
)

# Application layer
from app.application import UseCase, Command, Query, UseCaseResult

__all__ = [
    # Core
    "settings",
    "get_logger",
    # Domain
    "Entity",
    "User",
    "Project",
    "PullRequest",
    "CodeReview",
    "IGitHubService",
    "ILLMService",
    "ICacheService",
    "IGraphService",
    # Infrastructure
    "DIContainer",
    "get_container",
    "GitHubService",
    "RedisCacheService",
    "LLMServiceImpl",
    "get_db_session",
    # Application
    "UseCase",
    "Command",
    "Query",
    "UseCaseResult",
]
