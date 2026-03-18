import logging

logger = logging.getLogger(__name__)

import asyncio

import asyncpg


async def test_conn():
    url = "postgresql://postgres@127.0.0.1:5433/postgres"
    logger.info("Testing raw asyncpg connection to {url}")
    try:
        conn = await asyncpg.connect(url)
        logger.info("Connected!")
        await conn.fetchval("SELECT 1")
        logger.info("Result: {val}")
        await conn.close()
    except Exception:
        logger.info("Error: {e}")


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_conn())
