import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
CloudWatch Alarms Management Script

This script provides programmatic management of CloudWatch alarms for the AI Reviewer system.
It complements the Terraform module by allowing runtime alarm management and testing.

Usage:
    python manage_cloudwatch_alarms.py create-all --region us-east-1 --environment prod
    python manage_cloudwatch_alarms.py list --region us-east-1
    python manage_cloudwatch_alarms.py describe --alarm-name prod-ai-reviewer-high-error-rate
    python manage_cloudwatch_alarms.py delete --alarm-name test-alarm
    python manage_cloudwatch_alarms.py test --alarm-name prod-ai-reviewer-high-error-rate

Requirements:
    - boto3
    - AWS credentials configured (via environment variables or ~/.aws/credentials)
    - Appropriate IAM permissions for CloudWatch operations
"""

import argparse
import json
import sys

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    logger.info("Error: boto3 is required. Install with: pip install boto3")
    sys.exit(1)


class CloudWatchAlarmsManager:
    """Manager for CloudWatch alarms operations."""

    def __init__(self, region: str, environment: str = "prod", service_name: str = "ai-reviewer"):
        """
        Initialize the CloudWatch alarms manager.

        Args:
            region: AWS region
            environment: Environment name (dev, staging, prod)
            service_name: Service name for alarm naming
        """
        self.region = region
        self.environment = environment
        self.service_name = service_name
        self.cloudwatch = boto3.client("cloudwatch", region_name=region)
        self.sns = boto3.client("sns", region_name=region)

    def create_sns_topic(self, email: str | None = None) -> str:
        """
        Create SNS topic for alarm notifications.

        Args:
            email: Optional email address for notifications

        Returns:
            SNS topic ARN
        """
        topic_name = f"{self.environment}-{self.service_name}-alerts"

        try:
            response = self.sns.create_topic(
                Name=topic_name,
                Tags=[
                    {"Key": "Environment", "Value": self.environment},
                    {"Key": "Service", "Value": self.service_name},
                    {"Key": "Purpose", "Value": "CloudWatch alarm notifications"},
                ],
            )
            topic_arn = response["TopicArn"]
            logger.info("✓ Created SNS topic: {topic_name}")
            logger.info("  ARN: {topic_arn}")

            # Subscribe email if provided
            if email:
                self.sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email)
                logger.info("✓ Subscribed email: {email}")
                logger.info("  Note: Check your email to confirm the subscription")

            return topic_arn

        except ClientError as e:
            if e.response["Error"]["Code"] == "TopicAlreadyExists":
                # Get existing topic ARN
                topics = self.sns.list_topics()
                for topic in topics["Topics"]:
                    if topic_name in topic["TopicArn"]:
                        logger.info("✓ Using existing SNS topic: {topic_name}")
                        return topic["TopicArn"]
            raise

    def create_high_error_rate_alarm(self, sns_topic_arn: str, threshold: float = 5.0) -> str:
        """
        Create alarm for high error rate (> 5%).

        Args:
            sns_topic_arn: SNS topic ARN for notifications
            threshold: Error rate threshold percentage

        Returns:
            Alarm name
        """
        alarm_name = f"{self.environment}-{self.service_name}-high-error-rate"

        self.cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator="GreaterThanThreshold",
            EvaluationPeriods=2,
            Threshold=threshold,
            AlarmDescription=f"Alert when error rate exceeds {threshold}% for 5 minutes",
            AlarmActions=[sns_topic_arn],
            OKActions=[sns_topic_arn],
            TreatMissingData="notBreaching",
            Metrics=[
                {
                    "Id": "error_rate",
                    "Expression": "100 * (errors / requests)",
                    "Label": "Error Rate %",
                    "ReturnData": True,
                },
                {
                    "Id": "errors",
                    "MetricStat": {
                        "Metric": {"Namespace": self.service_name, "MetricName": "http_errors_total"},
                        "Period": 300,
                        "Stat": "Sum",
                    },
                    "ReturnData": False,
                },
                {
                    "Id": "requests",
                    "MetricStat": {
                        "Metric": {"Namespace": self.service_name, "MetricName": "http_requests_total"},
                        "Period": 300,
                        "Stat": "Sum",
                    },
                    "ReturnData": False,
                },
            ],
            Tags=[
                {"Key": "Environment", "Value": self.environment},
                {"Key": "Severity", "Value": "Critical"},
                {"Key": "Runbook", "Value": "https://docs.example.com/runbooks/high-error-rate"},
            ],
        )

        logger.info("✓ Created alarm: {alarm_name}")
        return alarm_name

    def create_high_response_time_alarm(self, sns_topic_arn: str, threshold: float = 1.0) -> str:
        """
        Create alarm for high API response time (> 1 second P95).

        Args:
            sns_topic_arn: SNS topic ARN for notifications
            threshold: Response time threshold in seconds

        Returns:
            Alarm name
        """
        alarm_name = f"{self.environment}-{self.service_name}-high-response-time"

        self.cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator="GreaterThanThreshold",
            EvaluationPeriods=2,
            Threshold=threshold,
            AlarmDescription=f"Alert when API P95 response time exceeds {threshold} second for 5 minutes",
            AlarmActions=[sns_topic_arn],
            OKActions=[sns_topic_arn],
            TreatMissingData="notBreaching",
            Metrics=[
                {
                    "Id": "response_time",
                    "MetricStat": {
                        "Metric": {"Namespace": self.service_name, "MetricName": "http_request_duration_seconds"},
                        "Period": 300,
                        "Stat": "p95",
                    },
                    "ReturnData": True,
                }
            ],
            Tags=[
                {"Key": "Environment", "Value": self.environment},
                {"Key": "Severity", "Value": "Critical"},
                {"Key": "Runbook", "Value": "https://docs.example.com/runbooks/high-response-time"},
            ],
        )

        logger.info("✓ Created alarm: {alarm_name}")
        return alarm_name

    def create_high_cpu_alarm(
        self, sns_topic_arn: str, threshold: float = 80.0, autoscaling_group: str | None = None
    ) -> str:
        """
        Create alarm for high CPU utilization (> 80%).

        Args:
            sns_topic_arn: SNS topic ARN for notifications
            threshold: CPU utilization threshold percentage
            autoscaling_group: Optional Auto Scaling Group name

        Returns:
            Alarm name
        """
        alarm_name = f"{self.environment}-{self.service_name}-high-cpu-utilization"

        alarm_config = {
            "AlarmName": alarm_name,
            "ComparisonOperator": "GreaterThanThreshold",
            "EvaluationPeriods": 2,
            "MetricName": "CPUUtilization",
            "Namespace": "AWS/EC2",
            "Period": 300,
            "Statistic": "Average",
            "Threshold": threshold,
            "AlarmDescription": f"Alert when CPU utilization exceeds {threshold}% for 10 minutes",
            "AlarmActions": [sns_topic_arn],
            "OKActions": [sns_topic_arn],
            "TreatMissingData": "notBreaching",
            "Tags": [
                {"Key": "Environment", "Value": self.environment},
                {"Key": "Severity", "Value": "Critical"},
                {"Key": "Runbook", "Value": "https://docs.example.com/runbooks/high-cpu-utilization"},
            ],
        }

        if autoscaling_group:
            alarm_config["Dimensions"] = [{"Name": "AutoScalingGroupName", "Value": autoscaling_group}]

        self.cloudwatch.put_metric_alarm(**alarm_config)
        logger.info("✓ Created alarm: {alarm_name}")
        return alarm_name

    def create_high_memory_alarm(self, sns_topic_arn: str, threshold: float = 85.0) -> str:
        """
        Create alarm for high memory utilization (> 85%).

        Args:
            sns_topic_arn: SNS topic ARN for notifications
            threshold: Memory utilization threshold percentage

        Returns:
            Alarm name
        """
        alarm_name = f"{self.environment}-{self.service_name}-high-memory-utilization"

        self.cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator="GreaterThanThreshold",
            EvaluationPeriods=2,
            MetricName="mem_used_percent",
            Namespace="CWAgent",
            Period=300,
            Statistic="Average",
            Threshold=threshold,
            AlarmDescription=f"Alert when memory utilization exceeds {threshold}% for 10 minutes",
            AlarmActions=[sns_topic_arn],
            OKActions=[sns_topic_arn],
            TreatMissingData="notBreaching",
            Tags=[
                {"Key": "Environment", "Value": self.environment},
                {"Key": "Severity", "Value": "Warning"},
                {"Key": "Runbook", "Value": "https://docs.example.com/runbooks/high-memory-utilization"},
            ],
        )

        logger.info("✓ Created alarm: {alarm_name}")
        return alarm_name

    def create_high_disk_alarm(self, sns_topic_arn: str, threshold: float = 90.0) -> str:
        """
        Create alarm for high disk utilization (> 90%).

        Args:
            sns_topic_arn: SNS topic ARN for notifications
            threshold: Disk utilization threshold percentage

        Returns:
            Alarm name
        """
        alarm_name = f"{self.environment}-{self.service_name}-high-disk-utilization"

        self.cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator="GreaterThanThreshold",
            EvaluationPeriods=1,
            MetricName="disk_used_percent",
            Namespace="CWAgent",
            Period=300,
            Statistic="Average",
            Threshold=threshold,
            AlarmDescription=f"Alert when disk utilization exceeds {threshold}%",
            AlarmActions=[sns_topic_arn],
            OKActions=[sns_topic_arn],
            TreatMissingData="notBreaching",
            Tags=[
                {"Key": "Environment", "Value": self.environment},
                {"Key": "Severity", "Value": "Warning"},
                {"Key": "Runbook", "Value": "https://docs.example.com/runbooks/high-disk-utilization"},
            ],
        )

        logger.info("✓ Created alarm: {alarm_name}")
        return alarm_name

    def create_all_alarms(self, email: str | None = None, autoscaling_group: str | None = None) -> list[str]:
        """
        Create all CloudWatch alarms.

        Args:
            email: Optional email address for notifications
            autoscaling_group: Optional Auto Scaling Group name

        Returns:
            List of created alarm names
        """
        logger.info("\nCreating CloudWatch alarms for {self.environment} environment...")
        logger.info("Region: {self.region}")
        logger.info("Service: {self.service_name}\n")

        # Create SNS topic
        sns_topic_arn = self.create_sns_topic(email)
        logger.info()

        # Create alarms
        alarm_names = []
        alarm_names.append(self.create_high_error_rate_alarm(sns_topic_arn))
        alarm_names.append(self.create_high_response_time_alarm(sns_topic_arn))
        alarm_names.append(self.create_high_cpu_alarm(sns_topic_arn, autoscaling_group=autoscaling_group))
        alarm_names.append(self.create_high_memory_alarm(sns_topic_arn))
        alarm_names.append(self.create_high_disk_alarm(sns_topic_arn))

        logger.info("\n✓ Successfully created {len(alarm_names)} alarms")
        return alarm_names

    def list_alarms(self, prefix: str | None = None) -> list[dict]:
        """
        List all CloudWatch alarms.

        Args:
            prefix: Optional alarm name prefix filter

        Returns:
            List of alarm details
        """
        try:
            if prefix:
                response = self.cloudwatch.describe_alarms(AlarmNamePrefix=prefix, MaxRecords=100)
            else:
                response = self.cloudwatch.describe_alarms(MaxRecords=100)

            alarms = response.get("MetricAlarms", [])

            if not alarms:
                logger.info("No alarms found")
                return []

            logger.info("\nFound {len(alarms)} alarm(s):\n")
            for alarm in alarms:
                state = alarm["StateValue"]
                {"OK": "✓", "ALARM": "✗", "INSUFFICIENT_DATA": "?"}.get(state, "-")

                logger.info("{state_emoji} {alarm['AlarmName']}")
                logger.info("  State: {state}")
                logger.info("  Description: {alarm.get('AlarmDescription', 'N/A')}")
                logger.info("  Threshold: {alarm.get('Threshold', 'N/A')}")
                logger.info()

            return alarms

        except ClientError:
            logger.info("Error listing alarms: {e}")
            return []

    def describe_alarm(self, alarm_name: str) -> dict | None:
        """
        Get detailed information about a specific alarm.

        Args:
            alarm_name: Name of the alarm

        Returns:
            Alarm details or None if not found
        """
        try:
            response = self.cloudwatch.describe_alarms(AlarmNames=[alarm_name])
            alarms = response.get("MetricAlarms", [])

            if not alarms:
                logger.info("Alarm not found: {alarm_name}")
                return None

            alarm = alarms[0]
            logger.info("\nAlarm Details: {alarm_name}\n")
            logger.info(str(json.dumps(alarm, indent=2, default=str)))
            return alarm

        except ClientError:
            logger.info("Error describing alarm: {e}")
            return None

    def delete_alarm(self, alarm_name: str) -> bool:
        """
        Delete a CloudWatch alarm.

        Args:
            alarm_name: Name of the alarm to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cloudwatch.delete_alarms(AlarmNames=[alarm_name])
            logger.info("✓ Deleted alarm: {alarm_name}")
            return True

        except ClientError:
            logger.info("Error deleting alarm: {e}")
            return False

    def test_alarm(self, alarm_name: str) -> bool:
        """
        Test an alarm by setting it to ALARM state.

        Args:
            alarm_name: Name of the alarm to test

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cloudwatch.set_alarm_state(
                AlarmName=alarm_name,
                StateValue="ALARM",
                StateReason="Testing alarm notification",
                StateReasonData=json.dumps({"test": True, "message": "This is a test alarm notification"}),
            )
            logger.info("✓ Set alarm to ALARM state: {alarm_name}")
            logger.info("  Check your notification channels for the test alert")
            return True

        except ClientError:
            logger.info("Error testing alarm: {e}")
            return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Manage CloudWatch alarms for AI Reviewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create all alarms
  python manage_cloudwatch_alarms.py create-all --region us-east-1 --environment prod --email ops@example.com

  # List all alarms
  python manage_cloudwatch_alarms.py list --region us-east-1

  # Describe specific alarm
  python manage_cloudwatch_alarms.py describe --alarm-name prod-ai-reviewer-high-error-rate

  # Test alarm notification
  python manage_cloudwatch_alarms.py test --alarm-name prod-ai-reviewer-high-error-rate

  # Delete alarm
  python manage_cloudwatch_alarms.py delete --alarm-name test-alarm
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create-all command
    create_parser = subparsers.add_parser("create-all", help="Create all CloudWatch alarms")
    create_parser.add_argument("--region", required=True, help="AWS region")
    create_parser.add_argument("--environment", default="prod", help="Environment (dev/staging/prod)")
    create_parser.add_argument("--service-name", default="ai-reviewer", help="Service name")
    create_parser.add_argument("--email", help="Email address for notifications")
    create_parser.add_argument("--autoscaling-group", help="Auto Scaling Group name")

    # List command
    list_parser = subparsers.add_parser("list", help="List all CloudWatch alarms")
    list_parser.add_argument("--region", required=True, help="AWS region")
    list_parser.add_argument("--prefix", help="Alarm name prefix filter")

    # Describe command
    describe_parser = subparsers.add_parser("describe", help="Describe a specific alarm")
    describe_parser.add_argument("--region", required=True, help="AWS region")
    describe_parser.add_argument("--alarm-name", required=True, help="Alarm name")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a CloudWatch alarm")
    delete_parser.add_argument("--region", required=True, help="AWS region")
    delete_parser.add_argument("--alarm-name", required=True, help="Alarm name")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test alarm notification")
    test_parser.add_argument("--region", required=True, help="AWS region")
    test_parser.add_argument("--alarm-name", required=True, help="Alarm name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "create-all":
            manager = CloudWatchAlarmsManager(
                region=args.region, environment=args.environment, service_name=args.service_name
            )
            manager.create_all_alarms(email=args.email, autoscaling_group=args.autoscaling_group)

        elif args.command == "list":
            manager = CloudWatchAlarmsManager(region=args.region)
            manager.list_alarms(prefix=args.prefix)

        elif args.command == "describe":
            manager = CloudWatchAlarmsManager(region=args.region)
            manager.describe_alarm(args.alarm_name)

        elif args.command == "delete":
            manager = CloudWatchAlarmsManager(region=args.region)
            manager.delete_alarm(args.alarm_name)

        elif args.command == "test":
            manager = CloudWatchAlarmsManager(region=args.region)
            manager.test_alarm(args.alarm_name)

    except NoCredentialsError:
        logger.info("\nError: AWS credentials not found")
        logger.info("Configure credentials using one of these methods:")
        logger.info("  1. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        logger.info("  2. AWS credentials file: ~/.aws/credentials")
        logger.info("  3. IAM role (if running on EC2)")
        sys.exit(1)

    except ClientError:
        logger.info("\nAWS Error: {e}")
        sys.exit(1)

    except Exception:
        logger.info("\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
