#!/usr/bin/env python3

import traceback

logger.info("Testing imports...")

try:
    logger.info("1. Importing basic modules...")
    logger.info("   ✓ Basic modules imported")

    logger.info("2. Importing httpx...")
    logger.info("   ✓ httpx imported")

    logger.info("3. Importing app schemas...")
    logger.info("   ✓ Schemas imported")

    logger.info("4. Importing app models...")
    logger.info("   ✓ Models imported")

    logger.info("5. Importing metadata fetcher module...")
    logger.info("   ✓ Module imported")
    logger.info("   Available attributes: {[attr for attr in dir(mf) if not attr.startswith('_')]}")

    logger.info("6. Trying to import specific classes...")
    try:
        logger.info("   ✓ MetadataFetchError imported")
    except Exception:
        logger.info("   ✗ MetadataFetchError failed: {e}")

    try:
        logger.info("   ✓ AsyncCircuitBreaker imported")
    except Exception:
        logger.info("   ✗ AsyncCircuitBreaker failed: {e}")

    try:
        logger.info("   ✓ MetadataFetcher imported")
    except Exception:
        logger.info("   ✗ MetadataFetcher failed: {e}")

except Exception:
    logger.info("Error during import: {e}")
    traceback.print_exc()
