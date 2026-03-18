"""
Query performance analysis script using EXPLAIN ANALYZE

This script tests common query patterns and analyzes their performance
using PostgreSQL's EXPLAIN ANALYZE to verify index effectiveness.

Requirements: 10.5 - Database query optimization with proper indexes
"""

import logging

logger = logging.getLogger(__name__)

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.database.postgresql import AsyncSessionLocal


async def analyze_query(session, query_name: str, query: str):
    """Execute EXPLAIN ANALYZE on a query and print results"""
    logger.info("\n{'='*80}")
    logger.info("Query: {query_name}")
    logger.info("{'='*80}")
    logger.info("SQL: {query}\n")

    try:
        result = await session.execute(text(f"EXPLAIN ANALYZE {query}"))
        logger.info("Execution Plan:")
        for _row in result:
            logger.info("  {row[0]}")
    except Exception:
        logger.info("Error: {e}")


async def main():
    """Run query performance analysis"""
    async with AsyncSessionLocal() as session:
        logger.info("Database Query Performance Analysis")
        logger.info("=" * 80)

        # Query 1: Get PRs by project and status (uses composite index)
        await analyze_query(
            session,
            "Get PRs by project and status",
            """
            SELECT * FROM pull_requests
            WHERE project_id = '00000000-0000-0000-0000-000000000001'::uuid
            AND status = 'pending'
            """,
        )

        # Query 2: Get recent PRs for a project (uses composite index)
        await analyze_query(
            session,
            "Get recent PRs for a project",
            """
            SELECT * FROM pull_requests
            WHERE project_id = '00000000-0000-0000-0000-000000000001'::uuid
            ORDER BY created_at DESC
            LIMIT 10
            """,
        )

        # Query 3: Get reviews with comments (uses foreign key indexes)
        await analyze_query(
            session,
            "Get reviews with comments",
            """
            SELECT cr.*, rc.*
            FROM code_reviews cr
            LEFT JOIN review_comments rc ON rc.review_id = cr.id
            WHERE cr.pull_request_id = '00000000-0000-0000-0000-000000000002'::uuid
            """,
        )

        # Query 4: Get high severity comments for a review (uses composite index)
        await analyze_query(
            session,
            "Get high severity comments",
            """
            SELECT * FROM review_comments
            WHERE review_id = '00000000-0000-0000-0000-000000000003'::uuid
            AND severity IN ('high', 'critical')
            """,
        )

        # Query 5: Get architecture violations by type (uses type index)
        await analyze_query(
            session,
            "Get circular dependency violations",
            """
            SELECT * FROM architecture_violations
            WHERE type = 'circular_dependency'
            AND severity IN ('high', 'critical')
            """,
        )

        # Query 6: Get audit trail for user (uses composite index)
        await analyze_query(
            session,
            "Get user audit trail",
            """
            SELECT * FROM audit_logs
            WHERE user_id = '00000000-0000-0000-0000-000000000004'::uuid
            ORDER BY timestamp DESC
            LIMIT 50
            """,
        )

        # Query 7: Get audit logs for entity (uses composite index)
        await analyze_query(
            session,
            "Get entity audit trail",
            """
            SELECT * FROM audit_logs
            WHERE entity_type = 'project'
            AND entity_id = '00000000-0000-0000-0000-000000000001'::uuid
            ORDER BY timestamp DESC
            """,
        )

        # Query 8: Get active projects for owner (uses composite index)
        await analyze_query(
            session,
            "Get active projects for owner",
            """
            SELECT * FROM projects
            WHERE owner_id = '00000000-0000-0000-0000-000000000004'::uuid
            AND is_active = true
            """,
        )

        # Query 9: Get current baseline for project (uses composite index)
        await analyze_query(
            session,
            "Get current architectural baseline",
            """
            SELECT * FROM architectural_baselines
            WHERE project_id = '00000000-0000-0000-0000-000000000001'::uuid
            AND is_current = true
            """,
        )

        # Query 10: Get active sessions for user (uses composite index)
        await analyze_query(
            session,
            "Get active user sessions",
            """
            SELECT * FROM sessions
            WHERE user_id = '00000000-0000-0000-0000-000000000004'::uuid
            AND is_active = true
            """,
        )

        # Query 11: Get expired sessions for cleanup (uses expires_at index)
        await analyze_query(
            session,
            "Get expired sessions",
            """
            SELECT * FROM sessions
            WHERE expires_at < NOW()
            AND is_active = true
            """,
        )

        # Query 12: Get code entities by project and type (uses composite index)
        await analyze_query(
            session,
            "Get functions in project",
            """
            SELECT * FROM code_entities
            WHERE project_id = '00000000-0000-0000-0000-000000000001'::uuid
            AND entity_type = 'function'
            """,
        )

        # Query 13: Get code entities by file (uses file_path index)
        await analyze_query(
            session,
            "Get entities in file",
            """
            SELECT * FROM code_entities
            WHERE file_path = 'src/main.py'
            """,
        )

        # Query 14: Get libraries by project context (uses composite index)
        await analyze_query(
            session,
            "Get backend libraries",
            """
            SELECT * FROM libraries
            WHERE project_id = 'project-123'
            AND project_context = 'backend'
            """,
        )

        # Query 15: Get comments by file path (uses file_path index)
        await analyze_query(
            session,
            "Get comments for file",
            """
            SELECT * FROM review_comments
            WHERE file_path = 'src/services/analyzer.py'
            """,
        )

        logger.info("\n{'='*80}")
        logger.info("Analysis Complete")
        logger.info("{'='*80}")
        logger.info("\nLook for:")
        logger.info("  - 'Index Scan' or 'Index Only Scan' (good - using indexes)")
        logger.info("  - 'Seq Scan' (bad - full table scan, missing index)")
        logger.info("  - Low execution times (< 10ms for simple queries)")
        logger.info("  - 'Bitmap Index Scan' (acceptable for multi-column queries)")


if __name__ == "__main__":
    asyncio.run(main())
