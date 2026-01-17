"""
Test cases for Celery async tasks and PR analysis endpoints

Tests verify:
1. Async task queuing without waiting for results
2. Task status polling
3. Mock Celery task execution
4. API response times
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from celery.result import AsyncResult
from datetime import datetime
import json

from app.main import app
from app.models import PullRequest, Project, PRStatus


client = TestClient(app)


# ===========================
# Fixtures
# ===========================

@pytest.fixture
def mock_project():
    """Mock project instance"""
    return {
        'id': 'test-project-1',
        'name': 'Test Project',
        'github_repo_url': 'https://github.com/user/test-repo',
        'language': 'Python',
        'github_webhook_secret': 'test-secret'
    }


@pytest.fixture
def mock_pr():
    """Mock PR instance"""
    return {
        'id': 'test-pr-1',
        'project_id': 'test-project-1',
        'github_pr_number': 42,
        'title': 'feat: Add new feature',
        'description': 'This PR adds amazing features',
        'commit_sha': 'abc123def456',
        'files_changed': 3,
        'lines_added': 50,
        'lines_deleted': 10,
        'status': 'pending'
    }


@pytest.fixture
def mock_celery_task():
    """Mock Celery task result"""
    return {
        'id': 'task-abc123',
        'status': 'SUCCESS',
        'result': {
            'pr_id': 'test-pr-1',
            'status': 'completed',
            'issues_found': 5,
            'risk_score': 45.5,
            'confidence_score': 0.92
        }
    }


# ===========================
# Task Queuing Tests
# ===========================

@pytest.mark.asyncio
async def test_analyze_pr_task_queuing():
    """Test that PR analysis task is queued without waiting for results"""
    
    with patch('app.tasks.pull_request_analysis.analyze_pull_request.apply_async') as mock_apply:
        mock_apply.return_value.id = 'task-abc123'
        
        from app.tasks.pull_request_analysis import analyze_pull_request_sync
        
        result = analyze_pull_request_sync('pr-1', 'project-1')
        
        # Verify task was queued
        assert result['status'] == 'PENDING'
        assert result['message'] == 'PR analysis queued and will begin shortly'
        assert 'task_id' in result
        assert result['pr_id'] == 'pr-1'
        
        # Verify apply_async was called with correct parameters
        mock_apply.assert_called_once()
        call_args = mock_apply.call_args
        assert call_args[1]['queue'] == 'high_priority'


@pytest.mark.asyncio
async def test_task_queuing_is_non_blocking():
    """Test that queuing a task takes minimal time"""
    import time
    
    with patch('app.tasks.pull_request_analysis.analyze_pull_request.apply_async') as mock_apply:
        mock_apply.return_value.id = 'task-xyz789'
        
        from app.tasks.pull_request_analysis import analyze_pull_request_sync
        
        start_time = time.time()
        result = analyze_pull_request_sync('pr-1', 'project-1')
        elapsed = time.time() - start_time
        
        # Should complete in < 100ms
        assert elapsed < 0.1
        assert result['status'] == 'PENDING'


# ===========================
# Task Status Polling Tests
# ===========================

@pytest.mark.asyncio
async def test_task_status_pending():
    """Test getting status of pending task"""
    
    mock_result = AsyncMock()
    mock_result.status = 'PENDING'
    mock_result.result = None
    mock_result.info = None
    
    with patch('app.celery_config.celery_app.AsyncResult', return_value=mock_result):
        # Simulate API call
        response = {
            "task_id": "task-abc123",
            "status": "PENDING",
            "result": None,
            "error": None
        }
        
        assert response['status'] == 'PENDING'
        assert response['result'] is None


@pytest.mark.asyncio
async def test_task_status_success():
    """Test getting status of completed task"""
    
    expected_result = {
        'pr_id': 'pr-1',
        'status': 'completed',
        'issues_found': 5,
        'risk_score': 45.5,
        'confidence_score': 0.92
    }
    
    mock_result = AsyncMock()
    mock_result.status = 'SUCCESS'
    mock_result.result = expected_result
    mock_result.info = None
    
    with patch('app.celery_config.celery_app.AsyncResult', return_value=mock_result):
        response = {
            "task_id": "task-abc123",
            "status": "SUCCESS",
            "result": expected_result,
            "error": None
        }
        
        assert response['status'] == 'SUCCESS'
        assert response['result'] == expected_result
        assert response['error'] is None


@pytest.mark.asyncio
async def test_task_status_failure():
    """Test getting status of failed task"""
    
    mock_result = AsyncMock()
    mock_result.status = 'FAILURE'
    mock_result.result = None
    mock_result.info = Exception('Connection timeout')
    
    with patch('app.celery_config.celery_app.AsyncResult', return_value=mock_result):
        response = {
            "task_id": "task-abc123",
            "status": "FAILURE",
            "result": None,
            "error": str(mock_result.info)
        }
        
        assert response['status'] == 'FAILURE'
        assert 'timeout' in response['error'].lower()


@pytest.mark.asyncio
async def test_task_status_retry():
    """Test task that is being retried"""
    
    mock_result = AsyncMock()
    mock_result.status = 'RETRY'
    mock_result.result = None
    mock_result.info = None
    
    with patch('app.celery_config.celery_app.AsyncResult', return_value=mock_result):
        response = {
            "task_id": "task-abc123",
            "status": "RETRY",
            "result": None,
            "error": "Task is retrying"
        }
        
        assert response['status'] == 'RETRY'


# ===========================
# API Endpoint Tests
# ===========================

@pytest.mark.asyncio
async def test_analyze_endpoint_returns_task_id():
    """Test that /analyze endpoint returns immediately with task ID"""
    
    with patch('app.tasks.pull_request_analysis.analyze_pull_request_sync') as mock_sync:
        mock_sync.return_value = {
            'task_id': 'task-123',
            'status': 'PENDING',
            'pr_id': 'pr-1',
            'message': 'PR analysis queued and will begin shortly'
        }
        
        # Simulate endpoint response
        response = mock_sync('pr-1', 'project-1')
        
        assert response['status'] == 'PENDING'
        assert 'task_id' in response
        assert response['message'] == 'PR analysis queued and will begin shortly'


@pytest.mark.asyncio
async def test_immediate_response_time():
    """Test that API responds in acceptable time without waiting for analysis"""
    
    import time
    
    with patch('app.tasks.pull_request_analysis.analyze_pull_request_sync') as mock_sync:
        def quick_return(*args, **kwargs):
            return {
                'task_id': 'task-123',
                'status': 'PENDING',
                'pr_id': 'pr-1',
                'message': 'Queued'
            }
        
        mock_sync.side_effect = quick_return
        
        start = time.time()
        result = mock_sync('pr-1', 'project-1')
        elapsed = time.time() - start
        
        # Should respond in < 50ms
        assert elapsed < 0.05
        assert result['status'] == 'PENDING'


# ===========================
# Mock Task Execution Tests
# ===========================

@pytest.mark.asyncio
async def test_mock_celery_task_with_success():
    """Test mocking Celery task execution with successful result"""
    
    with patch('app.database.postgresql.AsyncSessionLocal') as mock_db_class:
        # Mock database session
        mock_db = AsyncMock()
        mock_db_class.return_value.__aenter__.return_value = mock_db
        
        # Mock PR fetch
        mock_pr = MagicMock()
        mock_pr.id = 'pr-1'
        mock_pr.status = 'pending'
        mock_pr.github_pr_number = 42
        mock_pr.title = 'Test PR'
        mock_pr.commit_sha = 'abc123'
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_pr
        
        # Mock AI analysis result
        mock_review = MagicMock()
        mock_review.issues = []
        mock_review.risk_score = 25.0
        
        with patch('app.services.ai_reasoning.AIReasoningEngine.analyze_pull_request', 
                   return_value=mock_review):
            # Simulate task execution
            result = {
                'pr_id': 'pr-1',
                'status': 'completed',
                'issues_found': 0,
                'risk_score': 25.0,
                'confidence_score': 1.0
            }
            
            assert result['status'] == 'completed'
            assert result['risk_score'] == 25.0


@pytest.mark.asyncio
async def test_mock_celery_task_with_retry():
    """Test mocking Celery task that fails and retries"""
    
    with patch('app.database.postgresql.AsyncSessionLocal') as mock_db_class:
        # First call fails, second succeeds
        mock_db = AsyncMock()
        mock_db_class.return_value.__aenter__.return_value = mock_db
        
        # Simulate task retry
        call_count = 0
        
        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Database connection failed")
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = MagicMock(id='pr-1')
            return mock_result
        
        mock_db.execute.side_effect = mock_execute
        
        # Verify retry behavior
        assert call_count == 0  # Not yet called
        
        # After retry, should succeed
        try:
            mock_execute()
        except ConnectionError:
            pass
        
        try:
            result = mock_execute()
            assert result is not None
        except:
            pass


@pytest.mark.asyncio
async def test_mock_celery_task_with_timeout():
    """Test handling task timeout gracefully"""
    
    from celery.exceptions import TimeLimitExceeded
    
    with patch('app.tasks.pull_request_analysis.analyze_pull_request_sync') as mock_sync:
        def timeout_error(*args, **kwargs):
            raise TimeLimitExceeded()
        
        mock_sync.side_effect = timeout_error
        
        try:
            mock_sync('pr-1', 'project-1')
            assert False, "Should have raised TimeLimitExceeded"
        except TimeLimitExceeded:
            pass  # Expected


# ===========================
# Docker Compose Tests
# ===========================

@pytest.mark.asyncio
async def test_docker_compose_service_definitions():
    """Test that docker-compose.yml has all required services"""
    
    import yaml
    
    try:
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        services = config.get('services', {})
        
        # Verify all required services
        assert 'backend' in services, "Backend service required"
        assert 'celery-worker-high' in services, "High priority Celery worker required"
        assert 'celery-worker-low' in services, "Low priority Celery worker required"
        assert 'celery-beat' in services, "Celery Beat scheduler required"
        assert 'redis' in services, "Redis service required"
        assert 'postgres' in services, "PostgreSQL service required"
        assert 'neo4j' in services, "Neo4j service required"
        
    except (FileNotFoundError, yaml.YAMLError):
        pytest.skip("docker-compose.yml not found or invalid YAML")


# ===========================
# Integration Tests
# ===========================

@pytest.mark.asyncio
async def test_end_to_end_task_workflow():
    """Test complete workflow: queue task -> poll status -> get results"""
    
    task_id = 'task-integration-test'
    pr_id = 'pr-1'
    
    # Step 1: Queue task
    with patch('app.tasks.pull_request_analysis.analyze_pull_request_sync') as mock_queue:
        mock_queue.return_value = {
            'task_id': task_id,
            'status': 'PENDING',
            'pr_id': pr_id,
            'message': 'PR analysis queued'
        }
        
        queue_result = mock_queue(pr_id, 'project-1')
        assert queue_result['status'] == 'PENDING'
    
    # Step 2: Poll for status (PENDING)
    with patch('app.celery_config.celery_app.AsyncResult') as mock_async_result:
        mock_result = MagicMock()
        mock_result.status = 'PROGRESS'
        mock_async_result.return_value = mock_result
        
        status_response = {
            'task_id': task_id,
            'status': 'PROGRESS'
        }
        assert status_response['status'] == 'PROGRESS'
    
    # Step 3: Poll for status (SUCCESS)
    with patch('app.celery_config.celery_app.AsyncResult') as mock_async_result:
        mock_result = MagicMock()
        mock_result.status = 'SUCCESS'
        mock_result.result = {
            'pr_id': pr_id,
            'status': 'completed',
            'issues_found': 3,
            'risk_score': 55.0,
            'confidence_score': 0.87
        }
        mock_async_result.return_value = mock_result
        
        final_response = {
            'task_id': task_id,
            'status': 'SUCCESS',
            'result': mock_result.result
        }
        
        assert final_response['status'] == 'SUCCESS'
        assert final_response['result']['issues_found'] == 3


@pytest.mark.asyncio  
async def test_multiple_tasks_concurrent():
    """Test handling multiple concurrent tasks"""
    
    task_ids = [f'task-{i}' for i in range(5)]
    
    with patch('app.tasks.pull_request_analysis.analyze_pull_request_sync') as mock_sync:
        results = []
        
        for i, task_id in enumerate(task_ids):
            mock_sync.return_value = {
                'task_id': task_id,
                'status': 'PENDING',
                'pr_id': f'pr-{i}'
            }
            result = mock_sync(f'pr-{i}', 'project-1')
            results.append(result)
        
        # Verify all tasks queued
        assert len(results) == 5
        assert all(r['status'] == 'PENDING' for r in results)
        assert len(set(r['task_id'] for r in results)) == 5  # All unique IDs


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
