"""
AWS Secrets Manager integration for secure configuration management.

This module provides functionality to:
- Retrieve secrets from AWS Secrets Manager
- Cache secrets to reduce API calls
- Implement secret rotation support
- Handle fallback to environment variables

Validates Requirements: 14.4
"""
import json
import logging
import os
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class SecretsManagerClient:
    """
    AWS Secrets Manager client with caching and fallback support.
    
    Features:
    - Automatic secret retrieval from AWS Secrets Manager
    - In-memory caching with TTL to reduce API calls
    - Fallback to environment variables if Secrets Manager is unavailable
    - Support for secret rotation
    - JSON secret parsing
    
    Validates Requirement 14.4: Store sensitive configuration in AWS Secrets Manager
    """
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        cache_ttl_seconds: int = 300,
        enabled: bool = True
    ):
        """
        Initialize Secrets Manager client.
        
        Args:
            region_name: AWS region for Secrets Manager
            cache_ttl_seconds: Time-to-live for cached secrets (default: 5 minutes)
            enabled: Whether to use Secrets Manager (False = use env vars only)
        """
        self.region_name = region_name
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enabled = enabled
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        if self.enabled:
            try:
                self.client = boto3.client(
                    service_name='secretsmanager',
                    region_name=region_name
                )
                logger.info(f"AWS Secrets Manager client initialized for region {region_name}")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize AWS Secrets Manager client: {e}. "
                    "Falling back to environment variables."
                )
                self.enabled = False
                self.client = None
        else:
            self.client = None
            logger.info("AWS Secrets Manager disabled, using environment variables only")
    
    def get_secret(
        self,
        secret_name: str,
        key: Optional[str] = None,
        default: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Retrieve a secret from AWS Secrets Manager or environment variables.
        
        Args:
            secret_name: Name of the secret in Secrets Manager
            key: Optional key for JSON secrets (e.g., "database/password")
            default: Default value if secret not found
            use_cache: Whether to use cached value
        
        Returns:
            Secret value as string, or default if not found
        
        Example:
            # Get entire secret
            api_key = secrets.get_secret("production/api/openai_key")
            
            # Get specific key from JSON secret
            db_password = secrets.get_secret(
                "production/database",
                key="postgres_password"
            )
        """
        # Check cache first
        if use_cache and secret_name in self._cache:
            cached_data = self._cache[secret_name]
            if datetime.now() < cached_data['expires_at']:
                logger.debug(f"Using cached secret: {secret_name}")
                secret_value = cached_data['value']
                return self._extract_key(secret_value, key) if key else secret_value
        
        # Try AWS Secrets Manager if enabled
        if self.enabled and self.client:
            try:
                response = self.client.get_secret_value(SecretId=secret_name)
                
                # Extract secret string
                if 'SecretString' in response:
                    secret_value = response['SecretString']
                else:
                    # Binary secrets (not commonly used for config)
                    import base64
                    secret_value = base64.b64decode(response['SecretBinary']).decode('utf-8')
                
                # Cache the secret
                self._cache[secret_name] = {
                    'value': secret_value,
                    'expires_at': datetime.now() + timedelta(seconds=self.cache_ttl_seconds)
                }
                
                logger.info(f"Retrieved secret from AWS Secrets Manager: {secret_name}")
                
                # Extract specific key if requested
                if key:
                    return self._extract_key(secret_value, key)
                
                return secret_value
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    logger.warning(f"Secret not found in Secrets Manager: {secret_name}")
                elif error_code == 'InvalidRequestException':
                    logger.error(f"Invalid request for secret: {secret_name}")
                elif error_code == 'InvalidParameterException':
                    logger.error(f"Invalid parameter for secret: {secret_name}")
                elif error_code == 'DecryptionFailure':
                    logger.error(f"Failed to decrypt secret: {secret_name}")
                elif error_code == 'InternalServiceError':
                    logger.error(f"AWS Secrets Manager internal error for: {secret_name}")
                else:
                    logger.error(f"Error retrieving secret {secret_name}: {e}")
            except BotoCoreError as e:
                logger.error(f"BotoCore error retrieving secret {secret_name}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error retrieving secret {secret_name}: {e}")
        
        # Fallback to environment variable
        env_var_name = self._secret_name_to_env_var(secret_name, key)
        env_value = os.environ.get(env_var_name)
        
        if env_value:
            logger.debug(f"Using environment variable: {env_var_name}")
            return env_value
        
        # Return default if provided
        if default is not None:
            logger.debug(f"Using default value for: {secret_name}")
            return default
        
        logger.warning(
            f"Secret not found in Secrets Manager or environment: {secret_name}"
        )
        return None
    
    def get_secret_dict(
        self,
        secret_name: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve a JSON secret as a dictionary.
        
        Args:
            secret_name: Name of the secret in Secrets Manager
            use_cache: Whether to use cached value
        
        Returns:
            Dictionary of secret key-value pairs
        
        Example:
            db_config = secrets.get_secret_dict("production/database")
            host = db_config.get("postgres_host")
            password = db_config.get("postgres_password")
        """
        secret_value = self.get_secret(secret_name, use_cache=use_cache)
        
        if not secret_value:
            return {}
        
        try:
            return json.loads(secret_value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON secret {secret_name}: {e}")
            return {}
    
    def _extract_key(self, secret_value: str, key: str) -> Optional[str]:
        """
        Extract a specific key from a JSON secret.
        
        Args:
            secret_value: JSON string containing the secret
            key: Key to extract
        
        Returns:
            Value for the specified key, or None if not found
        """
        try:
            secret_dict = json.loads(secret_value)
            return secret_dict.get(key)
        except json.JSONDecodeError:
            logger.warning(f"Secret is not JSON, cannot extract key: {key}")
            return None
    
    def _secret_name_to_env_var(self, secret_name: str, key: Optional[str] = None) -> str:
        """
        Convert secret name to environment variable name.
        
        Args:
            secret_name: Secret name (e.g., "production/database/postgres_password")
            key: Optional key within JSON secret
        
        Returns:
            Environment variable name (e.g., "POSTGRES_PASSWORD")
        
        Examples:
            "production/database/postgres_password" -> "POSTGRES_PASSWORD"
            "staging/api/openai_key" -> "OPENAI_KEY"
            "production/database" + key="postgres_host" -> "POSTGRES_HOST"
        """
        if key:
            # Use the key as the env var name
            return key.upper().replace('/', '_').replace('-', '_')
        
        # Extract the last part of the secret name
        parts = secret_name.split('/')
        env_var = parts[-1].upper().replace('-', '_')
        return env_var
    
    def invalidate_cache(self, secret_name: Optional[str] = None):
        """
        Invalidate cached secrets.
        
        Args:
            secret_name: Specific secret to invalidate, or None to clear all
        """
        if secret_name:
            if secret_name in self._cache:
                del self._cache[secret_name]
                logger.info(f"Invalidated cache for secret: {secret_name}")
        else:
            self._cache.clear()
            logger.info("Invalidated all cached secrets")
    
    def rotate_secret(self, secret_name: str) -> bool:
        """
        Trigger secret rotation in AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret to rotate
        
        Returns:
            True if rotation initiated successfully, False otherwise
        
        Note:
            This requires a Lambda function to be configured for rotation.
            See AWS documentation for setting up automatic rotation.
        """
        if not self.enabled or not self.client:
            logger.warning("Cannot rotate secret: Secrets Manager not enabled")
            return False
        
        try:
            self.client.rotate_secret(SecretId=secret_name)
            logger.info(f"Initiated rotation for secret: {secret_name}")
            
            # Invalidate cache for this secret
            self.invalidate_cache(secret_name)
            
            return True
        except ClientError as e:
            logger.error(f"Failed to rotate secret {secret_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error rotating secret {secret_name}: {e}")
            return False
    
    def list_secrets(self, prefix: Optional[str] = None) -> list:
        """
        List all secrets in Secrets Manager.
        
        Args:
            prefix: Optional prefix to filter secrets (e.g., "production/")
        
        Returns:
            List of secret names
        """
        if not self.enabled or not self.client:
            logger.warning("Cannot list secrets: Secrets Manager not enabled")
            return []
        
        try:
            secrets = []
            paginator = self.client.get_paginator('list_secrets')
            
            for page in paginator.paginate():
                for secret in page['SecretList']:
                    secret_name = secret['Name']
                    if prefix is None or secret_name.startswith(prefix):
                        secrets.append(secret_name)
            
            logger.info(f"Found {len(secrets)} secrets with prefix: {prefix}")
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


# Global instance
_secrets_manager: Optional[SecretsManagerClient] = None


def get_secrets_manager() -> SecretsManagerClient:
    """
    Get or create the global Secrets Manager client instance.
    
    Returns:
        SecretsManagerClient instance
    """
    global _secrets_manager
    
    if _secrets_manager is None:
        # Read configuration from environment
        region = os.environ.get('AWS_REGION', 'us-east-1')
        enabled = os.environ.get('AWS_SECRETS_MANAGER_ENABLED', 'false').lower() == 'true'
        cache_ttl = int(os.environ.get('SECRETS_CACHE_TTL_SECONDS', '300'))
        
        _secrets_manager = SecretsManagerClient(
            region_name=region,
            cache_ttl_seconds=cache_ttl,
            enabled=enabled
        )
    
    return _secrets_manager


def load_secrets_into_env(secret_mappings: Dict[str, str]):
    """
    Load secrets from Secrets Manager into environment variables.
    
    This is useful for loading secrets at application startup.
    
    Args:
        secret_mappings: Dictionary mapping secret names to env var names
                        Example: {
                            "production/database/postgres_password": "POSTGRES_PASSWORD",
                            "production/api/openai_key": "OPENAI_API_KEY"
                        }
    
    Example:
        load_secrets_into_env({
            "production/database/postgres_password": "POSTGRES_PASSWORD",
            "production/api/openai_key": "OPENAI_API_KEY",
            "production/api/github_token": "GITHUB_TOKEN"
        })
    """
    secrets_manager = get_secrets_manager()
    
    for secret_name, env_var_name in secret_mappings.items():
        # Skip if env var already set (allow local override)
        if os.environ.get(env_var_name):
            logger.debug(f"Skipping {env_var_name}: already set in environment")
            continue
        
        secret_value = secrets_manager.get_secret(secret_name)
        if secret_value:
            os.environ[env_var_name] = secret_value
            logger.info(f"Loaded secret into environment: {env_var_name}")
        else:
            logger.warning(f"Failed to load secret: {secret_name} -> {env_var_name}")
