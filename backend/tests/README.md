# Backend Testing Guide

This guide explains how to run tests for the FastAPI backend with Neo4j integration, including debugging common failure patterns and using the AI reviewer-compatible JSON output.

## 🚀 Quick Start

### Install Test Dependencies
```bash
cd backend
pip install -r requirements-test.txt
```

### Run Tests with Different Configurations

```bash
# Run all tests
pytest

# Run only unit tests (no database required)
pytest -m "unit"

# Run integration tests (requires databases)
pytest -m "integration"

# Run tests with detailed output
pytest -v

# Run specific test file
pytest tests/test_neo4j_fixtures.py -v

# Run tests and generate coverage report
pytest --cov=app --cov-report=html
```

## 🛠️ Common Test Failure Patterns & Solutions

### 1. Neo4j Connection Issues

**Symptoms:**
- `neo4j.exceptions.ServiceUnavailable: Connection refused`
- `Connection timeout` errors
- `Failed to establish connection` messages

**Solutions:**

#### Option A: Use Mocked Neo4j (Recommended for Unit Tests)
```python
@pytest.mark.asyncio
async def test_my_service_with_mock(mock_neo4j_driver):
    from app.services.my_service import MyService

    service = MyService()
    result = await service.do_something()

    assert result is not None
```

#### Option B: Use Testcontainers (For Integration Tests)
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_real_neo4j(neo4j_container):
    # Testcontainers automatically starts Neo4j
    from app.database.neo4j_db import init_neo4j

    await init_neo4j()
    # Your test code here
```

#### Option C: Skip Tests Requiring Neo4j
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_real_connection():
    try:
        await init_neo4j()
        # Test logic
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
```

### 2. Async Event Loop Issues

**Symptoms:**
- `RuntimeError: Cannot run the event loop while another loop is running`
- `There is no current event loop` errors
- Tests hang or timeout unexpectedly

**Solutions:**

#### Use the event_loop_policy fixture:
```python
@pytest.mark.asyncio
async def test_async_functionality(event_loop_policy):
    # This fixture handles event loop conflicts
    result = await my_async_function()
    assert result == expected
```

#### Use mock_async_timeouts to prevent hanging:
```python
@pytest.mark.asyncio
async def test_with_timeouts(mock_async_timeouts):
    # Prevents async operations from actually timing out
    result = await slow_operation()
    assert result is not None
```

### 3. Pydantic Validation Failures

**Symptoms:**
- `ValidationError: 1 validation error for ModelName`
- Unexpected type validation errors
- Model instantiation failures

**Debugging:**
```python
def test_validation_with_capture(pydantic_validation_errors):
    try:
        # Code that should trigger validation error
        MyModel(field="invalid_value")
    except ValidationError:
        pass

    # Check what errors were captured
    assert len(pydantic_validation_errors) > 0
    print(pydantic_validation_errors[0])
```

## 📊 AI Reviewer JSON Output

### Automatic JSON Generation

Tests automatically generate a JSON report compatible with your AI-Based Reviewer's Project Management module:

```json
{
  "test_run_id": "uuid-string",
  "timestamp": "2024-01-17T10:59:26.123456",
  "failures": [
    {
      "test_id": "tests/test_example.py::TestClass::test_method",
      "test_name": "test_method",
      "test_file": "tests/test_example.py",
      "error_type": "failure",
      "exception_type": "AssertionError",
      "exception_message": "Expected 5 but got 3",
      "traceback": "Full traceback string",
      "duration": 0.123,
      "when": "call"
    }
  ],
  "errors": [...],
  "summary": {
    "total_tests": 150,
    "passed": 145,
    "failed": 3,
    "skipped": 2,
    "exit_code": 1,
    "duration": 45.67
  }
}
```

### Custom JSON Output Location

Set the `TEST_RESULTS_JSON` environment variable:

```bash
export TEST_RESULTS_JSON=my-custom-results.json
pytest
```

### GitHub Actions Integration

The CI/CD pipeline automatically analyzes failures:

```yaml
- name: Analyze Test Failures
  if: failure()
  run: |
    python -c "
    import json
    with open('test-results-ai-reviewer.json') as f:
        results = json.load(f)

    neo4j_failures = [f for f in results['failures'] + results['errors']
                     if 'neo4j' in f['exception_message'].lower()]

    print(f'Neo4j-related failures: {len(neo4j_failures)}')
    # Additional analysis...
    "
```

## 🧪 Available Test Fixtures

### Neo4j Fixtures

| Fixture | Purpose | Use Case |
|---------|---------|----------|
| `mock_neo4j_driver` | Fully mocked Neo4j driver | Unit tests, no database needed |
| `neo4j_session_data` | Mock with sample data | Testing with realistic responses |
| `neo4j_container` | Real Neo4j in container | Integration tests (requires testcontainers) |

### Async/Pydantic Fixtures

| Fixture | Purpose | Use Case |
|---------|---------|----------|
| `event_loop_policy` | Handle event loop conflicts | Async tests with loop issues |
| `mock_async_timeouts` | Prevent timeout hangs | Fast async testing |
| `pydantic_validation_errors` | Capture validation errors | Debugging model validation |

### Database Fixtures

| Fixture | Purpose | Use Case |
|---------|---------|----------|
| `db_session` | PostgreSQL test session | API endpoint testing |
| `client` | FastAPI test client | HTTP endpoint testing |
| `mock_db_timeouts` | Mock database init | Fast database testing |

## 🏷️ Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only Neo4j-related tests
pytest -m neo4j

# Run only async tests
pytest -m async

# Skip slow tests
pytest -m "not slow"

# Combine markers
pytest -m "unit and not slow"
```

## 🔧 Configuration Files

### pytest.ini
Contains pytest configuration including:
- Test discovery patterns
- Coverage settings
- Warning filters
- Custom markers

### conftest.py
Contains:
- Global fixtures for all tests
- Test result collection hooks
- Session-level setup/teardown

## 🚨 Troubleshooting

### Tests Hanging
```bash
# Add timeout to prevent hanging
pytest --timeout=300

# Run with verbose output to see what's happening
pytest -v -s
```

### Database Connection Issues
```bash
# Check if databases are running
docker ps

# Test database connections manually
python tests/test_connections.py

# Use mocked fixtures for faster testing
pytest -m "unit"  # Only runs tests with mocked dependencies
```

### Import Errors
```bash
# Ensure you're in the correct directory
cd backend

# Install missing dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

## 📈 Performance Testing

```bash
# Run performance benchmarks
pytest --benchmark-only

# Compare performance between runs
pytest --benchmark-compare

# Save benchmark results
pytest --benchmark-save=mybench
```

## 🤖 AI Reviewer Integration

The JSON output format is designed to be directly ingestible by your AI-Based Quality Check system:

1. **Structured Data**: All test failures include complete context
2. **Categorization**: Failures are categorized by type (Neo4j, async, validation, etc.)
3. **Traceability**: Full stack traces and timing information
4. **Session Tracking**: Each test run has a unique ID for tracking

### Example AI Processing Script

```python
import json

def analyze_test_failures(json_file):
    with open(json_file) as f:
        results = json.load(f)

    # Categorize failures
    categories = {
        'neo4j': [],
        'async': [],
        'validation': [],
        'other': []
    }

    for failure in results['failures'] + results['errors']:
        msg = failure['exception_message'].lower()

        if 'neo4j' in msg or 'connection' in msg:
            categories['neo4j'].append(failure)
        elif 'async' in msg or 'event loop' in msg:
            categories['async'].append(failure)
        elif 'validation' in msg or 'pydantic' in msg:
            categories['validation'].append(failure)
        else:
            categories['other'].append(failure)

    return categories
```

This testing setup provides comprehensive coverage while being resilient to common FastAPI/Neo4j testing challenges.
