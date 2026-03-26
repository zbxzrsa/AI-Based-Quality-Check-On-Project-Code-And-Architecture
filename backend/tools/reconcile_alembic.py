#!/usr/bin/env python3
"""
Reconcile Alembic version history with an existing database.

Use this when a legacy database already has tables but `alembic_version` is
empty or inconsistent. It stamps (or normalizes) to the current Alembic head
without replaying all historical migrations.
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import psycopg


ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = ROOT / "alembic" / "versions"


def _extract_revisions() -> Dict[str, Optional[Iterable[str]]]:
    rev_pat = re.compile(r"^revision\s*=\s*(.+)$", re.MULTILINE)
    down_pat = re.compile(r"^down_revision\s*=\s*(.+)$", re.MULTILINE)

    revisions: Dict[str, Optional[Iterable[str]]] = {}
    for file in sorted(VERSIONS_DIR.glob("*.py")):
        text = file.read_text(encoding="utf-8")
        rev_match = rev_pat.search(text)
        down_match = down_pat.search(text)
        if not rev_match:
            continue

        revision = ast.literal_eval(rev_match.group(1).strip())
        down_raw = ast.literal_eval(down_match.group(1).strip()) if down_match else None

        if down_raw is None:
            revisions[revision] = None
        elif isinstance(down_raw, (tuple, list, set)):
            revisions[revision] = [str(v) for v in down_raw]
        else:
            revisions[revision] = [str(down_raw)]
    return revisions


def _find_heads(revisions: Dict[str, Optional[Iterable[str]]]) -> List[str]:
    referenced: Set[str] = set()
    for downs in revisions.values():
        if not downs:
            continue
        referenced.update(downs)
    heads = [rev for rev in revisions.keys() if rev not in referenced]
    return sorted(heads)


def _default_db_url() -> str:
    import os

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url.replace("+psycopg", "")

    pg_user = os.getenv("POSTGRES_USER", "postgres")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_db = os.getenv("POSTGRES_DB", "ai_code_review")
    return f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"


def _table_exists(cur: psycopg.Cursor, table_name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.tables
          WHERE table_schema='public' AND table_name=%s
        )
        """,
        (table_name,),
    )
    return bool(cur.fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=_default_db_url())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    revisions = _extract_revisions()
    heads = _find_heads(revisions)
    if len(heads) != 1:
        print(f"[ERROR] Expected 1 Alembic head, found {len(heads)}: {heads}")
        return 2
    head = heads[0]
    known_revisions = set(revisions.keys())
    print(f"[INFO] Alembic head: {head}")

    with psycopg.connect(args.db_url) as conn:
        with conn.cursor() as cur:
            if not _table_exists(cur, "alembic_version"):
                print("[INFO] alembic_version table does not exist; creating")
                if not args.dry_run:
                    cur.execute(
                        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                    )

            cur.execute("SELECT version_num FROM alembic_version")
            rows = [row[0] for row in cur.fetchall()]
            print(f"[INFO] Current alembic_version rows: {rows}")

            if len(rows) == 1 and rows[0] == head:
                print("[OK] Migration history already aligned")
                return 0

            if rows and not args.force:
                invalid = [r for r in rows if r not in known_revisions]
                if invalid:
                    print(f"[ERROR] Found unknown revisions: {invalid}. Re-run with --force after backup.")
                    return 3
                if len(rows) == 1:
                    print(f"[WARN] DB revision is {rows[0]}, head is {head}. Use --force to normalize.")
                    return 4
                print("[WARN] Multiple alembic_version rows found. Use --force to normalize.")
                return 5

            if not rows and not _table_exists(cur, "users"):
                print("[WARN] Empty DB detected (users table missing). Run `alembic upgrade head` instead of stamp.")
                return 6

            print(f"[ACTION] Setting alembic_version to {head}")
            if not args.dry_run:
                cur.execute("DELETE FROM alembic_version")
                cur.execute(
                    "INSERT INTO alembic_version(version_num) VALUES (%s)",
                    (head,),
                )
                conn.commit()
            print("[OK] Alembic history reconciled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
