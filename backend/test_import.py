#!/usr/bin/env python3
"""Basic import smoke test for backend modules."""

import logging
import traceback

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    logger.info("Testing backend imports...")
    try:
        import httpx  # noqa: F401
        from app import models  # noqa: F401
        from app import schemas  # noqa: F401
        from app.services import github_client as metadata_fetcher  # noqa: F401

        logger.info("Import smoke test passed")
        return 0
    except Exception as exc:
        logger.error("Import smoke test failed: %s", exc)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
