import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Script to set up secrets in AWS Secrets Manager.

This script helps initialize secrets for different environments:
- Database credentials (PostgreSQL, Neo4j, Redis)
- API keys (GitHub, OpenAI, Anthropic)
- Application secrets (JWT, encryption keys)

Usage:
    python scripts/setup_secrets_manager.py --environment production
    python scripts/setup_secrets_manager.py --environment staging --dry-run
"""
import argparse
import json
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError


def create_or_update_secret(
    client, secret_name: str, secret_value: dict[str, Any] | str, description: str = "", dry_run: bool = False
) -> bool:
    """
    Create or update a secret in AWS Secrets Manager.

    Args:
        client: Boto3 Secrets Manager client
        secret_name: Name of the secret
        secret_value: Secret value (dict will be JSON-encoded)
        description: Description of the secret
        dry_run: If True, only print what would be done

    Returns:
        True if successful, False otherwise
    """
    # Convert dict to JSON string
    if isinstance(secret_value, dict):
        secret_string = json.dumps(secret_value)
    else:
        secret_string = secret_value

    if dry_run:
        logger.info(f"[DRY RUN] Would create/update secret: {secret_name}")
        logger.info(f"  Description: {description}")
        display_value = f"  Value: {secret_string[:50]}..." if len(secret_string) > 50 else f"  Value: {secret_string}"
        logger.info(display_value)
        return True

    try:
        # Try to create the secret
        client.create_secret(Name=secret_name, Description=description, SecretString=secret_string)
        logger.info("✓ Created secret: {secret_name}")
        return True

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceExistsException":
            # Secret exists, update it
            try:
                client.update_secret(SecretId=secret_name, SecretString=secret_string)
                logger.info("✓ Updated secret: {secret_name}")
                return True
            except ClientError:
                logger.info("✗ Failed to update secret {secret_name}: {update_error}")
                return False
        else:
            logger.info("✗ Failed to create secret {secret_name}: {e}")
            return False


def setup_database_secrets(client, environment: str, dry_run: bool = False):
    """Set up database-related secrets."""
    logger.info("\n=== Setting up database secrets for {environment} ===")

    # PostgreSQL credentials
    postgres_secret = {
        "postgres_host": "REPLACE_WITH_RDS_ENDPOINT",
        "postgres_port": "5432",
        "postgres_db": f"ai_code_review_{environment}",
        "postgres_user": f"ai_review_user_{environment}",
        "postgres_password": "REPLACE_WITH_SECURE_PASSWORD",
    }

    create_or_update_secret(
        client,
        f"{environment}/database/postgresql",
        postgres_secret,
        f"PostgreSQL database credentials for {environment}",
        dry_run,
    )

    # Neo4j credentials
    neo4j_secret = {
        "neo4j_uri": "REPLACE_WITH_NEO4J_URI",
        "neo4j_user": "neo4j",
        "neo4j_password": "REPLACE_WITH_SECURE_PASSWORD",
    }

    create_or_update_secret(
        client,
        f"{environment}/database/neo4j",
        neo4j_secret,
        f"Neo4j graph database credentials for {environment}",
        dry_run,
    )

    # Redis credentials
    redis_secret = {
        "redis_host": "REPLACE_WITH_ELASTICACHE_ENDPOINT",
        "redis_port": "6379",
        "redis_password": "REPLACE_WITH_SECURE_PASSWORD",
    }

    create_or_update_secret(
        client, f"{environment}/database/redis", redis_secret, f"Redis cache credentials for {environment}", dry_run
    )


def setup_api_secrets(client, environment: str, dry_run: bool = False):
    """Set up external API secrets."""
    logger.info("\n=== Setting up API secrets for {environment} ===")

    # GitHub integration
    github_secret = {"github_token": "REPLACE_WITH_GITHUB_PAT", "github_webhook_secret": "REPLACE_WITH_WEBHOOK_SECRET"}

    create_or_update_secret(
        client,
        f"{environment}/integrations/github",
        github_secret,
        f"GitHub API credentials for {environment}",
        dry_run,
    )

    # OpenAI API
    create_or_update_secret(
        client,
        f"{environment}/integrations/openai_api_key",
        "REPLACE_WITH_OPENAI_API_KEY",
        f"OpenAI API key for {environment}",
        dry_run,
    )

    # Anthropic API
    create_or_update_secret(
        client,
        f"{environment}/integrations/anthropic_api_key",
        "REPLACE_WITH_ANTHROPIC_API_KEY",
        f"Anthropic Claude API key for {environment}",
        dry_run,
    )


def setup_app_secrets(client, environment: str, dry_run: bool = False):
    """Set up application secrets."""
    logger.info("\n=== Setting up application secrets for {environment} ===")

    # Application secrets
    app_secret = {
        "secret_key": "REPLACE_WITH_SECURE_RANDOM_STRING_MIN_32_CHARS",
        "jwt_secret": "REPLACE_WITH_SECURE_RANDOM_STRING_MIN_32_CHARS",
        "session_secret": "REPLACE_WITH_SECURE_RANDOM_STRING_MIN_32_CHARS",
        "encryption_key": "REPLACE_WITH_BASE64_ENCODED_32_BYTE_KEY",
        "kms_key_id": "REPLACE_WITH_AWS_KMS_KEY_ID",
    }

    create_or_update_secret(
        client, f"{environment}/app/secrets", app_secret, f"Application secrets for {environment}", dry_run
    )


def setup_frontend_secrets(client, environment: str, dry_run: bool = False):
    """Set up frontend secrets."""
    logger.info("\n=== Setting up frontend secrets for {environment} ===")

    # NextAuth secret
    create_or_update_secret(
        client,
        f"{environment}/frontend/nextauth_secret",
        "REPLACE_WITH_SECURE_RANDOM_STRING_MIN_32_CHARS",
        f"NextAuth secret for {environment}",
        dry_run,
    )

    # OAuth credentials
    oauth_secret = {
        "github_client_id": "REPLACE_WITH_GITHUB_OAUTH_CLIENT_ID",
        "github_client_secret": "REPLACE_WITH_GITHUB_OAUTH_CLIENT_SECRET",
        "google_client_id": "REPLACE_WITH_GOOGLE_OAUTH_CLIENT_ID",
        "google_client_secret": "REPLACE_WITH_GOOGLE_OAUTH_CLIENT_SECRET",
    }

    create_or_update_secret(
        client, f"{environment}/oauth/credentials", oauth_secret, f"OAuth credentials for {environment}", dry_run
    )


def setup_monitoring_secrets(client, environment: str, dry_run: bool = False):
    """Set up monitoring and observability secrets."""
    logger.info("\n=== Setting up monitoring secrets for {environment} ===")

    monitoring_secret = {"sentry_dsn": "REPLACE_WITH_SENTRY_DSN", "ga_tracking_id": "REPLACE_WITH_GA_TRACKING_ID"}

    create_or_update_secret(
        client,
        f"{environment}/monitoring/credentials",
        monitoring_secret,
        f"Monitoring credentials for {environment}",
        dry_run,
    )


def enable_secret_rotation(client, secret_name: str, lambda_arn: str, dry_run: bool = False):
    """
    Enable automatic secret rotation.

    Args:
        client: Boto3 Secrets Manager client
        secret_name: Name of the secret
        lambda_arn: ARN of the Lambda function for rotation
        dry_run: If True, only print what would be done
    """
    if dry_run:
        logger.info("[DRY RUN] Would enable rotation for: {secret_name}")
        return

    try:
        client.rotate_secret(
            SecretId=secret_name, RotationLambdaARN=lambda_arn, RotationRules={"AutomaticallyAfterDays": 30}
        )
        logger.info("✓ Enabled rotation for secret: {secret_name}")
    except ClientError:
        logger.info("✗ Failed to enable rotation for {secret_name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Set up secrets in AWS Secrets Manager")
    parser.add_argument(
        "--environment",
        required=True,
        choices=["development", "staging", "production"],
        help="Environment to set up secrets for",
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without making changes")
    parser.add_argument(
        "--enable-rotation", action="store_true", help="Enable automatic secret rotation (requires Lambda function)"
    )
    parser.add_argument("--rotation-lambda-arn", help="ARN of Lambda function for secret rotation")

    args = parser.parse_args()

    # Initialize AWS Secrets Manager client
    try:
        client = boto3.client("secretsmanager", region_name=args.region)
        logger.info("Connected to AWS Secrets Manager in region: {args.region}")
    except Exception:
        logger.info("Failed to connect to AWS Secrets Manager: {e}")
        sys.exit(1)

    # Set up secrets
    setup_database_secrets(client, args.environment, args.dry_run)
    setup_api_secrets(client, args.environment, args.dry_run)
    setup_app_secrets(client, args.environment, args.dry_run)
    setup_frontend_secrets(client, args.environment, args.dry_run)
    setup_monitoring_secrets(client, args.environment, args.dry_run)

    # Enable rotation if requested
    if args.enable_rotation:
        if not args.rotation_lambda_arn:
            logger.info("\n⚠ Warning: --rotation-lambda-arn required for rotation")
        else:
            logger.info("\n=== Enabling secret rotation ===")
            secrets_to_rotate = [
                f"{args.environment}/database/postgresql",
                f"{args.environment}/database/neo4j",
                f"{args.environment}/database/redis",
            ]
            for secret_name in secrets_to_rotate:
                enable_secret_rotation(client, secret_name, args.rotation_lambda_arn, args.dry_run)

    logger.info("\n" + "=" * 60)
    if args.dry_run:
        logger.info("DRY RUN COMPLETE - No changes were made")
    else:
        logger.info("SETUP COMPLETE")
        logger.info("\n⚠ IMPORTANT: Replace all placeholder values with actual secrets!")
        logger.info("   Use AWS Console or AWS CLI to update secret values.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
