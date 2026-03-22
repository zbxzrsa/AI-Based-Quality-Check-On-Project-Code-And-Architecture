import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Create default admin user for the AI Code Review Platform.

This script creates an admin user with email and password.
Run this after database initialization to create the first admin account.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid

from sqlalchemy import select

from app.database.postgresql import get_db, init_db
from app.models import User, UserRole
from app.utils.password import hash_password


async def create_admin_user(email: str = None, password: str = None, full_name: str = "System Administrator"):
    """
    Create a default admin user.

    Args:
        email: Admin email address (or get from ADMIN_EMAIL env var)
        password: Admin password (must get from ADMIN_PASSWORD env var for security)
        full_name: Admin full name
    """
    # Get credentials from environment variables for security
    email = email or os.environ.get("ADMIN_EMAIL", "admin@example.com")
    password = password or os.environ.get("ADMIN_PASSWORD")

    if not password:
        logger.error("Password is required. Set ADMIN_PASSWORD environment variable or pass as argument.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("AI Code Review Platform - Admin User Creation")
    logger.info("=" * 60)
    logger.info()

    # Initialize database
    logger.info("Initializing database connection...")
    await init_db()

    async for db in get_db():
        try:
            # Check if admin already exists
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                logger.info(f"❌ Admin user with email '{email}' already exists!")
                logger.info(f"   User ID: {existing_user.id}")
                logger.info(f"   Role: {existing_user.role.value}")
                logger.info(f"   Created: {existing_user.created_at}")
                logger.info()
                logger.info("If you need to reset the password, use the password reset feature.")
                return False

            # Hash password
            logger.info(f"Creating admin user: {email}")
            password_hash = hash_password(password)

            # Create admin user
            admin_user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash=password_hash,
                role=UserRole.USER,
                full_name=full_name,
                is_active=True,
            )

            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

            logger.info()
            logger.info("✅ Admin user created successfully!")
            logger.info()
            logger.info("=" * 60)
            logger.info("LOGIN CREDENTIALS")
            logger.info("=" * 60)
            logger.info(f"Email:    {email}")
            logger.info("Password: (hidden)")
            logger.info(f"Role:     {admin_user.role.value}")
            logger.info(f"User ID:  {admin_user.id}")
            logger.info("=" * 60)
            logger.info()
            logger.info("⚠️  IMPORTANT SECURITY NOTICE:")
            logger.info("   1. Change this password immediately after first login")
            logger.info("   2. Do not share these credentials")
            logger.info("   3. Enable MFA if available")
            logger.info("   4. This password should only be used in development")
            logger.info()
            logger.info("Login at: http://localhost:3000/login")
            logger.info()

            return True

        except Exception as e:
            logger.info(f"❌ Error creating admin user: {e}")
            await db.rollback()
            return False


async def main():
    """Main function to create admin user."""
    import argparse

    parser = argparse.ArgumentParser(description="Create admin user for AI Code Review Platform")
    parser.add_argument("--email", default="admin@example.com", help="Admin email address (default: admin@example.com)")
    parser.add_argument(
        "--password",
        default=None,
        help="Admin password (if omitted, uses ADMIN_PASSWORD env var)",
    )
    parser.add_argument(
        "--name", default="System Administrator", help="Admin full name (default: System Administrator)"
    )

    args = parser.parse_args()

    success = await create_admin_user(email=args.email, password=args.password, full_name=args.name)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
