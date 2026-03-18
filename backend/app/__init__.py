"""
Backend Application - Central Exports

This module provides centralized exports for the backend application.
Import from here instead of importing from individual modules.
"""

# Core utilities
# Application layer
from app.application import Command, Query, UseCase, UseCaseResult
from app.core import get_logger, settings

# Domain layer
from app.domain import (
    CodeReview,
    Entity,
    ICacheService,
    IGitHubService,
    IGraphService,
    ILLMService,
    Project,
    PullRequest,
    User,
)

# Infrastructure layer
from app.infrastructure import (
    DIContainer,
    GitHubService,
    LLMServiceImpl,
    RedisCacheService,
    get_container,
    get_db_session,
)

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
