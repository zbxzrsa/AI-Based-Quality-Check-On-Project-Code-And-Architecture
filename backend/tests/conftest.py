"""
Backend test configuration with Neo4j mocking support
"""
import logging
logger = logging.getLogger(__name__)

import pytest
import pytest_asyncio
import asyncio
import json
import os
import subprocess
import sys

# Windows socket issues with ProactorEventLoop in tests
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from typing import AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

# Set TESTING environment variable and override DB name before importing app
os.environ["TESTING"] = "true"
os.environ["POSTGRES_DB"] = "ai_code_review_test"
os.environ["POSTGRES_HOST"] = "127.0.0.1"
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_USER"] = "postgres"
# Keep a non-empty password so Settings validation passes even when the
# local test database uses trust auth on port 5433.
os.environ["POSTGRES_PASSWORD"] = "postgres123"

from app.main import app
from app.database.postgresql import get_db
from app.core.config import settings

# Import common fixtures to make them available to all tests


def is_docker_available() -> bool:
    """Check if Docker is available and running"""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers",
        "requires_docker: mark test as requiring Docker to run"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests that require Docker if Docker is not available"""
    if not is_docker_available():
        skip_docker = pytest.mark.skip(reason="Docker is not available - start Docker to run these tests")
        for item in items:
            if "requires_docker" in item.keywords:
                item.add_marker(skip_docker)

# Test database URL
TEST_DATABASE_URL = settings.postgres_url

# Test results collection for AI reviewer
test_results = {
    "test_run_id": None,
    "timestamp": None,
    "failures": [],
    "errors": [],
    "summary": {}
}


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session using a fresh engine for isolation"""
    from app.database.postgresql import Base
    logger.info("\n[DB_FIXTURE] Starting db_session setup")
    
    # Create a fresh engine
    engine = create_async_engine(
        settings.postgres_url,
        poolclass=NullPool,
        echo=False
    )
    
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        logger.info("[DB_FIXTURE] Creating tables")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[DB_FIXTURE] Tables created")
        
        async with async_session_factory() as session:
            logger.info("[DB_FIXTURE] Yielding session")
            yield session
            logger.info("[DB_FIXTURE] Test finished, closing session")
        
        logger.info("[DB_FIXTURE] Dropping tables")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("[DB_FIXTURE] Tables dropped")
    except Exception as e:
        logger.info("[DB_FIXTURE] ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        logger.info("[DB_FIXTURE] Disposing engine")
        await engine.dispose()
        logger.info("[DB_FIXTURE] Engine disposed")


@pytest_asyncio.fixture(scope="function")
async def async_session(db_session: AsyncSession) -> AsyncSession:
    """Alias for db_session to match test expectations"""
    return db_session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """Create test client"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Get authentication headers"""
    from app.utils.jwt import create_access_token
    token = create_access_token({"sub": str(test_user.id), "email": test_user.email, "role": test_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user"""
    from app.models import User
    from app.utils.password import hash_password
    
    user = User(
        email="test@example.com",
        password_hash=hash_password("TestPass123!"),
        full_name="Test User",
        role="developer"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def access_token(test_user):
    """Generate access token for test user"""
    from app.utils.jwt import create_access_token
    return create_access_token({"sub": str(test_user.id), "email": test_user.email, "role": test_user.role.value})


# ===== NEO4J MOCKING FIXTURES =====

@pytest_asyncio.fixture(scope="function", autouse=True)
async def mock_neo4j_driver():
    """
    Mock Neo4j driver for unit tests that don't need real database
    Returns a mock driver that simulates Neo4j behavior
    """
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_record = MagicMock()

    mock_result.data.return_value = []
    mock_result.single.return_value = mock_record
    mock_session.run.return_value = mock_result
    mock_session.execute_query.return_value = ([], mock_result)
    mock_session.execute_write.return_value = None
    mock_session.execute_read.return_value = []

    mock_tx = AsyncMock()
    mock_tx.run.return_value = mock_result
    mock_session.begin_transaction.return_value = mock_tx

    mock_driver = AsyncMock()
    mock_driver.session.return_value = mock_session
    mock_driver.verify_connectivity.return_value = None

    with patch('app.database.neo4j_db.get_neo4j_driver', return_value=mock_driver):
        yield mock_driver


@pytest_asyncio.fixture(scope="function")
async def neo4j_session_data():
    """
    Pre-populated mock Neo4j session with test data
    Useful for integration tests that need realistic graph data
    """
    mock_session = AsyncMock()

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
    """
    try:
        from testcontainers.neo4j import Neo4jContainer

        container = Neo4jContainer("neo4j:5", password=TEST_PASSWORD)
        container.start()

        original_uri = os.environ.get('NEO4J_URI')
        original_user = os.environ.get('NEO4J_USER')
        original_password = os.environ.get('NEO4J_PASSWORD')

        os.environ['NEO4J_URI'] = container.get_connection_url()
        os.environ['NEO4J_USER'] = "neo4j"
        os.environ['NEO4J_PASSWORD'] = TEST_PASSWORD

        yield container

        container.stop()

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

    output_file = os.environ.get('TEST_RESULTS_JSON', 'test-results.json')
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)

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
                for failure in test_results['failures'][:5]:
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
        "exit_code": exitstatus,
    }


# ===== ASYNC TIMEOUT FIXTURES =====

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

        mock_postgres.return_value = None
        mock_neo4j.return_value = None
        mock_redis.return_value = None

        yield {
            "postgres": mock_postgres,
            "neo4j": mock_neo4j,
            "redis": mock_redis
        }


# ===== REDIS MOCKING FIXTURES =====

@pytest.fixture(scope="function", autouse=True)
def mock_redis_client():
    """
    Mock Redis client for unit tests
    """
    storage = {}
    ttls = {}
    
    class MockRedis:
        async def set(self, key: str, value: str, ex: Optional[int] = None, **kwargs):
            nx = kwargs.get('nx', False)
            if nx and key in storage:
                return None
            storage[key] = value
            if ex:
                ttls[key] = ex
            return True
        
        async def get(self, key: str):
            return storage.get(key)
        
        async def exists(self, key: str):
            return 1 if key in storage else 0
        
        async def delete(self, key: str):
            if key in storage:
                del storage[key]
                if key in ttls:
                    del ttls[key]
            return 1
        
        async def ttl(self, key: str):
            return ttls.get(key, -1)
    
    mock_redis = MockRedis()
    
    import app.database.redis_db
    app.database.redis_db.redis_client = mock_redis
    
    with patch('app.database.redis_db.get_redis', return_value=mock_redis):
        with patch('app.utils.jwt.get_redis', return_value=mock_redis):
            yield mock_redis
    
    app.database.redis_db.redis_client = None
