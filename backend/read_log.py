import logging

logger = logging.getLogger(__name__)

import sys


def read_log(filename):
    try:
        with open(filename, encoding="utf-16") as f:
            content = f.read()
            logger.info(content)
    except Exception:
        logger.info("Error reading with utf-16: {e}")
        try:
            with open(filename, encoding="utf-8") as f:
                content = f.read()
                logger.info(content)
        except Exception:
            logger.info("Error reading with utf-8: {e2}")


if __name__ == "__main__":
    read_log(sys.argv[1])
