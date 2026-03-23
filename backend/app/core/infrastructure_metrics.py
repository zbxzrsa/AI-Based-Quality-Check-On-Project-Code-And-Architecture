"""
Infrastructure Metrics Collection for CloudWatch

Provides:
- Custom application metrics collection
- EC2 instance metrics (CPU, memory, disk, network)
- Database connection pool metrics
- Cache metrics (hit/miss ratio, eviction rate)
- Integration with CloudWatch Metrics API

Validates Requirements: 7.4, 7.10
"""
import logging
import os
import psutil
from typing import Dict, Optional
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception


logger = logging.getLogger(__name__)


class InfrastructureMetricsCollector:
    """
    Collects and sends infrastructure metrics to CloudWatch.
    
    Validates Requirements: 7.4, 7.10
    """
    
    def __init__(
        self,
        namespace: Optional[str] = None,
        region_name: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Initialize infrastructure metrics collector.
        
        Args:
            namespace: CloudWatch namespace (default: AICodeReviewer/{environment})
            region_name: AWS region (default: from AWS_REGION env var)
            enabled: Whether metrics collection is enabled
        """
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.service_name = os.getenv('SERVICE_NAME', 'backend-api')
        self.instance_id = os.getenv('INSTANCE_ID', 'local')
        
        # CloudWatch configuration
        self.namespace = namespace or f"AICodeReviewer/{self.environment}"
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.enabled = enabled and os.getenv('CLOUDWATCH_METRICS_ENABLED', 'true').lower() == 'true'
        
        # Initialize CloudWatch client
        self.cloudwatch_client = None
        if BOTO3_AVAILABLE and self.enabled:
            try:
                self.cloudwatch_client = boto3.client(
                    'cloudwatch',
                    region_name=self.region_name
                )
                logger.info(
                    "Infrastructure metrics collector initialized",
                    extra={
                        'namespace': self.namespace,
                        'region': self.region_name,
                        'instance_id': self.instance_id
                    }
                )
            except (NoCredentialsError, Exception) as e:
                logger.warning(
                    f"Failed to initialize CloudWatch client: {e}",
                    extra={'error': str(e)}
                )
                self.enabled = False
    
    def collect_system_metrics(self) -> Dict[str, float]:
        """
        Collect system-level metrics (CPU, memory, disk, network).
        
        Returns:
            Dictionary of metric names and values
            
        Validates Requirement: 7.4
        """
        metrics = {}
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics['cpu_usage_percent'] = cpu_percent
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics['memory_used_percent'] = memory.percent
            metrics['memory_available_mb'] = memory.available / (1024 * 1024)
            metrics['memory_used_mb'] = memory.used / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics['disk_used_percent'] = disk.percent
            metrics['disk_free_gb'] = disk.free / (1024 * 1024 * 1024)
            metrics['disk_used_gb'] = disk.used / (1024 * 1024 * 1024)
            
            # Network metrics
            net_io = psutil.net_io_counters()
            metrics['network_bytes_sent'] = net_io.bytes_sent
            metrics['network_bytes_received'] = net_io.bytes_recv
            metrics['network_packets_sent'] = net_io.packets_sent
            metrics['network_packets_received'] = net_io.packets_recv
            metrics['network_errors_in'] = net_io.errin
            metrics['network_errors_out'] = net_io.errout
            metrics['network_drops_in'] = net_io.dropin
            metrics['network_drops_out'] = net_io.dropout
            
            # Process metrics
            metrics['processes_total'] = len(psutil.pids())
            
            logger.debug(
                "System metrics collected",
                extra={'metrics_count': len(metrics)}
            )
            
        except Exception as e:
            logger.error(
                f"Failed to collect system metrics: {e}",
                extra={'error': str(e), 'error_type': type(e).__name__}
            )
        
        return metrics
    
    def collect_connection_pool_metrics(
        self,
        pool_name: str,
        size: int,
        checked_out: int,
        overflow: int,
        checked_in: int
    ) -> Dict[str, float]:
        """
        Collect database connection pool metrics.
        
        Args:
            pool_name: Name of the connection pool (e.g., 'postgresql', 'redis')
            size: Total pool size
            checked_out: Number of connections checked out
            overflow: Number of overflow connections
            checked_in: Number of connections checked in
            
        Returns:
            Dictionary of metric names and values
            
        Validates Requirement: 7.4
        """
        metrics = {
            f'{pool_name}_pool_size': size,
            f'{pool_name}_pool_checked_out': checked_out,
            f'{pool_name}_pool_overflow': overflow,
            f'{pool_name}_pool_checked_in': checked_in,
            f'{pool_name}_pool_utilization_percent': (checked_out / size * 100) if size > 0 else 0
        }
        
        logger.debug(
            f"Connection pool metrics collected for {pool_name}",
            extra={'pool_name': pool_name, 'metrics': metrics}
        )
        
        return metrics
    
    def collect_cache_metrics(
        self,
        cache_name: str,
        hits: int,
        misses: int,
        evictions: int,
        size: int
    ) -> Dict[str, float]:
        """
        Collect cache metrics (hit/miss ratio, eviction rate).
        
        Args:
            cache_name: Name of the cache (e.g., 'redis', 'local')
            hits: Number of cache hits
            misses: Number of cache misses
            evictions: Number of cache evictions
            size: Current cache size
            
        Returns:
            Dictionary of metric names and values
            
        Validates Requirement: 7.4
        """
        total_requests = hits + misses
        hit_ratio = (hits / total_requests * 100) if total_requests > 0 else 0
        miss_ratio = (misses / total_requests * 100) if total_requests > 0 else 0
        
        metrics = {
            f'{cache_name}_cache_hits': hits,
            f'{cache_name}_cache_misses': misses,
            f'{cache_name}_cache_hit_ratio_percent': hit_ratio,
            f'{cache_name}_cache_miss_ratio_percent': miss_ratio,
            f'{cache_name}_cache_evictions': evictions,
            f'{cache_name}_cache_size': size
        }
        
        logger.debug(
            f"Cache metrics collected for {cache_name}",
            extra={'cache_name': cache_name, 'hit_ratio': hit_ratio}
        )
        
        return metrics
    
    def send_metrics_to_cloudwatch(
        self,
        metrics: Dict[str, float],
        dimensions: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send metrics to CloudWatch.
        
        Args:
            metrics: Dictionary of metric names and values
            dimensions: Optional dimensions to add to metrics
            
        Returns:
            True if metrics were sent successfully, False otherwise
            
        Validates Requirement: 7.4
        """
        if not self.enabled or not self.cloudwatch_client:
            logger.debug("CloudWatch metrics disabled or client not available")
            return False
        
        if not metrics:
            logger.debug("No metrics to send")
            return False
        
        try:
            # Default dimensions
            default_dimensions = {
                'Environment': self.environment,
                'ServiceName': self.service_name,
                'InstanceId': self.instance_id
            }
            
            # Merge with provided dimensions
            if dimensions:
                default_dimensions.update(dimensions)
            
            # Convert dimensions to CloudWatch format
            dimension_list = [
                {'Name': key, 'Value': value}
                for key, value in default_dimensions.items()
            ]
            
            # Prepare metric data
            metric_data = []
            timestamp = datetime.utcnow()
            
            for metric_name, value in metrics.items():
                metric_data.append({
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': self._get_metric_unit(metric_name),
                    'Timestamp': timestamp,
                    'Dimensions': dimension_list
                })
            
            # Send metrics in batches of 20 (CloudWatch limit)
            batch_size = 20
            for i in range(0, len(metric_data), batch_size):
                batch = metric_data[i:i + batch_size]
                
                self.cloudwatch_client.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
                
                logger.debug(
                    f"Sent {len(batch)} metrics to CloudWatch",
                    extra={
                        'namespace': self.namespace,
                        'metrics_count': len(batch)
                    }
                )
            
            logger.info(
                f"Successfully sent {len(metrics)} metrics to CloudWatch",
                extra={
                    'namespace': self.namespace,
                    'metrics_count': len(metrics)
                }
            )
            
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(
                f"Failed to send metrics to CloudWatch: {error_code}",
                extra={
                    'error': str(e),
                    'error_code': error_code,
                    'namespace': self.namespace
                }
            )
            return False
            
        except Exception as e:
            logger.error(
                f"Unexpected error sending metrics to CloudWatch: {e}",
                extra={
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            return False
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """
        Get the appropriate CloudWatch unit for a metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            CloudWatch unit string
        """
        if 'percent' in metric_name.lower():
            return 'Percent'
        elif 'bytes' in metric_name.lower():
            return 'Bytes'
        elif 'mb' in metric_name.lower():
            return 'Megabytes'
        elif 'gb' in metric_name.lower():
            return 'Gigabytes'
        elif 'ms' in metric_name.lower() or 'milliseconds' in metric_name.lower():
            return 'Milliseconds'
        elif 'seconds' in metric_name.lower():
            return 'Seconds'
        else:
            return 'Count'
    
    def collect_and_send_all_metrics(
        self,
        additional_metrics: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        Collect all system metrics and send to CloudWatch.
        
        Args:
            additional_metrics: Optional additional metrics to include
            
        Returns:
            True if metrics were sent successfully, False otherwise
            
        Validates Requirement: 7.4
        """
        # Collect system metrics
        metrics = self.collect_system_metrics()
        
        # Add additional metrics if provided
        if additional_metrics:
            metrics.update(additional_metrics)
        
        # Send to CloudWatch
        return self.send_metrics_to_cloudwatch(metrics)


# Global metrics collector instance
_metrics_collector: Optional[InfrastructureMetricsCollector] = None


def get_metrics_collector() -> InfrastructureMetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        InfrastructureMetricsCollector instance
    """
    global _metrics_collector
    
    if _metrics_collector is None:
        _metrics_collector = InfrastructureMetricsCollector()
    
    return _metrics_collector


def collect_and_send_metrics(
    additional_metrics: Optional[Dict[str, float]] = None
) -> bool:
    """
    Convenience function to collect and send metrics.
    
    Args:
        additional_metrics: Optional additional metrics to include
        
    Returns:
        True if metrics were sent successfully, False otherwise
    """
    collector = get_metrics_collector()
    return collector.collect_and_send_all_metrics(additional_metrics)
