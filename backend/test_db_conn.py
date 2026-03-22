import logging

logger = logging.getLogger(__name__)

import asyncio
import os

import asyncpg


async def test_conn():
    db_password = os.getenv("POSTGRES_PASSWORD")
    if not db_password:
        raise RuntimeError("POSTGRES_PASSWORD is required for test_db_conn")
    url = f"postgresql://postgres:{db_password}@127.0.0.1:5433/postgres"
    logger.info("Testing raw asyncpg connection")
    try:
        conn = await asyncpg.connect(url)
        logger.info("Connected!")
        val = await conn.fetchval("SELECT 1")
        logger.info("Connection test result: %s", val)
        await conn.close()
    except Exception:
        logger.exception("Database connection test failed")


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_conn())
