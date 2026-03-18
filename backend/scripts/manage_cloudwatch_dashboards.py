import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
CloudWatch Dashboard Management Script

This script provides programmatic management of CloudWatch dashboards
for the AI-Based Reviewer system.

Features:
- Create/update dashboards using AWS SDK
- Validate dashboard configurations
- Export dashboard definitions
- List existing dashboards

Validates Requirements: 18.2
"""
import argparse
import json
import os
import sys

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.info("Warning: boto3 not installed. Install with: pip install boto3")


class CloudWatchDashboardManager:
    """
    Manager for CloudWatch dashboards.

    Validates Requirements: 18.2
    """

    def __init__(self, region: str = None, environment: str = None, service_name: str = None):
        """
        Initialize the dashboard manager.

        Args:
            region: AWS region (default: from AWS_REGION env var or us-east-1)
            environment: Environment name (default: from ENVIRONMENT env var or dev)
            service_name: Service name (default: from SERVICE_NAME env var or ai-reviewer)
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required. Install with: pip install boto3")

        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.environment = environment or os.getenv("ENVIRONMENT", "dev")
        self.service_name = service_name or os.getenv("SERVICE_NAME", "ai-reviewer")

        self.cloudwatch = boto3.client("cloudwatch", region_name=self.region)

    def create_system_health_dashboard(self) -> dict:
        """
        Create System Health dashboard with uptime, error rates, health checks, and active sessions.

        Validates Requirements: 18.2
        """
        dashboard_name = f"{self.environment}-{self.service_name}-system-health"

        dashboard_body = {
            "widgets": [
                # Uptime Percentage Widget
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/ApplicationELB", "HealthyHostCount", {"stat": "Average", "label": "Healthy Hosts"}],
                            [".", "UnHealthyHostCount", {"stat": "Average", "label": "Unhealthy Hosts"}],
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "System Uptime - Healthy vs Unhealthy Hosts",
                        "yAxis": {"left": {"min": 0}},
                    },
                    "width": 12,
                    "height": 6,
                    "x": 0,
                    "y": 0,
                },
                # Uptime Percentage Calculation
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [{"expression": "100 * (m1 / (m1 + m2))", "label": "Uptime %", "id": "e1"}],
                            ["AWS/ApplicationELB", "HealthyHostCount", {"id": "m1", "visible": False}],
                            [".", "UnHealthyHostCount", {"id": "m2", "visible": False}],
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "System Uptime Percentage (Target: 99.5%)",
                        "yAxis": {"left": {"min": 95, "max": 100}},
                        "annotations": {
                            "horizontal": [{"value": 99.5, "label": "SLA Target", "fill": "above", "color": "#2ca02c"}]
                        },
                    },
                    "width": 12,
                    "height": 6,
                    "x": 12,
                    "y": 0,
                },
                # Error Rate by Endpoint Widget
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [
                                self.service_name,
                                "http_errors_total",
                                "endpoint",
                                "/api/v1/projects",
                                {"stat": "Sum", "label": "Projects API"},
                            ],
                            ["...", "/api/v1/analysis", {"stat": "Sum", "label": "Analysis API"}],
                            ["...", "/api/v1/auth/login", {"stat": "Sum", "label": "Auth API"}],
                            ["...", "/api/v1/webhooks", {"stat": "Sum", "label": "Webhooks API"}],
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Error Count by Endpoint",
                        "yAxis": {"left": {"min": 0}},
                    },
                    "width": 12,
                    "height": 6,
                    "x": 0,
                    "y": 6,
                },
                # Error Rate Percentage
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [{"expression": "100 * (m1 / m2)", "label": "Error Rate %", "id": "e1"}],
                            [self.service_name, "http_errors_total", {"id": "m1", "stat": "Sum", "visible": False}],
                            [".", "http_requests_total", {"id": "m2", "stat": "Sum", "visible": False}],
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Overall Error Rate (Target: < 5%)",
                        "yAxis": {"left": {"min": 0, "max": 10}},
                        "annotations": {
                            "horizontal": [
                                {"value": 5, "label": "Alert Threshold", "fill": "above", "color": "#d62728"}
                            ]
                        },
                    },
                    "width": 12,
                    "height": 6,
                    "x": 12,
                    "y": 6,
                },
                # Health Check Status Widget
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/ApplicationELB", "TargetResponseTime", {"stat": "Average", "label": "Response Time"}],
                            ["...", {"stat": "p99", "label": "P99 Response Time"}],
                        ],
                        "period": 60,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Health Check Response Time",
                        "yAxis": {"left": {"min": 0}},
                        "annotations": {
                            "horizontal": [
                                {"value": 1, "label": "Alert Threshold (1s)", "fill": "above", "color": "#ff7f0e"}
                            ]
                        },
                    },
                    "width": 8,
                    "height": 6,
                    "x": 0,
                    "y": 12,
                },
                # Database Health Status
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [
                                self.service_name,
                                "database_connections_active",
                                "database",
                                "postgresql",
                                {"stat": "Average", "label": "PostgreSQL Connections"},
                            ],
                            ["...", "redis", {"stat": "Average", "label": "Redis Connections"}],
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Database Connection Health",
                        "yAxis": {"left": {"min": 0}},
                    },
                    "width": 8,
                    "height": 6,
                    "x": 8,
                    "y": 12,
                },
                # Active User Sessions Widget
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [self.service_name, "active_sessions", {"stat": "Average", "label": "Active Sessions"}]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Active User Sessions",
                        "yAxis": {"left": {"min": 0}},
                    },
                    "width": 8,
                    "height": 6,
                    "x": 16,
                    "y": 12,
                },
            ]
        }

        return self._put_dashboard(dashboard_name, dashboard_body)

    def create_performance_dashboard(self) -> dict:
        """
        Create Performance Metrics dashboard.

        Validates Requirements: 18.2
        """
        dashboard_name = f"{self.environment}-{self.service_name}-performance"

        dashboard_body = {
            "widgets": [
                # API Response Time
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [self.service_name, "http_request_duration_seconds", {"stat": "p50", "label": "P50"}],
                            ["...", {"stat": "p95", "label": "P95"}],
                            ["...", {"stat": "p99", "label": "P99"}],
                        ],
                        "period": 300,
                        "region": self.region,
                        "title": "API Response Time Percentiles (Target P95 < 500ms)",
                        "yAxis": {"left": {"min": 0}},
                        "annotations": {
                            "horizontal": [
                                {"value": 0.5, "label": "P95 Target (500ms)", "fill": "above", "color": "#ff7f0e"}
                            ]
                        },
                    },
                    "width": 12,
                    "height": 6,
                    "x": 0,
                    "y": 0,
                },
                # Database Query Performance
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [
                                self.service_name,
                                "database_query_duration_seconds",
                                "database",
                                "postgresql",
                                {"stat": "Average", "label": "PostgreSQL Avg"},
                            ],
                            ["...", {"stat": "p95", "label": "PostgreSQL P95"}],
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Database Query Performance",
                        "yAxis": {"left": {"min": 0}},
                    },
                    "width": 12,
                    "height": 6,
                    "x": 12,
                    "y": 0,
                },
                # Cache Hit Ratio
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [self.service_name, "cache_hit_ratio", {"stat": "Average", "label": "Cache Hit Ratio"}]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Cache Hit Ratio (Target: > 70%)",
                        "yAxis": {"left": {"min": 0, "max": 1}},
                        "annotations": {
                            "horizontal": [{"value": 0.7, "label": "Target", "fill": "below", "color": "#ff7f0e"}]
                        },
                    },
                    "width": 12,
                    "height": 6,
                    "x": 0,
                    "y": 6,
                },
            ]
        }

        return self._put_dashboard(dashboard_name, dashboard_body)

    def create_business_metrics_dashboard(self) -> dict:
        """
        Create Business Metrics dashboard.

        Validates Requirements: 18.2
        """
        dashboard_name = f"{self.environment}-{self.service_name}-business-metrics"

        dashboard_body = {
            "widgets": [
                # Analysis Completion Rate
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [
                                self.service_name,
                                "code_analysis_total",
                                "status",
                                "success",
                                {"stat": "Sum", "label": "Successful"},
                            ],
                            ["...", "error", {"stat": "Sum", "label": "Failed"}],
                        ],
                        "period": 3600,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Code Analysis Completion Rate",
                        "yAxis": {"left": {"min": 0}},
                    },
                    "width": 12,
                    "height": 6,
                    "x": 0,
                    "y": 0,
                },
                # User Activity
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [
                                self.service_name,
                                "auth_attempts_total",
                                "method",
                                "login",
                                "status",
                                "success",
                                {"stat": "Sum", "label": "Logins"},
                            ],
                            ["...", "register", "...", {"stat": "Sum", "label": "Registrations"}],
                        ],
                        "period": 3600,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "User Activity (Logins & Registrations)",
                        "yAxis": {"left": {"min": 0}},
                    },
                    "width": 12,
                    "height": 6,
                    "x": 12,
                    "y": 0,
                },
            ]
        }

        return self._put_dashboard(dashboard_name, dashboard_body)

    def _put_dashboard(self, dashboard_name: str, dashboard_body: dict) -> dict:
        """
        Create or update a CloudWatch dashboard.

        Args:
            dashboard_name: Name of the dashboard
            dashboard_body: Dashboard configuration

        Returns:
            Response from CloudWatch API
        """
        try:
            response = self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name, DashboardBody=json.dumps(dashboard_body)
            )

            logger.info("✓ Successfully created/updated dashboard: {dashboard_name}")
            logger.info(
                "  URL: https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={dashboard_name}"
            )

            return response

        except ClientError as e:
            e.response.get("Error", {}).get("Code", "Unknown")
            logger.info("✗ Failed to create dashboard {dashboard_name}: {error_code}")
            logger.info("  Error: {str(e)}")
            raise

    def list_dashboards(self) -> list[dict]:
        """
        List all CloudWatch dashboards.

        Returns:
            List of dashboard information
        """
        try:
            response = self.cloudwatch.list_dashboards()
            dashboards = response.get("DashboardEntries", [])

            logger.info("\nFound {len(dashboards)} CloudWatch dashboards:")
            for _dashboard in dashboards:
                logger.info("  - {dashboard['DashboardName']}")

            return dashboards

        except ClientError:
            logger.info("✗ Failed to list dashboards: {str(e)}")
            raise

    def get_dashboard(self, dashboard_name: str) -> dict:
        """
        Get dashboard configuration.

        Args:
            dashboard_name: Name of the dashboard

        Returns:
            Dashboard configuration
        """
        try:
            response = self.cloudwatch.get_dashboard(DashboardName=dashboard_name)
            return json.loads(response["DashboardBody"])

        except ClientError:
            logger.info("✗ Failed to get dashboard {dashboard_name}: {str(e)}")
            raise

    def delete_dashboard(self, dashboard_name: str) -> dict:
        """
        Delete a CloudWatch dashboard.

        Args:
            dashboard_name: Name of the dashboard

        Returns:
            Response from CloudWatch API
        """
        try:
            response = self.cloudwatch.delete_dashboards(DashboardNames=[dashboard_name])

            logger.info("✓ Successfully deleted dashboard: {dashboard_name}")
            return response

        except ClientError:
            logger.info("✗ Failed to delete dashboard {dashboard_name}: {str(e)}")
            raise

    def create_all_dashboards(self) -> None:
        """
        Create all dashboards (System Health, Performance, Business Metrics).

        Validates Requirements: 18.2
        """
        logger.info("\nCreating CloudWatch dashboards for {self.environment} environment...")
        logger.info("Region: {self.region}")
        logger.info("Service: {self.service_name}\n")

        self.create_system_health_dashboard()
        self.create_performance_dashboard()
        self.create_business_metrics_dashboard()

        logger.info("\n✓ All dashboards created successfully!")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Manage CloudWatch dashboards for AI-Based Reviewer")

    parser.add_argument("action", choices=["create", "list", "get", "delete", "create-all"], help="Action to perform")

    parser.add_argument("--dashboard", help="Dashboard name (for get/delete actions)")

    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "us-east-1"),
        help="AWS region (default: AWS_REGION env var or us-east-1)",
    )

    parser.add_argument(
        "--environment",
        default=os.getenv("ENVIRONMENT", "dev"),
        help="Environment name (default: ENVIRONMENT env var or dev)",
    )

    parser.add_argument(
        "--service-name",
        default=os.getenv("SERVICE_NAME", "ai-reviewer"),
        help="Service name (default: SERVICE_NAME env var or ai-reviewer)",
    )

    args = parser.parse_args()

    if not BOTO3_AVAILABLE:
        logger.info("Error: boto3 is not installed. Install with: pip install boto3")
        sys.exit(1)

    try:
        manager = CloudWatchDashboardManager(
            region=args.region, environment=args.environment, service_name=args.service_name
        )

        if args.action == "create-all":
            manager.create_all_dashboards()

        elif args.action == "create":
            if not args.dashboard:
                logger.info("Error: --dashboard is required for create action")
                sys.exit(1)

            if "health" in args.dashboard.lower():
                manager.create_system_health_dashboard()
            elif "performance" in args.dashboard.lower():
                manager.create_performance_dashboard()
            elif "business" in args.dashboard.lower():
                manager.create_business_metrics_dashboard()
            else:
                logger.info("Error: Unknown dashboard type: {args.dashboard}")
                sys.exit(1)

        elif args.action == "list":
            manager.list_dashboards()

        elif args.action == "get":
            if not args.dashboard:
                logger.info("Error: --dashboard is required for get action")
                sys.exit(1)

            config = manager.get_dashboard(args.dashboard)
            logger.info(str(json.dumps(config, indent=2)))

        elif args.action == "delete":
            if not args.dashboard:
                logger.info("Error: --dashboard is required for delete action")
                sys.exit(1)

            manager.delete_dashboard(args.dashboard)

    except NoCredentialsError:
        logger.info("Error: AWS credentials not found. Configure with 'aws configure'")
        sys.exit(1)

    except Exception:
        logger.info("Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
