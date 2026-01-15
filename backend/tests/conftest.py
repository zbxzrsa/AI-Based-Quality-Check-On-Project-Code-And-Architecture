"""
Backend test configuration
"""
import pytest
import asyncio
from typing import AsyncGenerator
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
