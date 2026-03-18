"""
Core Module - Central Exports

This module provides centralized exports for the core module.
Import from here instead of importing from individual files.
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.core.utils import format_error_message, normalize_string, safe_get_nested_value

__all__ = [
    "settings",
    "get_logger",
    "safe_get_nested_value",
    "normalize_string",
    "format_error_message",
]
