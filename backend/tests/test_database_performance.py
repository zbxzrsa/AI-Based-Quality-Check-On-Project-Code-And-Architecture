"""
Database performance tests

Tests query performance under load and verifies P95 response time < 500ms.

Requirements:
- 5.9: Performance tests verifying API response time under 500ms for P95
- 10.1: API responds within 500ms for P95 of requests
- 10.5: Database query optimization with proper indexes
"""
import logging
logger = logging.getLogger(__name__)

import pytest
import asyncio
import time
import statistics
from typing import List
from uuid import uuid4

from sqlalchemy import text, select
from app.database.postgresql import AsyncSessionLocal
from app.models import User, Project, PullRequest, CodeReview, ReviewComment
from app.utils.password import hash_password
from backend.tests.utils.secure_test_data import get_test_password


@pytest.fixture
async def test_data():
    """Create test data for performance testing"""
    async with AsyncSessionLocal() as session:
        # Create test user
        user = User(
            id=uuid4(),
            email=f"perf_test_{uuid4()}@example.com",
            password_hash=hash_password(get_test_password("database_performance_hash_marker")),
            role="developer",
            full_name="Performance Test User"
        )
        session.add(user)
        
        # Create test project
        project = Project(
            id=uuid4(),
            owner_id=user.id,
            name=f"Performance Test Project {uuid4()}",
            description="Test project for performance testing",
            language="python"
        )
        session.add(project)
        
        await session.commit()
        
        # Create multiple PRs for testing
        pr_ids = []
        for i in range(50):
            pr = PullRequest(
                id=uuid4(),
                project_id=project.id,
                author_id=user.id,
                github_pr_number=i + 1,
                title=f"Test PR {i + 1}",
                description=f"Test PR description {i + 1}",
                status="pending" if i % 3 == 0 else "reviewed"
            )
            session.add(pr)
            pr_ids.append(pr.id)
        
        await session.commit()
        
        # Create reviews and comments for some PRs
        for i, pr_id in enumerate(pr_ids[:20]):
            review = CodeReview(
                id=uuid4(),
                pull_request_id=pr_id,
                status="completed"
            )
            session.add(review)
            await session.flush()
            
            # Add comments
            for j in range(5):
                comment = ReviewComment(
                    id=uuid4(),
                    review_id=review.id,
                    file_path=f"src/file_{j}.py",
                    line_number=j * 10,
                    message=f"Test comment {j}",
                    severity="medium" if j % 2 == 0 else "high"
                )
                session.add(comment)
        
        await session.commit()
        
        yield {
            "user_id": user.id,
            "project_id": project.id,
            "pr_ids": pr_ids
        }
        
        # Cleanup
        await session.execute(
            text("DELETE FROM review_comments WHERE review_id IN (SELECT id FROM code_reviews WHERE pull_request_id = ANY(:pr_ids))"),
            {"pr_ids": pr_ids}
        )
        await session.execute(
            text("DELETE FROM code_reviews WHERE pull_request_id = ANY(:pr_ids)"),
            {"pr_ids": pr_ids}
        )
        await session.execute(
            text("DELETE FROM pull_requests WHERE project_id = :project_id"),
            {"project_id": project.id}
        )
        await session.execute(
            text("DELETE FROM projects WHERE id = :project_id"),
            {"project_id": project.id}
        )
        await session.execute(
            text("DELETE FROM users WHERE id = :user_id"),
            {"user_id": user.id}
        )
        await session.commit()


async def measure_query_time(query_func) -> float:
    """Measure query execution time in milliseconds"""
    start = time.perf_counter()
    await query_func()
    end = time.perf_counter()
    return (end - start) * 1000  # Convert to milliseconds


def calculate_percentile(times: List[float], percentile: int) -> float:
    """Calculate percentile from list of times"""
    if not times:
        return 0.0
    sorted_times = sorted(times)
    index = int(len(sorted_times) * percentile / 100)
    return sorted_times[min(index, len(sorted_times) - 1)]


@pytest.mark.asyncio
async def test_query_prs_by_project_performance(test_data):
    """
    Test performance of querying PRs by project
    
    Validates: Requirements 5.9, 10.1 - P95 response time < 500ms
    """
    project_id = test_data["project_id"]
    times = []
    
    # Run query 100 times to get statistical data
    for _ in range(100):
        async def query():
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(PullRequest).where(PullRequest.project_id == project_id)
                )
                return result.scalars().all()
        
        query_time = await measure_query_time(query)
        times.append(query_time)
    
    # Calculate statistics
    p50 = calculate_percentile(times, 50)
    p95 = calculate_percentile(times, 95)
    p99 = calculate_percentile(times, 99)
    avg = statistics.mean(times)
    
    logger.info("\nQuery PRs by Project Performance:")
    logger.info("  Average: {avg:.2f}ms")
    logger.info("  P50: {p50:.2f}ms")
    logger.info("  P95: {p95:.2f}ms")
    logger.info("  P99: {p99:.2f}ms")
    
    # Requirement: P95 < 500ms
    assert p95 < 500, f"P95 response time {p95:.2f}ms exceeds 500ms threshold"


@pytest.mark.asyncio
async def test_query_prs_by_status_performance(test_data):
    """
    Test performance of querying PRs by project and status (composite index)
    
    Validates: Requirements 5.9, 10.1, 10.5 - P95 < 500ms with index optimization
    """
    project_id = test_data["project_id"]
    times = []
    
    for _ in range(100):
        async def query():
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(PullRequest)
                    .where(PullRequest.project_id == project_id)
                    .where(PullRequest.status == "pending")
                )
                return result.scalars().all()
        
        query_time = await measure_query_time(query)
        times.append(query_time)
    
    p50 = calculate_percentile(times, 50)
    p95 = calculate_percentile(times, 95)
    avg = statistics.mean(times)
    
    logger.info("\nQuery PRs by Status Performance:")
    logger.info("  Average: {avg:.2f}ms")
    logger.info("  P50: {p50:.2f}ms")
    logger.info("  P95: {p95:.2f}ms")
    
    assert p95 < 500, f"P95 response time {p95:.2f}ms exceeds 500ms threshold"


@pytest.mark.asyncio
async def test_query_reviews_with_comments_performance(test_data):
    """
    Test performance of querying reviews with comments (JOIN query)
    
    Validates: Requirements 5.9, 10.1, 10.5 - P95 < 500ms with foreign key indexes
    """
    pr_ids = test_data["pr_ids"][:10]
    times = []
    
    for _ in range(100):
        async def query():
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(CodeReview, ReviewComment)
                    .join(ReviewComment, ReviewComment.review_id == CodeReview.id)
                    .where(CodeReview.pull_request_id.in_(pr_ids))
                )
                return result.all()
        
        query_time = await measure_query_time(query)
        times.append(query_time)
    
    p50 = calculate_percentile(times, 50)
    p95 = calculate_percentile(times, 95)
    avg = statistics.mean(times)
    
    logger.info("\nQuery Reviews with Comments Performance:")
    logger.info("  Average: {avg:.2f}ms")
    logger.info("  P50: {p50:.2f}ms")
    logger.info("  P95: {p95:.2f}ms")
    
    assert p95 < 500, f"P95 response time {p95:.2f}ms exceeds 500ms threshold"


@pytest.mark.asyncio
async def test_query_comments_by_severity_performance(test_data):
    """
    Test performance of querying comments by severity (composite index)
    
    Validates: Requirements 5.9, 10.1, 10.5 - P95 < 500ms with composite index
    """
    times = []
    
    for _ in range(100):
        async def query():
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ReviewComment)
                    .where(ReviewComment.severity.in_(["high", "critical"]))
                )
                return result.scalars().all()
        
        query_time = await measure_query_time(query)
        times.append(query_time)
    
    p50 = calculate_percentile(times, 50)
    p95 = calculate_percentile(times, 95)
    avg = statistics.mean(times)
    
    logger.info("\nQuery Comments by Severity Performance:")
    logger.info("  Average: {avg:.2f}ms")
    logger.info("  P50: {p50:.2f}ms")
    logger.info("  P95: {p95:.2f}ms")
    
    assert p95 < 500, f"P95 response time {p95:.2f}ms exceeds 500ms threshold"


@pytest.mark.asyncio
async def test_concurrent_query_performance(test_data):
    """
    Test performance under concurrent load
    
    Validates: Requirements 5.9, 10.1, 10.6 - P95 < 500ms with connection pooling
    """
    project_id = test_data["project_id"]
    times = []
    
    async def single_query():
        start = time.perf_counter()
        async with AsyncSessionLocal() as session:
            await session.execute(
                select(PullRequest).where(PullRequest.project_id == project_id)
            )
        end = time.perf_counter()
        return (end - start) * 1000
    
    # Run 50 concurrent queries, repeat 10 times
    for _ in range(10):
        tasks = [single_query() for _ in range(50)]
        batch_times = await asyncio.gather(*tasks)
        times.extend(batch_times)
    
    p50 = calculate_percentile(times, 50)
    p95 = calculate_percentile(times, 95)
    p99 = calculate_percentile(times, 99)
    avg = statistics.mean(times)
    
    logger.info("\nConcurrent Query Performance (50 concurrent queries):")
    logger.info("  Average: {avg:.2f}ms")
    logger.info("  P50: {p50:.2f}ms")
    logger.info("  P95: {p95:.2f}ms")
    logger.info("  P99: {p99:.2f}ms")
    
    assert p95 < 500, f"P95 response time {p95:.2f}ms exceeds 500ms threshold under load"


@pytest.mark.asyncio
async def test_complex_query_performance(test_data):
    """
    Test performance of complex multi-table query
    
    Validates: Requirements 5.9, 10.1, 10.5 - P95 < 500ms for complex queries
    """
    project_id = test_data["project_id"]
    times = []
    
    for _ in range(100):
        async def query():
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Project, PullRequest, CodeReview, ReviewComment)
                    .join(PullRequest, PullRequest.project_id == Project.id)
                    .join(CodeReview, CodeReview.pull_request_id == PullRequest.id)
                    .join(ReviewComment, ReviewComment.review_id == CodeReview.id)
                    .where(Project.id == project_id)
                    .where(ReviewComment.severity == "high")
                )
                return result.all()
        
        query_time = await measure_query_time(query)
        times.append(query_time)
    
    p50 = calculate_percentile(times, 50)
    p95 = calculate_percentile(times, 95)
    avg = statistics.mean(times)
    
    logger.info("\nComplex Multi-Table Query Performance:")
    logger.info("  Average: {avg:.2f}ms")
    logger.info("  P50: {p50:.2f}ms")
    logger.info("  P95: {p95:.2f}ms")
    
    assert p95 < 500, f"P95 response time {p95:.2f}ms exceeds 500ms threshold"


@pytest.mark.asyncio
async def test_connection_pool_under_load(test_data):
    """
    Test connection pool performance under heavy load
    
    Validates: Requirement 10.6 - Connection pooling with pool size 20
    """
    project_id = test_data["project_id"]
    
    async def query_task():
        async with AsyncSessionLocal() as session:
            await session.execute(
                select(PullRequest).where(PullRequest.project_id == project_id)
            )
    
    # Test with 100 concurrent connections (exceeds pool size)
    start = time.perf_counter()
    tasks = [query_task() for _ in range(100)]
    await asyncio.gather(*tasks)
    end = time.perf_counter()
    
    total_time = (end - start) * 1000
    avg_time_per_query = total_time / 100
    
    logger.info("\nConnection Pool Under Load (100 concurrent queries):")
    logger.info("  Total Time: {total_time:.2f}ms")
    logger.info("  Average per Query: {avg_time_per_query:.2f}ms")
    
    # With proper pooling, average should still be reasonable
    assert avg_time_per_query < 100, f"Average query time {avg_time_per_query:.2f}ms too high under load"


@pytest.mark.asyncio
async def test_index_effectiveness():
    """
    Test that indexes are being used effectively
    
    Validates: Requirement 10.5 - Database query optimization with proper indexes
    """
    async with AsyncSessionLocal() as session:
        # Test that index is used for project_id query
        result = await session.execute(
            text("""
                EXPLAIN (FORMAT JSON)
                SELECT * FROM pull_requests 
                WHERE project_id = '00000000-0000-0000-0000-000000000001'::uuid
            """)
        )
        plan = result.scalar()
        
        # Check if index scan is used (not sequential scan)
        plan_str = str(plan)
        logger.info("\nIndex Usage Check:")
        logger.info("  Query Plan: {plan_str[:200]}...")
        
        # Index scan or bitmap index scan indicates index is being used
        assert "Index Scan" in plan_str or "Bitmap Index Scan" in plan_str, \
            "Query should use index scan, not sequential scan"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
