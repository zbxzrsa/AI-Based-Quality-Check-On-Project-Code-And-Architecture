"""
Feature flag system for gradual rollout and A/B testing.

This module provides a flexible feature flag system that supports:
- Environment-based flags
- User-based flags
- Percentage-based rollouts
- Dynamic flag updates without restart

Validates Requirement 14.7: Implement feature flags for gradual rollout
"""
import logging
import os
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)


class FeatureFlagStrategy(Enum):
    """Strategy for evaluating feature flags."""
    BOOLEAN = "boolean"  # Simple on/off
    PERCENTAGE = "percentage"  # Percentage-based rollout
    USER_LIST = "user_list"  # Specific user IDs
    ENVIRONMENT = "environment"  # Environment-specific


@dataclass
class FeatureFlag:
    """
    Feature flag definition.
    
    Attributes:
        name: Unique flag name
        enabled: Whether flag is enabled
        description: Human-readable description
        strategy: Evaluation strategy
        config: Additional configuration (e.g., percentage, user list)
    """
    name: str
    enabled: bool
    description: str
    strategy: FeatureFlagStrategy = FeatureFlagStrategy.BOOLEAN
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


class FeatureFlagManager:
    """
    Manages feature flags for the application.
    
    Features:
    - Simple boolean flags
    - Percentage-based rollouts
    - User-specific flags
    - Environment-specific flags
    - Dynamic flag updates
    
    Validates Requirement 14.7
    """
    
    def __init__(self):
        """Initialize feature flag manager."""
        self.flags: Dict[str, FeatureFlag] = {}
        self._load_default_flags()
        self._load_from_environment()
    
    def _load_default_flags(self):
        """Load default feature flags."""
        # Core features
        self.register_flag(
            "github_integration",
            enabled=True,
            description="Enable GitHub webhook integration and PR analysis",
            strategy=FeatureFlagStrategy.BOOLEAN
        )
        
        self.register_flag(
            "llm_analysis",
            enabled=True,
            description="Enable LLM-powered code analysis",
            strategy=FeatureFlagStrategy.BOOLEAN
        )
        
        self.register_flag(
            "architecture_analysis",
            enabled=True,
            description="Enable architecture drift detection and circular dependency analysis",
            strategy=FeatureFlagStrategy.BOOLEAN
        )
        
        self.register_flag(
            "compliance_check",
            enabled=True,
            description="Enable ISO/IEC 25010 compliance verification",
            strategy=FeatureFlagStrategy.BOOLEAN
        )
        
        self.register_flag(
            "audit_logging",
            enabled=True,
            description="Enable comprehensive audit logging",
            strategy=FeatureFlagStrategy.BOOLEAN
        )
        
        # Performance features
        self.register_flag(
            "redis_caching",
            enabled=True,
            description="Enable Redis caching for API responses",
            strategy=FeatureFlagStrategy.BOOLEAN
        )
        
        self.register_flag(
            "query_optimization",
            enabled=True,
            description="Enable database query optimization",
            strategy=FeatureFlagStrategy.BOOLEAN
        )
        
        # Experimental features
        self.register_flag(
            "realtime_updates",
            enabled=False,
            description="Enable WebSocket real-time updates",
            strategy=FeatureFlagStrategy.PERCENTAGE,
            config={"percentage": 10}  # 10% rollout
        )
        
        self.register_flag(
            "advanced_llm_features",
            enabled=False,
            description="Enable advanced LLM features (fine-tuning, custom prompts)",
            strategy=FeatureFlagStrategy.PERCENTAGE,
            config={"percentage": 25}  # 25% rollout
        )
        
        self.register_flag(
            "graph_visualization_v2",
            enabled=False,
            description="Enable new graph visualization engine",
            strategy=FeatureFlagStrategy.PERCENTAGE,
            config={"percentage": 0}  # Not rolled out yet
        )
        
        # Security features
        self.register_flag(
            "rate_limiting",
            enabled=True,
            description="Enable API rate limiting",
            strategy=FeatureFlagStrategy.BOOLEAN
        )
        
        self.register_flag(
            "mfa_authentication",
            enabled=False,
            description="Enable multi-factor authentication",
            strategy=FeatureFlagStrategy.PERCENTAGE,
            config={"percentage": 0}  # Not rolled out yet
        )
        
        # Monitoring features
        self.register_flag(
            "detailed_metrics",
            enabled=True,
            description="Enable detailed performance metrics collection",
            strategy=FeatureFlagStrategy.BOOLEAN
        )
        
        self.register_flag(
            "distributed_tracing",
            enabled=False,
            description="Enable distributed tracing with Jaeger",
            strategy=FeatureFlagStrategy.ENVIRONMENT,
            config={"environments": ["staging", "production"]}
        )
    
    def _load_from_environment(self):
        """Load feature flags from environment variables."""
        # Override flags from environment variables
        # Format: FEATURE_FLAG_{FLAG_NAME}=true/false
        for flag_name in self.flags.keys():
            env_var = f"FEATURE_FLAG_{flag_name.upper()}"
            env_value = os.environ.get(env_var)
            
            if env_value is not None:
                enabled = env_value.lower() in ("true", "1", "yes", "on")
                self.flags[flag_name].enabled = enabled
                logger.info(f"Feature flag '{flag_name}' set to {enabled} from environment")
        
        # Also check legacy environment variables
        legacy_mappings = {
            "ENABLE_GITHUB_INTEGRATION": "github_integration",
            "ENABLE_LLM_ANALYSIS": "llm_analysis",
            "ENABLE_ARCHITECTURE_ANALYSIS": "architecture_analysis",
            "ENABLE_COMPLIANCE_CHECK": "compliance_check",
            "ENABLE_AUDIT_LOGGING": "audit_logging",
            "RATE_LIMIT_ENABLED": "rate_limiting",
        }
        
        for env_var, flag_name in legacy_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None and flag_name in self.flags:
                enabled = env_value.lower() in ("true", "1", "yes", "on")
                self.flags[flag_name].enabled = enabled
                logger.info(f"Feature flag '{flag_name}' set to {enabled} from legacy env var {env_var}")
    
    def register_flag(
        self,
        name: str,
        enabled: bool,
        description: str,
        strategy: FeatureFlagStrategy = FeatureFlagStrategy.BOOLEAN,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Register a new feature flag.
        
        Args:
            name: Unique flag name
            enabled: Default enabled state
            description: Human-readable description
            strategy: Evaluation strategy
            config: Additional configuration
        """
        flag = FeatureFlag(
            name=name,
            enabled=enabled,
            description=description,
            strategy=strategy,
            config=config or {}
        )
        self.flags[name] = flag
        logger.debug(f"Registered feature flag: {name} (enabled={enabled})")
    
    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        environment: Optional[str] = None,
        default: bool = False
    ) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: Name of the feature flag
            user_id: Optional user ID for user-specific flags
            environment: Optional environment for environment-specific flags
            default: Default value if flag not found
        
        Returns:
            True if flag is enabled, False otherwise
        
        Example:
            if feature_flags.is_enabled("github_integration"):
                # Use GitHub integration
                pass
            
            if feature_flags.is_enabled("realtime_updates", user_id="user123"):
                # Enable real-time updates for this user
                pass
        """
        if flag_name not in self.flags:
            logger.warning(f"Feature flag not found: {flag_name}, using default: {default}")
            return default
        
        flag = self.flags[flag_name]
        
        # If flag is disabled, return False immediately
        if not flag.enabled:
            return False
        
        # Evaluate based on strategy
        if flag.strategy == FeatureFlagStrategy.BOOLEAN:
            return flag.enabled
        
        elif flag.strategy == FeatureFlagStrategy.PERCENTAGE:
            if user_id is None:
                logger.warning(f"Percentage-based flag '{flag_name}' requires user_id")
                return False
            
            percentage = flag.config.get("percentage", 0)
            return self._is_in_percentage(user_id, flag_name, percentage)
        
        elif flag.strategy == FeatureFlagStrategy.USER_LIST:
            if user_id is None:
                return False
            
            allowed_users = flag.config.get("users", [])
            return user_id in allowed_users
        
        elif flag.strategy == FeatureFlagStrategy.ENVIRONMENT:
            if environment is None:
                environment = os.environ.get("ENVIRONMENT", "development")
            
            allowed_environments = flag.config.get("environments", [])
            return environment in allowed_environments
        
        return flag.enabled
    
    def _is_in_percentage(self, user_id: str, flag_name: str, percentage: int) -> bool:
        """
        Determine if user is in percentage rollout.
        
        Uses consistent hashing to ensure same user always gets same result.
        
        Args:
            user_id: User identifier
            flag_name: Feature flag name
            percentage: Percentage of users to enable (0-100)
        
        Returns:
            True if user is in the percentage, False otherwise
        """
        if percentage <= 0:
            return False
        if percentage >= 100:
            return True
        
        # Create consistent hash
        hash_input = f"{flag_name}:{user_id}".encode('utf-8')
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        user_percentage = hash_value % 100
        
        return user_percentage < percentage
    
    def enable_flag(self, flag_name: str):
        """
        Enable a feature flag.
        
        Args:
            flag_name: Name of the flag to enable
        """
        if flag_name in self.flags:
            self.flags[flag_name].enabled = True
            logger.info(f"Enabled feature flag: {flag_name}")
        else:
            logger.warning(f"Cannot enable unknown flag: {flag_name}")
    
    def disable_flag(self, flag_name: str):
        """
        Disable a feature flag.
        
        Args:
            flag_name: Name of the flag to disable
        """
        if flag_name in self.flags:
            self.flags[flag_name].enabled = False
            logger.info(f"Disabled feature flag: {flag_name}")
        else:
            logger.warning(f"Cannot disable unknown flag: {flag_name}")
    
    def set_percentage(self, flag_name: str, percentage: int):
        """
        Set percentage for a percentage-based flag.
        
        Args:
            flag_name: Name of the flag
            percentage: Percentage to set (0-100)
        """
        if flag_name not in self.flags:
            logger.warning(f"Cannot set percentage for unknown flag: {flag_name}")
            return
        
        flag = self.flags[flag_name]
        if flag.strategy != FeatureFlagStrategy.PERCENTAGE:
            logger.warning(f"Flag '{flag_name}' is not a percentage-based flag")
            return
        
        flag.config["percentage"] = max(0, min(100, percentage))
        logger.info(f"Set percentage for flag '{flag_name}' to {percentage}%")
    
    def add_user_to_flag(self, flag_name: str, user_id: str):
        """
        Add user to user-list flag.
        
        Args:
            flag_name: Name of the flag
            user_id: User ID to add
        """
        if flag_name not in self.flags:
            logger.warning(f"Cannot add user to unknown flag: {flag_name}")
            return
        
        flag = self.flags[flag_name]
        if flag.strategy != FeatureFlagStrategy.USER_LIST:
            logger.warning(f"Flag '{flag_name}' is not a user-list flag")
            return
        
        if "users" not in flag.config:
            flag.config["users"] = []
        
        if user_id not in flag.config["users"]:
            flag.config["users"].append(user_id)
            logger.info(f"Added user '{user_id}' to flag '{flag_name}'")
    
    def remove_user_from_flag(self, flag_name: str, user_id: str):
        """
        Remove user from user-list flag.
        
        Args:
            flag_name: Name of the flag
            user_id: User ID to remove
        """
        if flag_name not in self.flags:
            logger.warning(f"Cannot remove user from unknown flag: {flag_name}")
            return
        
        flag = self.flags[flag_name]
        if flag.strategy != FeatureFlagStrategy.USER_LIST:
            logger.warning(f"Flag '{flag_name}' is not a user-list flag")
            return
        
        if "users" in flag.config and user_id in flag.config["users"]:
            flag.config["users"].remove(user_id)
            logger.info(f"Removed user '{user_id}' from flag '{flag_name}'")
    
    def get_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all feature flags and their current state.
        
        Returns:
            Dictionary of flag names to flag information
        """
        return {
            name: {
                "enabled": flag.enabled,
                "description": flag.description,
                "strategy": flag.strategy.value,
                "config": flag.config
            }
            for name, flag in self.flags.items()
        }
    
    def get_enabled_flags(self) -> list:
        """
        Get list of currently enabled flags.
        
        Returns:
            List of enabled flag names
        """
        return [name for name, flag in self.flags.items() if flag.enabled]


# Global instance
_feature_flags: Optional[FeatureFlagManager] = None


def get_feature_flags() -> FeatureFlagManager:
    """
    Get or create the global feature flag manager instance.
    
    Returns:
        FeatureFlagManager instance
    """
    global _feature_flags
    
    if _feature_flags is None:
        _feature_flags = FeatureFlagManager()
    
    return _feature_flags


def is_feature_enabled(
    flag_name: str,
    user_id: Optional[str] = None,
    environment: Optional[str] = None,
    default: bool = False
) -> bool:
    """
    Convenience function to check if a feature is enabled.
    
    Args:
        flag_name: Name of the feature flag
        user_id: Optional user ID
        environment: Optional environment
        default: Default value if flag not found
    
    Returns:
        True if feature is enabled, False otherwise
    
    Example:
        from app.core.feature_flags import is_feature_enabled
        
        if is_feature_enabled("github_integration"):
            # Use GitHub integration
            pass
    """
    flags = get_feature_flags()
    return flags.is_enabled(flag_name, user_id, environment, default)


def require_feature(flag_name: str):
    """
    Decorator to require a feature flag for a function.
    
    Args:
        flag_name: Name of the required feature flag
    
    Example:
        @require_feature("github_integration")
        def handle_github_webhook(payload):
            # This function only runs if github_integration is enabled
            pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            if not is_feature_enabled(flag_name):
                raise FeatureFlagDisabledError(
                    f"Feature '{flag_name}' is not enabled"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


class FeatureFlagDisabledError(Exception):
    """Raised when a required feature flag is disabled."""
    pass
