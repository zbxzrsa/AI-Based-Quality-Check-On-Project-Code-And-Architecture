"""
Configuration loading utilities.

This module provides reusable configuration loading functions following the DRY principle.
"""
import os
from typing import Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


def get_env(
    key: str,
    default: Optional[str] = None,
    required: bool = False,
    log_value: bool = True
) -> str:
    """
    Get environment variable with validation and logging.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Raise error if not found and no default
        log_value: Whether to log the value (set False for secrets)
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If required and not found
    """
    value = os.getenv(key, default)
    
    if value is None and required:
        raise ValueError(f"Required environment variable '{key}' not found")
    
    if log_value and value:
        logger.info(f"Loaded config: {key}={value}")
    elif value:
        logger.info(f"Loaded config: {key}=***")
    
    return value


def get_env_bool(
    key: str,
    default: bool = False,
    required: bool = False
) -> bool:
    """
    Get boolean environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Raise error if not found
        
    Returns:
        Boolean value
    """
    value = get_env(key, str(default), required=required)
    return value.lower() in ('true', '1', 'yes', 'on')


def get_env_int(
    key: str,
    default: Optional[int] = None,
    required: bool = False,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None
) -> int:
    """
    Get integer environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Raise error if not found
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Integer value
        
    Raises:
        ValueError: If value is invalid or out of range
    """
    value_str = get_env(key, str(default) if default is not None else None, required=required)
    
    try:
        value = int(value_str)
    except (ValueError, TypeError):
        raise ValueError(f"Environment variable '{key}' must be an integer, got: {value_str}")
    
    if min_value is not None and value < min_value:
        raise ValueError(f"Environment variable '{key}' must be >= {min_value}, got: {value}")
    
    if max_value is not None and value > max_value:
        raise ValueError(f"Environment variable '{key}' must be <= {max_value}, got: {value}")
    
    return value


def get_env_float(
    key: str,
    default: Optional[float] = None,
    required: bool = False,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> float:
    """
    Get float environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Raise error if not found
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Float value
        
    Raises:
        ValueError: If value is invalid or out of range
    """
    value_str = get_env(key, str(default) if default is not None else None, required=required)
    
    try:
        value = float(value_str)
    except (ValueError, TypeError):
        raise ValueError(f"Environment variable '{key}' must be a float, got: {value_str}")
    
    if min_value is not None and value < min_value:
        raise ValueError(f"Environment variable '{key}' must be >= {min_value}, got: {value}")
    
    if max_value is not None and value > max_value:
        raise ValueError(f"Environment variable '{key}' must be <= {max_value}, got: {value}")
    
    return value


def get_env_list(
    key: str,
    default: Optional[list] = None,
    separator: str = ",",
    required: bool = False
) -> list[str]:
    """
    Get list environment variable (comma-separated by default).
    
    Args:
        key: Environment variable name
        default: Default value if not found
        separator: Separator character
        required: Raise error if not found
        
    Returns:
        List of strings
    """
    default_str = separator.join(default) if default else None
    value_str = get_env(key, default_str, required=required)
    
    if not value_str:
        return []
    
    return [item.strip() for item in value_str.split(separator) if item.strip()]


def validate_config(config_dict: dict, required_keys: list[str]) -> None:
    """
    Validate that all required configuration keys are present.
    
    Args:
        config_dict: Configuration dictionary
        required_keys: List of required keys
        
    Raises:
        ValueError: If any required key is missing
    """
    missing_keys = [key for key in required_keys if key not in config_dict or config_dict[key] is None]
    
    if missing_keys:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")
    
    logger.info(f"Configuration validated: all {len(required_keys)} required keys present")
