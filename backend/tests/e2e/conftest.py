"""
Pytest configuration for end-to-end tests

This module provides fixtures and configuration for e2e tests.
"""
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock

from app.database.postgresql import AsyncSessionLocal, engine
from app.models import Base, User, UserRole, Project


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator:
    """
    Provide a test database session
    
    Creates tables before tests and drops them after.
    Each test gets a fresh database state.
    """
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Provide session
    async with AsyncSessionLocal() as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def test_user(test_db) -> User:
    """
    Create a test user for authentication
    
    Returns a user with developer role.
    """
    # Create user
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash="$2b$12$test_hash",
        role=UserRole.USER,
        is_active=True
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    
    return user


@pytest.fixture(scope="function")
async def test_project(test_db, test_user) -> Project:
    """
    Create a test project
    
    Returns a project owned by test_user.
    """
    project = Project(
        name="Test Project",
        description="Project for testing",
        github_repo_url="https://github.com/test/repo",
        github_webhook_secret="test_secret",
        language="Python"
    )
    test_db.add(project)
    await test_db.commit()
    await test_db.refresh(project)
    
    return project


@pytest.fixture(scope="function")
def mock_github_client():
    """
    Mock GitHub API client
    
    Returns a mock client with common methods.
    """
    client = AsyncMock()
    
    # Mock common methods
    client.get_pr_files.return_value = []
    client.get_file_content.return_value = ""
    client.post_review_comment.return_value = {'id': 1}
    client.update_pr_status.return_value = {'state': 'success'}
    client.get_repository.return_value = {
        'name': 'test-repo',
        'full_name': 'test/repo',
        'default_branch': 'main'
    }
    
    return client


@pytest.fixture(scope="function")
def mock_llm_client():
    """
    Mock LLM API client
    
    Returns a mock client with common methods.
    """
    client = AsyncMock()
    
    # Mock response
    mock_response = Mock()
    mock_response.content = '{"issues": [], "summary": "No issues found", "risk_score": 0}'
    mock_response.provider = 'openai'
    mock_response.tokens = {'total': 100}
    mock_response.cost = 0.001
    
    client.generate.return_value = mock_response
    
    return client


@pytest.fixture(scope="function")
def mock_cache_service():
    """
    Mock cache service
    
    Returns a mock cache service for testing.
    """
    cache = AsyncMock()
    
    cache.cache_exists.return_value = False
    cache.cache_set.return_value = True
    cache.cache_get.return_value = None
    cache.cache_delete.return_value = True
    
    return cache


@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """
    Cleanup fixture that runs after each test
    
    Ensures test data is cleaned up even if test fails.
    """
    yield


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add e2e marker to all tests in e2e directory
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
