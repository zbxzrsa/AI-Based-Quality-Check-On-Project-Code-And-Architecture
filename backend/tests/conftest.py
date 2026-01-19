"""
Backend test configuration with Neo4j mocking support
"""
import pytest
import asyncio
import json
import os
from typing import AsyncGenerator, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.database.postgresql import Base, get_db
from app.core.config import settings

# Test database URL
TEST_DATABASE_URL = settings.POSTGRES_URL.replace("/ai_code_review", "/ai_code_review_test")

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# Test results collection for AI reviewer
test_results = {
    "test_run_id": None,
    "timestamp": None,
    "failures": [],
    "errors": [],
    "summary": {}
}


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(access_token: str):
    """Get authentication headers"""
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create test user"""
    from app.models import User
    from app.utils.password import hash_password
    
    user = User(
        email="test@example.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="Test User",
        role="developer"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def access_token(test_user):
    """Generate access token for test user"""
    from app.utils.jwt import create_access_token
    return create_access_token({"sub": test_user.email, "user_id": str(test_user.id)})


# ===== NEO4J MOCKING FIXTURES =====

@pytest.fixture(scope="function")
async def mock_neo4j_driver():
    """
    Mock Neo4j driver for unit tests that don't need real database
    Returns a mock driver that simulates Neo4j behavior
    """
    # Create mock session
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_record = MagicMock()

    # Configure mock result
    mock_result.data.return_value = []
    mock_result.single.return_value = mock_record
    mock_session.run.return_value = mock_result
    mock_session.execute_query.return_value = ([], mock_result)
    mock_session.execute_write.return_value = None
    mock_session.execute_read.return_value = []

    # Create mock transaction
    mock_tx = AsyncMock()
    mock_tx.run.return_value = mock_result
    mock_session.begin_transaction.return_value = mock_tx

    # Create mock driver
    mock_driver = AsyncMock()
    mock_driver.session.return_value = mock_session
    mock_driver.verify_connectivity.return_value = None

    # Patch the global driver
    with patch('app.database.neo4j_db.get_neo4j_driver', return_value=mock_driver):
        yield mock_driver


@pytest.fixture(scope="function")
async def neo4j_session_data():
    """
    Pre-populated mock Neo4j session with test data
    Useful for integration tests that need realistic graph data
    """
    mock_session = AsyncMock()

    # Mock result with sample data
    mock_result = AsyncMock()
    mock_records = [
        MagicMock(data=MagicMock(return_value={
            "module": "test_module",
            "cycle_path": ["A", "B", "C", "A"],
            "cycle_length": 3,
            "relationship_types": ["DEPENDS_ON", "DEPENDS_ON", "DEPENDS_ON"]
        }))
    ]
    mock_result.data.return_value = mock_records
    mock_result.single.return_value = mock_records[0] if mock_records else None

    mock_session.run.return_value = mock_result
    mock_session.execute_query.return_value = (mock_records, mock_result)

    mock_driver = AsyncMock()
    mock_driver.session.return_value = mock_session

    with patch('app.database.neo4j_db.get_neo4j_driver', return_value=mock_driver):
        yield mock_session


@pytest.fixture(scope="session")
def neo4j_container():
    """
    Testcontainers Neo4j fixture for integration tests
    Requires: pip install testcontainers[neo4j]
    """
    try:
        from testcontainers.neo4j import Neo4jContainer

        container = Neo4jContainer("neo4j:5", password="testpassword")
        container.start()

        # Override environment variables for tests
        original_uri = os.environ.get('NEO4J_URI')
        original_user = os.environ.get('NEO4J_USER')
        original_password = os.environ.get('NEO4J_PASSWORD')

        os.environ['NEO4J_URI'] = container.get_connection_url()
        os.environ['NEO4J_USER'] = "neo4j"
        os.environ['NEO4J_PASSWORD'] = "testpassword"

        yield container

        # Cleanup
        container.stop()

        # Restore original environment
        if original_uri:
            os.environ['NEO4J_URI'] = original_uri
        if original_user:
            os.environ['NEO4J_USER'] = original_user
        if original_password:
            os.environ['NEO4J_PASSWORD'] = original_password

    except ImportError:
        pytest.skip("testcontainers not installed. Install with: pip install testcontainers[neo4j]")


# ===== TEST FAILURE COLLECTION FOR AI REVIEWER =====

@pytest.fixture(scope="session", autouse=True)
def collect_test_results():
    """Collect test results for AI reviewer ingestion"""
    import uuid
    from datetime import datetime, timezone

    test_results["test_run_id"] = str(uuid.uuid4())
    test_results["timestamp"] = datetime.now(timezone.utc).isoformat()

    yield

    # Write results to JSON file at end of test session
    output_file = os.environ.get('TEST_RESULTS_JSON', 'test-results.json')
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)

    # Also write to GitHub Actions summary if running in CI
    if os.environ.get('GITHUB_ACTIONS'):
        summary_file = os.environ.get('GITHUB_STEP_SUMMARY', '/dev/null')
        with open(summary_file, 'a') as f:
            f.write("## 🧪 Test Results for AI Reviewer\n\n")
            f.write(f"**Test Run ID:** {test_results['test_run_id']}\n")
            f.write(f"**Timestamp:** {test_results['timestamp']}\n")
            f.write(f"**Failures:** {len(test_results['failures'])}\n")
            f.write(f"**Errors:** {len(test_results['errors'])}\n\n")

            if test_results['failures']:
                f.write("### ❌ Test Failures\n")
                for failure in test_results['failures'][:5]:  # Show first 5
                    f.write(f"- `{failure['test_id']}`: {failure['error_type']}\n")
                if len(test_results['failures']) > 5:
                    f.write(f"- ... and {len(test_results['failures']) - 5} more\n")


def pytest_exception_interact(node, call, report):
    """Hook to capture test failures for AI reviewer"""
    if report.failed:
        failure_data = {
            "test_id": node.nodeid,
            "test_name": node.name,
            "test_file": str(node.fspath),
            "error_type": "failure" if call.excinfo.typename == "AssertionError" else "error",
            "exception_type": call.excinfo.typename,
            "exception_message": str(call.excinfo.value),
            "traceback": str(call.excinfo.traceback),
            "duration": call.duration,
            "when": call.when
        }

        if call.excinfo.typename == "AssertionError":
            test_results["failures"].append(failure_data)
        else:
            test_results["errors"].append(failure_data)


def pytest_sessionfinish(session, exitstatus):
    """Hook to collect session summary"""
    test_results["summary"] = {
        "total_tests": session.testscollected,
        "passed": len([r for r in session.get_reports() if r.passed]),
        "failed": len([r for r in session.get_reports() if r.failed]),
        "skipped": len([r for r in session.get_reports() if r.skipped]),
        "exit_code": exitstatus,
        "duration": session.duration
    }


# ===== ASYNC EVENT LOOP FIXTURES =====

@pytest.fixture(scope="function")
def event_loop_policy():
    """
    Fixture to handle async event loop issues in pytest-asyncio
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)

    yield loop

    loop.close()


@pytest.fixture(scope="function")
def mock_async_timeouts():
    """
    Mock asyncio timeouts to prevent hanging tests
    """
    with patch('asyncio.wait_for') as mock_wait_for:
        mock_wait_for.side_effect = lambda coro, timeout: coro
        yield mock_wait_for


# ===== PYDANTIC VALIDATION TEST HELPERS =====

@pytest.fixture(scope="function")
def pydantic_validation_errors():
    """
    Fixture that captures Pydantic validation errors for testing
    """
    from pydantic import ValidationError
    errors = []

    original_init = ValidationError.__init__

    def capture_validation_error(self, errors_list, *args, **kwargs):
        errors.append({
            "errors": errors_list,
            "model": self.model.__name__ if hasattr(self, 'model') else None
        })
        return original_init(self, errors_list, *args, **kwargs)

    ValidationError.__init__ = capture_validation_error

    yield errors

    ValidationError.__init__ = original_init


# ===== DATABASE CONNECTION TIMEOUT FIXTURES =====

@pytest.fixture(scope="function")
def mock_db_timeouts():
    """
    Mock database connection timeouts for faster test execution
    """
    with patch('app.database.postgresql.init_postgres') as mock_postgres, \
         patch('app.database.neo4j_db.init_neo4j') as mock_neo4j, \
         patch('app.database.redis_db.init_redis') as mock_redis:

        # Make init functions return immediately
        mock_postgres.return_value = None
        mock_neo4j.return_value = None
        mock_redis.return_value = None

        yield {
            "postgres": mock_postgres,
            "neo4j": mock_neo4j,
            "redis": mock_redis
        }
