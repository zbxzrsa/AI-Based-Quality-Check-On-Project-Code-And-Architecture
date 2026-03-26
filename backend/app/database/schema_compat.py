"""
Startup-time schema compatibility helpers for legacy local databases.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.database.postgresql import engine

logger = logging.getLogger(__name__)

CURRENT_ROLE_VALUES = ("user", "admin")
ALEMBIC_HEAD = "011_add_ai_settings_to_users"


async def reconcile_legacy_auth_schema() -> list[str]:
    """
    Normalize legacy auth schema/data so the current application can run
    against older local databases without manual intervention.
    """
    actions: list[str] = []

    async with engine.begin() as conn:
        users_exists = await conn.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'users'
                )
                """
            )
        )
        if not users_exists:
            return actions

        enum_labels = [
            row[0]
            for row in (
                await conn.execute(
                    text(
                        """
                        SELECT enumlabel
                        FROM pg_enum e
                        JOIN pg_type t ON e.enumtypid = t.oid
                        WHERE t.typname = 'user_role'
                        ORDER BY enumsortorder
                        """
                    )
                )
            ).fetchall()
        ]

        if enum_labels:
            for role in CURRENT_ROLE_VALUES:
                await conn.execute(
                    text(f"ALTER TYPE user_role ADD VALUE IF NOT EXISTS '{role}'")
                )
            actions.append("ensured user_role enum contains user/admin")

            await conn.execute(
                text(
                    """
                    UPDATE users
                    SET role = 'user'::user_role
                    WHERE role::text NOT IN ('user', 'admin')
                    """
                )
            )
            actions.append("normalized unsupported user roles to user")

            await conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ALTER COLUMN role SET DEFAULT 'user'::user_role
                    """
                )
            )
            actions.append("set users.role default to user")

        await _ensure_user_columns(conn, actions)
        await _ensure_pr_status_enum(conn, actions)

        modern_users = await _has_columns(
            conn,
            "users",
            ("role", "github_token", "github_username", "ai_settings"),
        )
        modern_projects = await _has_columns(
            conn,
            "projects",
            ("github_connection_type", "github_ssh_key_id", "github_cli_token"),
        )
        await _ensure_pull_request_columns(conn, actions)

        if modern_users and modern_projects:
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num varchar(32) NOT NULL PRIMARY KEY
                    )
                    """
                )
            )
            version_count = await conn.scalar(text("SELECT COUNT(*) FROM alembic_version"))
            if not version_count:
                await conn.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
                    {"version_num": ALEMBIC_HEAD},
                )
                actions.append(f"stamped alembic version to {ALEMBIC_HEAD}")

    for action in actions:
        logger.info("Schema compatibility: %s", action)

    return actions


async def _has_columns(conn, table_name: str, required_columns: tuple[str, ...]) -> bool:
    rows = (
        await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table_name
                """
            ),
            {"table_name": table_name},
        )
    ).fetchall()
    existing = {row[0] for row in rows}
    return all(column in existing for column in required_columns)


async def _ensure_user_columns(conn, actions: list[str]) -> None:
    rows = (
        await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'users'
                """
            )
        )
    ).fetchall()
    existing = {row[0] for row in rows}

    if "ai_settings" not in existing:
        await conn.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN ai_settings JSONB NOT NULL DEFAULT '{}'::jsonb
                """
            )
        )
        actions.append("added users.ai_settings with default empty JSON object")


async def _ensure_pr_status_enum(conn, actions: list[str]) -> None:
    enum_labels = [
        row[0]
        for row in (
            await conn.execute(
                text(
                    """
                    SELECT enumlabel
                    FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'pr_status'
                    ORDER BY enumsortorder
                    """
                )
            )
        ).fetchall()
    ]

    if not enum_labels:
        return

    if "merged" not in enum_labels:
        await conn.execute(text("ALTER TYPE pr_status ADD VALUE IF NOT EXISTS 'merged'"))
        actions.append("ensured pr_status enum contains merged")


async def _ensure_pull_request_columns(conn, actions: list[str]) -> None:
    rows = (
        await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'pull_requests'
                """
            )
        )
    ).fetchall()
    existing = {row[0] for row in rows}

    if not existing:
        return

    if "updated_at" not in existing:
        await conn.execute(
            text(
                """
                ALTER TABLE pull_requests
                ADD COLUMN updated_at TIMESTAMP NULL
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE pull_requests
                SET updated_at = created_at
                WHERE updated_at IS NULL
                """
            )
        )
        actions.append("added pull_requests.updated_at and backfilled it from created_at")

    if "merged_at" not in existing:
        await conn.execute(
            text(
                """
                ALTER TABLE pull_requests
                ADD COLUMN merged_at TIMESTAMP NULL
                """
            )
        )
        actions.append("added pull_requests.merged_at")

    if "closed_at" not in existing:
        await conn.execute(
            text(
                """
                ALTER TABLE pull_requests
                ADD COLUMN closed_at TIMESTAMP NULL
                """
            )
        )
        actions.append("added pull_requests.closed_at")
