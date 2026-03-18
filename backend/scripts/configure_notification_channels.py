import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
CloudWatch Notification Channels Configuration Script

This script helps configure and test notification channels for CloudWatch alarms.
Supports email and Slack notifications via Amazon SNS.

Usage:
    # Configure email notification
    python configure_notification_channels.py setup-email \\
        --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts \\
        --email ops-team@example.com

    # Configure Slack notification
    python configure_notification_channels.py setup-slack \\
        --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts \\
        --webhook-url https://hooks.slack.com/services/T00/B00/XXX

    # Test notifications
    python configure_notification_channels.py test \\
        --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts

    # List subscriptions
    python configure_notification_channels.py list \\
        --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts

    # Verify configuration
    python configure_notification_channels.py verify \\
        --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts

Requirements:
    - boto3
    - AWS credentials configured
    - SNS topic already created
"""

import argparse
import sys
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    logger.info("❌ Error: boto3 is not installed")
    logger.info("Install it with: pip install boto3")
    sys.exit(1)


class NotificationChannelManager:
    """Manages CloudWatch notification channels via SNS"""

    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the notification channel manager.

        Args:
            region: AWS region
        """
        self.region = region
        try:
            self.sns_client = boto3.client("sns", region_name=region)
            self.cloudwatch_client = boto3.client("cloudwatch", region_name=region)
        except NoCredentialsError:
            logger.info("❌ Error: AWS credentials not configured")
            logger.info("Configure credentials with: aws configure")
            sys.exit(1)

    def setup_email_subscription(self, topic_arn: str, email: str) -> dict[str, str]:
        """
        Set up email subscription to SNS topic.

        Args:
            topic_arn: ARN of the SNS topic
            email: Email address to subscribe

        Returns:
            Dictionary with subscription details
        """
        try:
            logger.info("📧 Setting up email subscription for: {email}")

            # Check if subscription already exists
            existing = self._get_subscription_by_endpoint(topic_arn, email)
            if existing:
                logger.info("ℹ️  Email subscription already exists")
                logger.info("   Subscription ARN: {existing['SubscriptionArn']}")
                if existing["SubscriptionArn"] == "PendingConfirmation":
                    logger.info("⚠️  Subscription pending confirmation - check email inbox")
                else:
                    logger.info("✅ Subscription confirmed and active")
                return existing

            # Create new subscription
            response = self.sns_client.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email)

            subscription_arn = response["SubscriptionArn"]

            logger.info("✅ Email subscription created successfully")
            logger.info("   Subscription ARN: {subscription_arn}")
            logger.info("   Status: Pending confirmation")
            logger.info()
            logger.info("📬 IMPORTANT: Check your email inbox!")
            logger.info("   1. Look for email from: AWS Notifications")
            logger.info("   2. Subject: AWS Notification - Subscription Confirmation")
            logger.info("   3. Click 'Confirm subscription' link")
            logger.info("   4. Subscription expires in 3 days if not confirmed")
            logger.info()
            logger.info("💡 Tip: Check spam/junk folder if email not received")

            return {
                "SubscriptionArn": subscription_arn,
                "Protocol": "email",
                "Endpoint": email,
                "Status": "PendingConfirmation",
            }

        except ClientError:
            logger.info("❌ Error setting up email subscription: {e}")
            raise

    def setup_slack_subscription(self, topic_arn: str, webhook_url: str) -> dict[str, str]:
        """
        Set up Slack webhook subscription to SNS topic.

        Args:
            topic_arn: ARN of the SNS topic
            webhook_url: Slack webhook URL

        Returns:
            Dictionary with subscription details
        """
        try:
            logger.info("💬 Setting up Slack subscription")

            # Validate webhook URL
            if not webhook_url.startswith("https://hooks.slack.com/"):
                logger.info("⚠️  Warning: Webhook URL doesn't look like a Slack webhook")
                logger.info("   Expected format: https://hooks.slack.com/services/T00/B00/XXX")

            # Check if subscription already exists
            existing = self._get_subscription_by_endpoint(topic_arn, webhook_url)
            if existing:
                logger.info("ℹ️  Slack subscription already exists")
                logger.info("   Subscription ARN: {existing['SubscriptionArn']}")
                logger.info("✅ Subscription active (HTTPS subscriptions auto-confirm)")
                return existing

            # Create new subscription
            response = self.sns_client.subscribe(TopicArn=topic_arn, Protocol="https", Endpoint=webhook_url)

            subscription_arn = response["SubscriptionArn"]

            logger.info("✅ Slack subscription created successfully")
            logger.info("   Subscription ARN: {subscription_arn}")
            logger.info("   Status: Active (HTTPS subscriptions auto-confirm)")
            logger.info()
            logger.info("💡 Tip: Test the subscription with:")
            logger.info("   python {sys.argv[0]} test --topic-arn {topic_arn}")

            return {
                "SubscriptionArn": subscription_arn,
                "Protocol": "https",
                "Endpoint": webhook_url,
                "Status": "Active",
            }

        except ClientError:
            logger.info("❌ Error setting up Slack subscription: {e}")
            raise

    def list_subscriptions(self, topic_arn: str) -> list[dict]:
        """
        List all subscriptions for a topic.

        Args:
            topic_arn: ARN of the SNS topic

        Returns:
            List of subscription dictionaries
        """
        try:
            logger.info("📋 Listing subscriptions for topic:")
            logger.info("   {topic_arn}")
            logger.info()

            response = self.sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)

            subscriptions = response.get("Subscriptions", [])

            if not subscriptions:
                logger.info("ℹ️  No subscriptions found")
                return []

            logger.info("Found {len(subscriptions)} subscription(s):")
            logger.info()

            for _i, sub in enumerate(subscriptions, 1):
                protocol = sub["Protocol"]
                endpoint = sub["Endpoint"]
                sub_arn = sub["SubscriptionArn"]

                # Determine status
                if sub_arn == "PendingConfirmation":
                    pass
                else:
                    pass

                # Format endpoint for display
                if protocol == "email":
                    pass
                elif protocol == "https":
                    # Mask webhook URL for security
                    if "hooks.slack.com" in endpoint:
                        pass
                    else:
                        f"{endpoint[:30]}..."
                else:
                    pass

                logger.info("{i}. {protocol.upper()} Subscription")
                logger.info("   Endpoint: {display_endpoint}")
                logger.info("   Status: {status}")
                logger.info("   ARN: {sub_arn}")
                logger.info()

            return subscriptions

        except ClientError:
            logger.info("❌ Error listing subscriptions: {e}")
            raise

    def test_notification(self, topic_arn: str, message: str | None = None) -> bool:
        """
        Send a test notification to all subscribers.

        Args:
            topic_arn: ARN of the SNS topic
            message: Custom test message (optional)

        Returns:
            True if successful
        """
        try:
            if message is None:
                message = (
                    f"🧪 Test notification from CloudWatch Alarms\n\n"
                    f"This is a test message to verify notification channels are working.\n"
                    f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n"
                    f"If you received this message, your notification channel is configured correctly!"
                )

            logger.info("🧪 Sending test notification...")
            logger.info("   Topic: {topic_arn}")
            logger.info()

            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Subject="TEST: CloudWatch Alarm Notification",
                Message=message,
            )

            response["MessageId"]

            logger.info("✅ Test notification sent successfully")
            logger.info("   Message ID: {message_id}")
            logger.info()
            logger.info("📬 Check your notification channels:")
            logger.info("   • Email: Check inbox (and spam folder)")
            logger.info("   • Slack: Check configured channel")
            logger.info()
            logger.info("⏱️  Notifications should arrive within 1 minute")

            return True

        except ClientError:
            logger.info("❌ Error sending test notification: {e}")
            raise

    def verify_configuration(self, topic_arn: str) -> dict[str, any]:
        """
        Verify notification channel configuration.

        Args:
            topic_arn: ARN of the SNS topic

        Returns:
            Dictionary with verification results
        """
        logger.info("🔍 Verifying notification channel configuration...")
        logger.info()

        results = {
            "topic_exists": False,
            "email_configured": False,
            "email_confirmed": False,
            "slack_configured": False,
            "total_subscriptions": 0,
            "issues": [],
        }

        try:
            # Check if topic exists
            try:
                self.sns_client.get_topic_attributes(TopicArn=topic_arn)
                results["topic_exists"] = True
                logger.info("✅ SNS topic exists")
            except ClientError:
                results["issues"].append("SNS topic not found")
                logger.info("❌ SNS topic not found")
                return results

            # List subscriptions
            response = self.sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
            subscriptions = response.get("Subscriptions", [])
            results["total_subscriptions"] = len(subscriptions)

            if not subscriptions:
                results["issues"].append("No subscriptions configured")
                logger.info("⚠️  No subscriptions configured")
                logger.info()
                logger.info("💡 Configure notifications with:")
                logger.info("   python {sys.argv[0]} setup-email --topic-arn {topic_arn} --email YOUR_EMAIL")
                logger.info("   python {sys.argv[0]} setup-slack --topic-arn {topic_arn} --webhook-url YOUR_WEBHOOK")
                return results

            # Check each subscription
            for sub in subscriptions:
                protocol = sub["Protocol"]
                sub_arn = sub["SubscriptionArn"]

                if protocol == "email":
                    results["email_configured"] = True
                    if sub_arn != "PendingConfirmation":
                        results["email_confirmed"] = True
                        logger.info("✅ Email subscription active: {sub['Endpoint']}")
                    else:
                        results["issues"].append("Email subscription pending confirmation")
                        logger.info("⚠️  Email subscription pending: {sub['Endpoint']}")
                        logger.info("   Check email inbox and confirm subscription")

                elif protocol == "https":
                    results["slack_configured"] = True
                    logger.info("✅ Slack subscription active")

            # Summary
            logger.info()
            logger.info("📊 Configuration Summary:")
            logger.info("   Total subscriptions: {results['total_subscriptions']}")
            logger.info("   Email configured: {'✅' if results['email_configured'] else '❌'}")
            logger.info("   Email confirmed: {'✅' if results['email_confirmed'] else '❌'}")
            logger.info("   Slack configured: {'✅' if results['slack_configured'] else '❌'}")

            if results["issues"]:
                logger.info()
                logger.info("⚠️  Issues found:")
                for _issue in results["issues"]:
                    logger.info("   • {issue}")
            else:
                logger.info()
                logger.info("✅ All notification channels configured correctly!")

            return results

        except ClientError:
            logger.info("❌ Error verifying configuration: {e}")
            raise

    def _get_subscription_by_endpoint(self, topic_arn: str, endpoint: str) -> dict | None:
        """
        Get subscription by endpoint.

        Args:
            topic_arn: ARN of the SNS topic
            endpoint: Subscription endpoint

        Returns:
            Subscription dictionary or None
        """
        try:
            response = self.sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
            subscriptions = response.get("Subscriptions", [])

            for sub in subscriptions:
                if sub["Endpoint"] == endpoint:
                    return sub

            return None

        except ClientError:
            return None


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Configure and test CloudWatch notification channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set up email notification
  %(prog)s setup-email \\
    --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts \\
    --email ops-team@example.com

  # Set up Slack notification
  %(prog)s setup-slack \\
    --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts \\
    --webhook-url https://hooks.slack.com/services/T00/B00/XXX

  # Test notifications
  %(prog)s test \\
    --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts

  # List subscriptions
  %(prog)s list \\
    --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts

  # Verify configuration
  %(prog)s verify \\
    --topic-arn arn:aws:sns:us-east-1:123456789012:prod-ai-reviewer-alerts
        """,
    )

    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # setup-email command
    setup_email_parser = subparsers.add_parser("setup-email", help="Set up email notification")
    setup_email_parser.add_argument("--topic-arn", required=True, help="SNS topic ARN")
    setup_email_parser.add_argument("--email", required=True, help="Email address to subscribe")

    # setup-slack command
    setup_slack_parser = subparsers.add_parser("setup-slack", help="Set up Slack notification")
    setup_slack_parser.add_argument("--topic-arn", required=True, help="SNS topic ARN")
    setup_slack_parser.add_argument("--webhook-url", required=True, help="Slack webhook URL")

    # list command
    list_parser = subparsers.add_parser("list", help="List all subscriptions")
    list_parser.add_argument("--topic-arn", required=True, help="SNS topic ARN")

    # test command
    test_parser = subparsers.add_parser("test", help="Send test notification")
    test_parser.add_argument("--topic-arn", required=True, help="SNS topic ARN")
    test_parser.add_argument("--message", help="Custom test message (optional)")

    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify notification configuration")
    verify_parser.add_argument("--topic-arn", required=True, help="SNS topic ARN")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize manager
    manager = NotificationChannelManager(region=args.region)

    try:
        # Execute command
        if args.command == "setup-email":
            manager.setup_email_subscription(args.topic_arn, args.email)

        elif args.command == "setup-slack":
            manager.setup_slack_subscription(args.topic_arn, args.webhook_url)

        elif args.command == "list":
            manager.list_subscriptions(args.topic_arn)

        elif args.command == "test":
            manager.test_notification(args.topic_arn, args.message)

        elif args.command == "verify":
            results = manager.verify_configuration(args.topic_arn)
            # Exit with error code if issues found
            if results["issues"]:
                sys.exit(1)

    except Exception:
        logger.info("\n❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
