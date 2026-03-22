"""
Serialization utilities for Redis caching

WARNING: Avoid pickle for untrusted data due to security risks (arbitrary code execution).
Use JSON-based serialization for all user-provided or external data.
"""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class EnhancedJSONEncoder(json.JSONEncoder):
    """
    Enhanced JSON encoder that handles additional Python types
    """

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, bytes):
            return obj.decode("utf-8")
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


def serialize_json(data: Any) -> str:
    """
    Serialize data to JSON string
    Handles datetime, Decimal, UUID, and custom objects

    Preferred method for all serialization tasks.
    """
    try:
        return json.dumps(data, cls=EnhancedJSONEncoder)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Cannot serialize data to JSON: {e}") from e


def deserialize_json(json_str: str) -> Any:
    """
    Deserialize JSON string to Python object

    Safe method that only deserializes valid JSON.
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Cannot deserialize JSON: {e}") from e


def serialize_pickle(_data: Any) -> bytes:
    """
    Pickle serialization is intentionally disabled.

    Pickle can execute arbitrary code during deserialization, which is not safe
    for any data that might be influenced by users or external systems.
    """
    raise ValueError("Pickle serialization is disabled for security reasons. Use JSON instead.")


def deserialize_pickle(_data: bytes) -> Any:
    """
    Pickle deserialization is intentionally disabled.

    Pickle can execute arbitrary code during deserialization, which is not safe
    for any data that might be influenced by users or external systems.
    """
    raise ValueError("Pickle deserialization is disabled for security reasons. Use JSON instead.")


def compress_json(data: Any) -> bytes:
    """
    Serialize and compress data for storage efficiency
    """
    import zlib

    json_str = serialize_json(data)
    return zlib.compress(json_str.encode("utf-8"))


def decompress_json(compressed_data: bytes) -> Any:
    """
    Decompress and deserialize data
    """
    import zlib

    json_str = zlib.decompress(compressed_data).decode("utf-8")
    return deserialize_json(json_str)
