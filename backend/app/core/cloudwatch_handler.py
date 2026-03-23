"""
CloudWatch Logs integration for centralized logging

Provides:
- CloudWatch Logs handler with watchtower
- Automatic log group and stream creation
- 30-day log retention configuration
- AWS credentials and region configuration
- Error handling for CloudWatch connection failures
- Graceful fallback when CloudWatch is unavailable

Validates Requirements: 7.2, 7.10
"""
import logging
import os
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
    from watchtower import CloudWatchLogHandler
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception
    PartialCredentialsError = Exception
    CloudWatchLogHandler = None


logger = logging.getLogger(__name__)


class CloudWatchConfig:
    """
    Configuration for CloudWatch Logs integration.
    
    Validates Requirements: 7.2, 7.10
    """
    
    def __init__(
        self,
        log_group: Optional[str] = None,
        log_stream: Optional[str] = None,
        region_name: Optional[str] = None,
        retention_days: int = 30,
        enabled: bool = True
    ):
        """
        Initialize CloudWatch configuration.
        
        Args:
            log_group: CloudWatch log group name (default: /aws/application/{service_name})
            log_stream: CloudWatch log stream name (default: {environment}/{instance_id})
            region_name: AWS region (default: from AWS_REGION env var or us-east-1)
            retention_days: Log retention in days (Requirement 7.10)
            enabled: Whether CloudWatch logging is enabled
        """
        self.service_name = os.getenv('SERVICE_NAME', 'backend-api')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.instance_id = os.getenv('INSTANCE_ID', 'local')
        
        # Log group configuration (Requirement 7.2)
        self.log_group = log_group or f"/aws/application/{self.service_name}"
        
        # Log stream configuration (Requirement 7.2)
        self.log_stream = log_stream or f"{self.environment}/{self.instance_id}"
        
        # AWS region configuration
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        
        # Log retention (Requirement 7.10)
        self.retention_days = retention_days
        
        # Enable/disable CloudWatch
        self.enabled = enabled and os.getenv('CLOUDWATCH_ENABLED', 'true').lower() == 'true'
    
    def __repr__(self) -> str:
        return (
            f"CloudWatchConfig(log_group={self.log_group}, "
            f"log_stream={self.log_stream}, "
            f"region={self.region_name}, "
            f"retention_days={self.retention_days}, "
            f"enabled={self.enabled})"
        )


def create_cloudwatch_handler(
    config: Optional[CloudWatchConfig] = None,
    log_level: int = logging.INFO
) -> Optional[CloudWatchLogHandler]:
    """
    Create CloudWatch Logs handler with proper configuration.
    
    This function:
    1. Creates boto3 CloudWatch Logs client
    2. Creates log group if it doesn't exist
    3. Sets log retention to 30 days (Requirement 7.10)
    4. Creates CloudWatch log handler
    5. Handles AWS credential and connection errors gracefully
    
    Args:
        config: CloudWatch configuration (uses defaults if None)
        log_level: Minimum log level to send to CloudWatch
        
    Returns:
        CloudWatchLogHandler instance or None if CloudWatch is unavailable
        
    Validates Requirements: 7.2, 7.10
    """
    if not CLOUDWATCH_AVAILABLE:
        logger.warning("CloudWatch dependencies not installed (boto3, watchtower)")
        return None
    
    if config is None:
        config = CloudWatchConfig()
    
    # Check if CloudWatch is enabled
    if not config.enabled:
        logger.info("CloudWatch logging is disabled")
        return None
    
    try:
        # Create boto3 CloudWatch Logs client
        logs_client = boto3.client(
            'logs',
            region_name=config.region_name
        )
        
        # Ensure log group exists and set retention (Requirement 7.2, 7.10)
        _ensure_log_group_exists(
            logs_client,
            config.log_group,
            config.retention_days
        )
        
        # Create CloudWatch handler (Requirement 7.2)
        handler = CloudWatchLogHandler(
            log_group_name=config.log_group,
            log_stream_name=config.log_stream,
            boto3_client=logs_client,
            send_interval=5,  # Send logs every 5 seconds
            max_batch_size=10000,  # Maximum batch size in bytes
            max_batch_count=100,  # Maximum number of log events per batch
            create_log_group=False,  # We create it manually to set retention
            create_log_stream=True  # Auto-create log stream
        )
        
        handler.setLevel(log_level)
        
        logger.info(
            "CloudWatch Logs handler created successfully",
            extra={
                'log_group': config.log_group,
                'log_stream': config.log_stream,
                'region': config.region_name,
                'retention_days': config.retention_days
            }
        )
        
        return handler
        
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.warning(
            "AWS credentials not found, CloudWatch logging disabled",
            extra={'error': str(e)}
        )
        return None
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.warning(
            f"Failed to create CloudWatch handler: {error_code}",
            extra={
                'error': str(e),
                'error_code': error_code,
                'log_group': config.log_group
            }
        )
        return None
        
    except Exception as e:
        logger.warning(
            "Unexpected error creating CloudWatch handler",
            extra={
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        return None


def _ensure_log_group_exists(
    logs_client,
    log_group_name: str,
    retention_days: int
) -> None:
    """
    Ensure CloudWatch log group exists with proper retention.
    
    Creates log group if it doesn't exist and sets retention policy
    to 30 days as per Requirement 7.10.
    
    Args:
        logs_client: boto3 CloudWatch Logs client
        log_group_name: Name of the log group
        retention_days: Log retention in days (Requirement 7.10)
        
    Validates Requirements: 7.2, 7.10
    """
    try:
        # Check if log group exists
        response = logs_client.describe_log_groups(
            logGroupNamePrefix=log_group_name,
            limit=1
        )
        
        log_groups = response.get('logGroups', [])
        log_group_exists = any(
            lg['logGroupName'] == log_group_name
            for lg in log_groups
        )
        
        if not log_group_exists:
            # Create log group (Requirement 7.2)
            logs_client.create_log_group(logGroupName=log_group_name)
            logger.info(f"Created CloudWatch log group: {log_group_name}")
        
        # Set retention policy (Requirement 7.10)
        logs_client.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=retention_days
        )
        logger.info(
            f"Set log retention to {retention_days} days for {log_group_name}"
        )
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        
        if error_code == 'ResourceAlreadyExistsException':
            # Log group already exists, just set retention
            try:
                logs_client.put_retention_policy(
                    logGroupName=log_group_name,
                    retentionInDays=retention_days
                )
                logger.info(
                    f"Updated log retention to {retention_days} days for {log_group_name}"
                )
            except ClientError as retention_error:
                logger.warning(
                    f"Failed to set retention policy: {retention_error}"
                )
        else:
            raise


def add_cloudwatch_handler_to_logger(
    logger_instance: logging.Logger,
    config: Optional[CloudWatchConfig] = None,
    log_level: int = logging.INFO
) -> bool:
    """
    Add CloudWatch handler to an existing logger.
    
    This is a convenience function to add CloudWatch logging to any logger.
    Returns True if handler was added successfully, False otherwise.
    
    Args:
        logger_instance: Logger to add CloudWatch handler to
        config: CloudWatch configuration (uses defaults if None)
        log_level: Minimum log level to send to CloudWatch
        
    Returns:
        True if CloudWatch handler was added, False otherwise
        
    Validates Requirements: 7.2, 7.10
    """
    handler = create_cloudwatch_handler(config, log_level)
    
    if handler:
        logger_instance.addHandler(handler)
        return True
    
    return False


def get_cloudwatch_status(config: Optional[CloudWatchConfig] = None) -> dict:
    """
    Get CloudWatch integration status.
    
    Returns information about CloudWatch configuration and connectivity.
    
    Args:
        config: CloudWatch configuration (uses defaults if None)
        
    Returns:
        Dictionary with status information
        
    Validates Requirements: 7.2, 7.10
    """
    if config is None:
        config = CloudWatchConfig()
    
    status = {
        'enabled': config.enabled,
        'log_group': config.log_group,
        'log_stream': config.log_stream,
        'region': config.region_name,
        'retention_days': config.retention_days,
        'connected': False,
        'error': None
    }
    
    if not CLOUDWATCH_AVAILABLE:
        status['error'] = 'CloudWatch dependencies not installed (boto3, watchtower)'
        return status
    
    if not config.enabled:
        status['error'] = 'CloudWatch logging is disabled'
        return status
    
    try:
        # Test connection
        logs_client = boto3.client('logs', region_name=config.region_name)
        logs_client.describe_log_groups(limit=1)
        status['connected'] = True
        
    except (NoCredentialsError, PartialCredentialsError) as e:
        status['error'] = f'AWS credentials not found: {str(e)}'
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        status['error'] = f'AWS error: {error_code}'
        
    except Exception as e:
        status['error'] = f'Unexpected error: {type(e).__name__}'
    
    return status
