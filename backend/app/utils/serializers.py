"""
Serialization utilities for Redis caching

WARNING: Avoid pickle for untrusted data due to security risks (arbitrary code execution).
Use JSON-based serialization for all user-provided or external data.
"""
import json
import pickle
from typing import Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
import logging

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
            return obj.decode('utf-8')
        if hasattr(obj, '__dict__'):
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
        raise ValueError(f"Cannot serialize data to JSON: {e}")


def deserialize_json(json_str: str) -> Any:
    """
    Deserialize JSON string to Python object
    
    Safe method that only deserializes valid JSON.
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Cannot deserialize JSON: {e}")


def serialize_pickle(data: Any) -> bytes:
    """
    Serialize data using pickle for complex Python objects.
    
    ⚠️  SECURITY WARNING: Only use for trusted data!
    Pickle can execute arbitrary code during deserialization.
    Never use pickle to deserialize untrusted data from users,
    databases, or external sources.
    
    Recommended alternatives:
    - Use JSON with custom encoders for most data types
    - Use msgpack or protobuf for binary serialization
    """
    logger.warning("Using pickle serialization. Ensure data is from a trusted source.")
    try:
        return pickle.dumps(data)
    except (TypeError, pickle.PickleError) as e:
        raise ValueError(f"Cannot serialize data with pickle: {e}")


def deserialize_pickle(data: bytes) -> Any:
    """
    Deserialize pickle data.
    
    ⚠️  SECURITY WARNING: Only use for trusted data!
    Pickle deserialization can execute arbitrary code.
    
    Only deserialize pickled data that:
    1. Comes from your own application
    2. Is stored in a controlled, secure location
    3. Has not been tampered with
    
    Never deserialize:
    - User-provided pickled data
    - Data from untrusted sources
    - Data from the internet
    """
    logger.warning("Deserializing pickle data. Ensure data is from a trusted source.")
    try:
        # Use pickle.loads() with default protocol for backward compatibility
        # Consider adding integrity checks (HMAC) for production use
        return pickle.loads(data)
    except (TypeError, pickle.UnpicklingError) as e:
        raise ValueError(f"Cannot deserialize pickle data: {e}")


def compress_json(data: Any) -> bytes:
    """
    Serialize and compress data for storage efficiency
    """
    import zlib
    json_str = serialize_json(data)
    return zlib.compress(json_str.encode('utf-8'))


def decompress_json(compressed_data: bytes) -> Any:
    """
    Decompress and deserialize data
    """
    import zlib
    json_str = zlib.decompress(compressed_data).decode('utf-8')
    return deserialize_json(json_str)
