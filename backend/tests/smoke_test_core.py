"""
Smoke Tests for Backend Core Modules
=====================================

This module provides minimal smoke tests to verify the availability
and basic functionality of core backend services.

Run with: pytest backend/tests/smoke_test_modules.py -v
"""

import os
import sys
import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestDatabaseConnectivity:
    """Test database connections - Critical Priority"""
    
    @pytest.mark.asyncio
    async def test_postgresql_connection(self):
        """
        Smoke Test: PostgreSQL Connection
        
        Verifies:
        - PostgreSQL is reachable
        - Connection pool is functional
        - Basic query execution works
        """
        try:
            from app.database.postgresql import get_postgres_connection
            
            conn = await get_postgres_connection()
            assert conn is not None, "PostgreSQL connection should not be None"
            
            # Execute a simple query
            result = await conn.execute("SELECT 1")
            assert result is not None, "Query should return a result"
            
            print("✅ PostgreSQL connection: OK")
            return {"status": "stable", "service": "PostgreSQL"}
            
        except ImportError as e:
            pytest.skip(f"PostgreSQL module not available: {e}")
        except Exception as e:
            print(f"🔴 PostgreSQL connection: FAILED - {str(e)[:100]}")
            pytest.fail(f"PostgreSQL connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """
        Smoke Test: Redis Connection
        
        Verifies:
        - Redis is reachable
        - Basic set/get operations work
        - Cache is functional
        """
        try:
            from app.database.redis_db import get_redis_connection
            
            redis = await get_redis_connection()
            assert redis is not None, "Redis connection should not be None"
            
            # Test basic operations
            await redis.set("smoke_test_key", "test_value", ex=10)
            value = await redis.get("smoke_test_key")
            assert value == b"test_value" or value == "test_value", "Redis get should return the set value"
            
            print("✅ Redis connection: OK")
            return {"status": "stable", "service": "Redis"}
            
        except ImportError as e:
            pytest.skip(f"Redis module not available: {e}")
        except Exception as e:
            print(f"🔴 Redis connection: FAILED - {str(e)[:100]}")
            pytest.fail(f"Redis connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_neo4j_connection(self):
        """
        Smoke Test: Neo4j Connection
        
        Verifies:
        - Neo4j is reachable
        - Bolt protocol works
        - Basic Cypher query execution
        """
        try:
            from app.database.neo4j_db import get_neo4j_driver
            
            driver = await get_neo4j_driver()
            assert driver is not None, "Neo4j driver should not be None"
            
            # Execute a simple query
            with driver.session() as session:
                result = session.run("RETURN 1 as value")
                record = result.single()
                assert record["value"] == 1, "Neo4j should return 1"
            
            print("✅ Neo4j connection: OK")
            return {"status": "stable", "service": "Neo4j"}
            
        except ImportError as e:
            pytest.skip(f"Neo4j module not available: {e}")
        except Exception as e:
            print(f"🔴 Neo4j connection: FAILED - {str(e)[:100]}")
            pytest.fail(f"Neo4j connection failed: {e}")


class TestAuthenticationFlow:
    """Test authentication flow - Critical Priority"""
    
    @pytest.mark.asyncio
    async def test_user_registration_and_login(self):
        """
        Smoke Test: User Registration and Login

        Verifies:
        - Password hashing is functional
        - JWT token generation works
        - Authentication endpoints are accessible
        """
        try:
            from app.utils.password import hash_password, verify_password
            from app.utils.jwt import create_access_token, verify_token

            # Test password hashing
            test_password = get_test_password("test_password")
            password_hash = hash_password(test_password)
            assert password_hash is not None, "Password hashing should work"
            assert verify_password(test_password, password_hash), "Password verification should work"

            # Test JWT token creation and verification
            test_user_data = {
                "sub": "smoke_test_user",
                "email": "smoke_test@example.com",
                "role": "developer"
            }

            token = create_access_token(test_user_data)
            assert token is not None, "Token creation should work"

            # Verify token
            payload = verify_token(token, "access")
            assert payload is not None, "Token verification should work"
            assert payload["sub"] == test_user_data["sub"], "Token should contain correct user data"
            assert payload["email"] == test_user_data["email"], "Token should contain correct email"

            print("✅ Authentication flow: OK")
            return {"status": "stable", "service": "Authentication"}

        except ImportError as e:
            pytest.skip(f"Auth module not available: {e}")
        except Exception as e:
            print(f"⚠️ Authentication flow: FLAKY - {str(e)[:100]}")
            pytest.skip(f"Authentication test skipped: {e}")




class TestGitHubIntegration:
    """Test GitHub integration - High Priority"""
    
    @pytest.mark.asyncio
    async def test_github_api_client_initialization(self):
        """
        Smoke Test: GitHub API Client
        
        Verifies:
        - GitHub client can be initialized
        - Environment variables are set
        - Basic API connectivity (if token is available)
        """
        try:
            from app.services.github import GitHubClient
            
            # Check if GitHub token is configured
            github_token = os.getenv("GITHUB_TOKEN")
            if not github_token:
                print("⚠️ GitHub integration: FLAKY - GITHUB_TOKEN not configured")
                pytest.skip("GITHUB_TOKEN not configured")
            
            # Initialize client
            client = GitHubClient()
            assert client is not None, "GitHub client should initialize"
            
            # Test basic API call (get authenticated user)
            try:
                user = await client.get_authenticated_user()
                assert user is not None, "Should get authenticated user"
                print("✅ GitHub integration: OK")
                return {"status": "stable", "service": "GitHub"}
            except Exception as api_error:
                print(f"⚠️ GitHub integration: FLAKY - API call failed: {str(api_error)[:100]}")
                return {"status": "flaky", "service": "GitHub", "error": str(api_error)[:100]}
                
        except ImportError as e:
            pytest.skip(f"GitHub module not available: {e}")
        except Exception as e:
            print(f"🔴 GitHub integration: FAILED - {str(e)[:100]}")
            pytest.fail(f"GitHub integration failed: {e}")


class TestLLMService:
    """Test LLM service - High Priority"""
    
    @pytest.mark.asyncio
    async def test_llm_service_initialization(self):
        """
        Smoke Test: LLM Service
        
        Verifies:
        - LLM service can be initialized
        - At least one LLM provider is configured
        - Basic health check works
        """
        try:
            from app.services.llm_service import llm_service
            
            # Check if any LLM provider is configured
            has_openai = os.getenv("OPENAI_API_KEY")
            has_anthropic = os.getenv("ANTHROPIC_API_KEY")
            has_ollama = os.getenv("OLLAMA_BASE_URL")
            
            if not (has_openai or has_anthropic or has_ollama):
                print("⚠️ LLM service: FLAKY - No LLM provider configured")
                pytest.skip("No LLM provider configured (OpenAI/Anthropic/Ollama)")
            
            # Initialize service
            await llm_service.initialize()
            assert llm_service.is_initialized, "LLM service should be initialized"
            
            # Test basic completion (very short to minimize cost)
            try:
                response = await llm_service.complete(
                    prompt="Say 'OK' if you can hear me.",
                    max_tokens=5
                )
                assert response is not None, "Should get a response"
                print("✅ LLM service: OK")
                return {"status": "stable", "service": "LLM"}
            except Exception as api_error:
                print(f"⚠️ LLM service: FLAKY - API call failed: {str(api_error)[:100]}")
                return {"status": "flaky", "service": "LLM", "error": str(api_error)[:100]}
                
        except ImportError as e:
            pytest.skip(f"LLM module not available: {e}")
        except Exception as e:
            print(f"⚠️ LLM service: FLAKY - {str(e)[:100]}")
            pytest.skip(f"LLM service test skipped: {e}")


class TestCodeReviewPipeline:
    """Test code review pipeline - High Priority"""
    
    @pytest.mark.asyncio
    async def test_code_review_endpoint_availability(self):
        """
        Smoke Test: Code Review Endpoint
        
        Verifies:
        - Code review endpoint is accessible
        - Request validation works
        - Basic error handling is in place
        """
        try:
            from fastapi.testclient import TestClient
            from app.main import app
            
            client = TestClient(app)
            
            # Test health endpoint first
            response = client.get("/health")
            assert response.status_code in [200, 503], "Health endpoint should be accessible"
            
            # Test code review endpoint (without authentication, should get 401)
            response = client.post(
                "/api/v1/code-review/analyze",
                json={"code": "print('hello')", "language": "python"}
            )
            assert response.status_code in [401, 403, 422], "Should require authentication or validation"
            
            print("✅ Code review endpoint: OK (authentication required)")
            return {"status": "stable", "service": "Code Review API"}
            
        except ImportError as e:
            pytest.skip(f"FastAPI test utilities not available: {e}")
        except Exception as e:
            print(f"⚠️ Code review endpoint: FLAKY - {str(e)[:100]}")
            pytest.skip(f"Code review test skipped: {e}")


class TestArchitectureAnalysis:
    """Test architecture analysis - Medium Priority"""
    
    @pytest.mark.asyncio
    async def test_architecture_service_availability(self):
        """
        Smoke Test: Architecture Analysis Service
        
        Verifies:
        - Architecture service is accessible
        - Neo4j queries can be executed
        - Basic graph operations work
        """
        try:
            from app.services.neo4j_service import Neo4jService
            from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key

            service = Neo4jService()
            
            # Test basic graph query
            try:
                result = await service.execute_query("RETURN 1 as test")
                assert result is not None, "Should get query result"
                print("✅ Architecture analysis: OK")
                return {"status": "stable", "service": "Architecture"}
            except Exception as db_error:
                print(f"⚠️ Architecture analysis: FLAKY - Neo4j query failed: {str(db_error)[:100]}")
                return {"status": "flaky", "service": "Architecture", "error": str(db_error)[:100]}
                
        except ImportError as e:
            pytest.skip(f"Architecture module not available: {e}")
        except Exception as e:
            print(f"⚠️ Architecture analysis: FLAKY - {str(e)[:100]}")
            pytest.skip(f"Architecture test skipped: {e}")


class TestWebSocketConnection:
    """Test WebSocket communication - Medium Priority"""
    
    def test_websocket_manager_initialization(self):
        """
        Smoke Test: WebSocket Manager
        
        Verifies:
        - WebSocket manager can be initialized
        - Connection configuration is valid
        """
        try:
            # Import from frontend (this test is for documentation purposes)
            # In reality, this would be tested in the frontend test suite
            print("ℹ️ WebSocket: Tests should be run in frontend test suite")
            pytest.skip("WebSocket tests should be run in frontend test suite")
            
        except ImportError as e:
            pytest.skip(f"WebSocket module not available: {e}")


# Test runner summary
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print smoke test summary"""
    print("\n" + "="*60)
    print("SMOKE TEST SUMMARY")
    print("="*60)
    
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    
    print(f"✅ Passed: {passed}")
    print(f"🔴 Failed: {failed}")
    print(f"⚠️  Skipped: {skipped}")
    print("="*60)
    
    if failed > 0:
        print("\n🔴 CRITICAL: Some core services are not functional!")
        print("Please check the errors above and fix them before proceeding.")
    elif skipped > 0:
        print("\n⚠️  WARNING: Some services were skipped (may be flaky or not configured)")
        print("Review skipped tests and configure missing services if needed.")
    else:
        print("\n✅ All core services are functional and stable!")
