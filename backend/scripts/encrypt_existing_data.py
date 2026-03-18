#!/usr/bin/env python3
"""
Encrypt existing plaintext data in the database.

This script encrypts sensitive fields that were previously stored as plaintext.
Run this after applying the encryption migration.

Implements Requirement 8.4: Encrypt all sensitive data at rest using AES-256 encryption

Usage:
    python backend/scripts/encrypt_existing_data.py [--dry-run] [--table TABLE] [--field FIELD]
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgresql import get_async_session_maker
from app.models import Project
from app.services.encryption_service import get_encryption_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def encrypt_project_webhook_secrets(session: AsyncSession, dry_run: bool = False) -> int:
    """
    Encrypt github_webhook_secret fields in projects table.

    Args:
        session: Database session
        dry_run: If True, only count records without encrypting

    Returns:
        Number of records encrypted
    """
    encryption_service = get_encryption_service()

    # Find projects with non-null webhook secrets
    result = await session.execute(select(Project).where(Project.github_webhook_secret.isnot(None)))
    projects = result.scalars().all()

    count = 0
    for project in projects:
        webhook_secret = project.github_webhook_secret

        # Skip if already encrypted (basic check - encrypted data is base64)
        if webhook_secret and len(webhook_secret) > 50 and "=" in webhook_secret[-5:]:
            logger.debug(f"Project {project.id} webhook secret appears already encrypted, skipping")
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would encrypt webhook secret for project: {project.name} ({project.id})")
            count += 1
        else:
            try:
                encrypted = encryption_service.encrypt(webhook_secret)
                project.github_webhook_secret = encrypted
                count += 1
                logger.info(f"Encrypted webhook secret for project: {project.name} ({project.id})")
            except Exception as e:
                logger.error(f"Failed to encrypt webhook secret for project {project.id}: {e}")

    if not dry_run and count > 0:
        await session.commit()

        # Update encryption metadata
        await session.execute(
            text("""
                UPDATE encryption_metadata
                SET is_encrypted = true,
                    encrypted_at = NOW(),
                    encrypted_by = 'encrypt_existing_data.py'
                WHERE table_name = 'projects'
                AND column_name = 'github_webhook_secret'
            """)
        )
        await session.commit()

    return count


async def get_encryption_status(session: AsyncSession) -> dict:
    """
    Get encryption status for all registered sensitive fields.

    Args:
        session: Database session

    Returns:
        Dictionary with encryption status
    """
    result = await session.execute(
        text("""
            SELECT table_name, column_name, is_encrypted, encryption_algorithm, encrypted_at
            FROM encryption_metadata
            ORDER BY table_name, column_name
        """)
    )

    status = {}
    for row in result:
        table = row[0]
        if table not in status:
            status[table] = []
        status[table].append(
            {
                "column": row[1],
                "encrypted": row[2],
                "algorithm": row[3],
                "encrypted_at": row[4],
            }
        )

    return status


async def main():
    """Main encryption script."""
    import argparse

    parser = argparse.ArgumentParser(description="Encrypt existing plaintext data in the database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be encrypted without making changes",
    )
    parser.add_argument(
        "--table",
        help="Only encrypt specific table (e.g., 'projects')",
    )
    parser.add_argument(
        "--field",
        help="Only encrypt specific field (e.g., 'github_webhook_secret')",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show encryption status and exit",
    )

    args = parser.parse_args()

    # Get database session
    session_maker = get_async_session_maker()

    async with session_maker() as session:
        # Show encryption status if requested
        if args.status:
            logger.info("📊 Encryption Status:")
            status = await get_encryption_status(session)

            for table, fields in status.items():
                logger.info(f"\n  Table: {table}")
                for field in fields:
                    encrypted_icon = "✅" if field["encrypted"] else "❌"
                    logger.info(
                        f"    {encrypted_icon} {field['column']}: "
                        f"{field['algorithm']} "
                        f"({'encrypted' if field['encrypted'] else 'not encrypted'})"
                    )
            return 0

        # Encrypt data
        logger.info("🔐 Starting data encryption...")
        if args.dry_run:
            logger.info("⚠️  DRY RUN MODE - No changes will be made")

        total_encrypted = 0

        # Encrypt project webhook secrets
        if not args.table or args.table == "projects":
            if not args.field or args.field == "github_webhook_secret":
                logger.info("\n📦 Encrypting project webhook secrets...")
                count = await encrypt_project_webhook_secrets(session, dry_run=args.dry_run)
                logger.info(f"   Encrypted {count} webhook secrets")
                total_encrypted += count

        # Add more encryption functions here for other tables/fields

        logger.info(f"\n✅ Encryption complete! Total records encrypted: {total_encrypted}")

        if args.dry_run:
            logger.info("⚠️  This was a dry run. Run without --dry-run to apply changes.")

        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
