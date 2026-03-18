"""
Cleanup Test Data Script

This script removes test data from the staging database to ensure
clean state for end-to-end tests.

Usage:
    python backend/scripts/cleanup_test_data.py
"""

import logging

logger = logging.getLogger(__name__)

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select

from app.database.postgresql import AsyncSessionLocal
from app.models import CodeEntity, Project, PullRequest, User
from app.services.graph_builder.service import GraphBuilderService


async def cleanup_test_projects():
    """Remove test projects and related data"""
    async with AsyncSessionLocal() as db:
        # Find test projects (those with 'test' or 'e2e' in name/url)
        result = await db.execute(
            select(Project).where(
                (Project.name.ilike("%test%"))
                | (Project.name.ilike("%e2e%"))
                | (Project.github_repo_url.ilike("%test%"))
                | (Project.github_repo_url.ilike("%e2e%"))
            )
        )
        test_projects = result.scalars().all()

        if not test_projects:
            logger.info("No test projects found to clean up")
            return

        logger.info("Found {len(test_projects)} test projects to clean up")

        for project in test_projects:
            logger.info("  Cleaning project: {project.name} (ID: {project.id})")

            # Delete code entities
            await db.execute(delete(CodeEntity).where(CodeEntity.project_id == project.id))

            # Delete pull requests
            await db.execute(delete(PullRequest).where(PullRequest.project_id == project.id))

            # Delete from Neo4j
            try:
                graph_service = GraphBuilderService()
                await graph_service.delete_project_graph(project.id)
                await graph_service.close()
                logger.info("    ✓ Deleted Neo4j graph data")
            except Exception:
                logger.info("    ⚠ Warning: Could not delete Neo4j data: {e}")

            # Delete project
            await db.delete(project)
            logger.info("    ✓ Deleted project and related data")

        await db.commit()
        logger.info("\n✓ Cleaned up {len(test_projects)} test projects")


async def cleanup_test_users():
    """Remove test users"""
    async with AsyncSessionLocal() as db:
        # Find test users
        result = await db.execute(
            select(User).where(
                (User.email.ilike("%test%"))
                | (User.email.ilike("%e2e%"))
                | (User.username.ilike("%test%"))
                | (User.username.ilike("%e2e%"))
            )
        )
        test_users = result.scalars().all()

        if not test_users:
            logger.info("No test users found to clean up")
            return

        logger.info("Found {len(test_users)} test users to clean up")

        for user in test_users:
            logger.info("  Cleaning user: {user.email} (ID: {user.id})")
            await db.delete(user)

        await db.commit()
        logger.info("✓ Cleaned up {len(test_users)} test users")


async def cleanup_orphaned_data():
    """Remove orphaned data (entities without projects, etc.)"""
    async with AsyncSessionLocal() as db:
        # Find orphaned code entities
        result = await db.execute(select(CodeEntity).where(~CodeEntity.project_id.in_(select(Project.id))))
        orphaned_entities = result.scalars().all()

        if orphaned_entities:
            logger.info("Found {len(orphaned_entities)} orphaned code entities")
            for entity in orphaned_entities:
                await db.delete(entity)
            await db.commit()
            logger.info("✓ Cleaned up {len(orphaned_entities)} orphaned entities")

        # Find orphaned pull requests
        result = await db.execute(select(PullRequest).where(~PullRequest.project_id.in_(select(Project.id))))
        orphaned_prs = result.scalars().all()

        if orphaned_prs:
            logger.info("Found {len(orphaned_prs)} orphaned pull requests")
            for pr in orphaned_prs:
                await db.delete(pr)
            await db.commit()
            logger.info("✓ Cleaned up {len(orphaned_prs)} orphaned PRs")


async def main():
    """Main cleanup function"""
    logger.info("=" * 60)
    logger.info("Cleaning Up Test Data")
    logger.info("=" * 60)
    logger.info()

    try:
        # Cleanup test projects
        await cleanup_test_projects()
        logger.info()

        # Cleanup test users
        await cleanup_test_users()
        logger.info()

        # Cleanup orphaned data
        await cleanup_orphaned_data()
        logger.info()

        logger.info("=" * 60)
        logger.info("✓ Cleanup Complete")
        logger.info("=" * 60)

    except Exception:
        logger.info("\n✗ Error during cleanup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
