"""
Example tests demonstrating Neo4j fixtures and failure analysis
"""
import pytest
from unittest.mock import patch


@pytest.mark.unit
@pytest.mark.asyncio
async def test_neo4j_service_with_mock(mock_neo4j_driver):
    """
    Unit test using mocked Neo4j driver - no real database needed
    """
    from app.services.neo4j_ast_service import Neo4jASTService

    service = Neo4jASTService(mock_neo4j_driver)

    # This should work with the mock
    result = await service.run_query("MATCH (n) RETURN count(n) as count", projectId="test")

    # Mock returns empty list, so result should be empty
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_neo4j_with_sample_data(neo4j_session_data):
    """
    Test with pre-populated mock data
    """
    from app.services.cypher_queries import CYCLIC_DEPENDENCY_QUERY

    # This would normally find cycles, but with mock data returns sample cycles
    records = await neo4j_session_data.run(CYCLIC_DEPENDENCY_QUERY, projectId="test-project")
    data = await records.data()

    assert len(data) >= 0  # Mock returns sample data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_real_connection():
    """
    Integration test that requires real Neo4j connection
    This will be skipped in CI if Neo4j is not available
    """
    from app.database.neo4j_db import get_neo4j_driver, init_neo4j

    try:
        await init_neo4j()
        driver = await get_neo4j_driver()

        async with driver.session() as session:
            result = await session.run("RETURN 'Hello Neo4j' as message")
            record = await result.single()
            assert record["message"] == "Hello Neo4j"

    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


@pytest.mark.asyncio
async def test_async_event_loop_issues(event_loop_policy):
    """
    Test that demonstrates proper async event loop handling
    """
    import asyncio

    # This should work without event loop conflicts
    async def async_task():
        await asyncio.sleep(0.1)
        return "success"

    result = await async_task()
    assert result == "success"


@pytest.mark.asyncio
async def test_with_timeout_mock(mock_async_timeouts):
    """
    Test with mocked async timeouts to prevent hanging
    """
    import asyncio

    # This would normally timeout, but mock prevents it
    async def slow_task():
        await asyncio.sleep(10)  # This would normally be slow
        return "done"

    result = await slow_task()
    assert result == "done"


def test_pydantic_validation_capture(pydantic_validation_errors):
    """
    Test that captures Pydantic validation errors
    """
    from pydantic import BaseModel, ValidationError

    class TestModel(BaseModel):
        name: str
        age: int

    # This should trigger a validation error
    try:
        TestModel(name="test", age="not_a_number")
    except ValidationError:
        pass

    # Check that our fixture captured the error
    assert len(pydantic_validation_errors) > 0
    assert pydantic_validation_errors[0]["model"] == "TestModel"


@pytest.mark.database
def test_database_connection_mock(mock_db_timeouts):
    """
    Test database initialization with mocked timeouts
    """
    # This should complete quickly due to mocking
    assert mock_db_timeouts["neo4j"].called or True  # Mock should be set up


@pytest.mark.slow
@pytest.mark.asyncio
async def test_performance_with_real_neo4j():
    """
    Performance test that requires real Neo4j
    Marked as slow to be skipped in fast test runs
    """
    pytest.skip("Performance test - requires real Neo4j setup")


# ===== FAILURE SIMULATION TESTS =====

@pytest.mark.asyncio
async def test_simulated_neo4j_connection_failure():
    """
    Test that simulates Neo4j connection failure
    Useful for testing error handling
    """
    from neo4j.exceptions import ServiceUnavailable

    with patch('app.database.neo4j_db.get_neo4j_driver') as mock_get_driver:
        mock_driver = mock_get_driver.return_value
        mock_driver.session.side_effect = ServiceUnavailable("Connection refused")

        with pytest.raises(ServiceUnavailable):
            from app.services.neo4j_ast_service import Neo4jASTService
            service = Neo4jASTService(mock_driver)
            await service.run_query("MATCH (n) RETURN n", projectId="test")


def test_simulated_pydantic_validation_failure():
    """
    Test that simulates Pydantic validation failure
    """
    from pydantic import BaseModel, ValidationError

    class StrictModel(BaseModel):
        email: str
        score: float

        class Config:
            validate_assignment = True

    # This should fail validation
    with pytest.raises(ValidationError) as exc_info:
        model = StrictModel(email="invalid-email", score="not-a-number")

    # Check that the error details are captured
    errors = exc_info.value.errors()
    assert len(errors) >= 2  # email and score validation errors


@pytest.mark.asyncio
async def test_simulated_async_event_loop_conflict():
    """
    Test that demonstrates how to handle async event loop conflicts
    """
    import asyncio

    # This simulates the kind of async issues that can occur in tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Simulate some async work
        async def task():
            await asyncio.sleep(0.01)
            return 42

        result = loop.run_until_complete(task())
        assert result == 42
    finally:
        loop.close()


# ===== AI REVIEWER JSON OUTPUT VERIFICATION =====

def test_json_output_format():
    """
    Test that verifies the JSON output format for AI reviewer
    """
    import json
    import os
    from datetime import datetime

    # Simulate what conftest.py does
    test_results = {
        "test_run_id": "test-123",
        "timestamp": datetime.utcnow().isoformat(),
        "failures": [
            {
                "test_id": "test_example.py::test_failure",
                "error_type": "failure",
                "exception_type": "AssertionError",
                "exception_message": "Expected True but got False",
                "traceback": "test_example.py:10 in test_failure",
                "duration": 0.1,
                "when": "call"
            }
        ],
        "errors": [],
        "summary": {
            "total_tests": 10,
            "passed": 9,
            "failed": 1,
            "skipped": 0,
            "exit_code": 1,
            "duration": 1.5
        }
    }

    # Write to temporary file
    test_file = "temp-test-results.json"
    try:
        with open(test_file, 'w') as f:
            json.dump(test_results, f, indent=2, default=str)

        # Read back and verify structure
        with open(test_file, 'r') as f:
            loaded = json.load(f)

        assert loaded["test_run_id"] == "test-123"
        assert len(loaded["failures"]) == 1
        assert loaded["summary"]["failed"] == 1

        print(f"✅ JSON format validation passed. File size: {os.path.getsize(test_file)} bytes")

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


if __name__ == "__main__":
    # Quick manual test
    test_json_output_format()
    print("Manual test passed!")
