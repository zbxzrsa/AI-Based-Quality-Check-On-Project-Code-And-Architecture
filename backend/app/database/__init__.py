"""
Database Layer - Central Exports

This module provides centralized exports for the database layer.
Import from here instead of importing from individual files.
"""

# Database session management
# Neo4j driver
from app.database.neo4j_db import get_neo4j_driver
from app.database.postgresql import AsyncSessionLocal, engine, get_db

# Redis client
from app.database.redis_db import get_redis_client

__all__ = [
    # PostgreSQL
    "get_db",
    "engine",
    "AsyncSessionLocal",
    "async_session_maker",
    # Neo4j
    "get_neo4j_driver",
    # Redis
    "get_redis_client",
]

# Backward-compatible alias for legacy imports.
async_session_maker = AsyncSessionLocal
