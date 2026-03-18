"""
Logging utilities for the application
"""

import logging


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name or __name__)
