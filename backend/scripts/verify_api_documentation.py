import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Verify API documentation setup.

This script verifies that:
1. Swagger UI is accessible at /docs
2. ReDoc is accessible at /redoc
3. OpenAPI spec includes authentication examples
4. Security schemes are properly configured

Usage:
    python scripts/verify_api_documentation.py [--url URL]

Requirements:
    - Backend server must be running
    - requests library must be installed
"""
import argparse
import sys

import requests


def check_endpoint(url: str, endpoint: str, expected_content: list[str]) -> bool:
    """
    Check if an endpoint is accessible and contains expected content.

    Args:
        url: Base URL of the API
        endpoint: Endpoint path to check
        expected_content: List of strings that should be in the response

    Returns:
        True if all checks pass, False otherwise
    """
    full_url = f"{url}{endpoint}"
    logger.info("\n🔍 Checking {full_url}...")

    try:
        response = requests.get(full_url, timeout=10)

        if response.status_code != 200:
            logger.info("   ❌ Failed: HTTP {response.status_code}")
            return False

        logger.info("   ✅ Accessible (HTTP {response.status_code})")

        # Check content
        content = response.text.lower()
        missing_content = []

        for expected in expected_content:
            if expected.lower() not in content:
                missing_content.append(expected)

        if missing_content:
            logger.info("   ⚠️  Missing expected content:")
            for _item in missing_content:
                logger.info("      - {item}")
            return False

        logger.info("   ✅ Contains all expected content")
        return True

    except requests.exceptions.RequestException:
        logger.info("   ❌ Request failed: {e}")
        return False


def check_openapi_spec(url: str) -> bool:
    """
    Check OpenAPI specification for completeness.

    Args:
        url: Base URL of the API

    Returns:
        True if all checks pass, False otherwise
    """
    spec_url = f"{url}/api/v1/openapi.json"
    logger.info("\n🔍 Checking OpenAPI spec at {spec_url}...")

    try:
        response = requests.get(spec_url, timeout=10)

        if response.status_code != 200:
            logger.info("   ❌ Failed: HTTP {response.status_code}")
            return False

        spec = response.json()
        logger.info("   ✅ OpenAPI spec accessible")

        # Check basic structure
        checks_passed = True

        # Check info section
        if "info" not in spec:
            logger.info("   ❌ Missing 'info' section")
            checks_passed = False
        else:
            info = spec["info"]
            if "title" in info:
                logger.info("   ✅ Title: {info['title']}")
            else:
                logger.info("   ❌ Missing title")
                checks_passed = False

            if "version" in info:
                logger.info("   ✅ Version: {info['version']}")
            else:
                logger.info("   ❌ Missing version")
                checks_passed = False

            if "description" in info and info["description"]:
                desc = info["description"]
                logger.info("   ✅ Description: {len(desc)} characters")

                # Check for authentication documentation
                auth_keywords = ["authentication", "bearer", "authorization", "jwt", "token"]
                found_keywords = [kw for kw in auth_keywords if kw.lower() in desc.lower()]

                if found_keywords:
                    logger.info("   ✅ Authentication documented (found: {', '.join(found_keywords)})")
                else:
                    logger.info("   ⚠️  Authentication documentation may be incomplete")

                # Check for examples
                if "curl" in desc.lower() or "example" in desc.lower():
                    logger.info("   ✅ Includes examples")
                else:
                    logger.info("   ⚠️  No examples found")

                # Check for Swagger UI instructions
                if "swagger" in desc.lower() and "authorize" in desc.lower():
                    logger.info("   ✅ Includes Swagger UI usage instructions")
                else:
                    logger.info("   ⚠️  Swagger UI instructions not found")
            else:
                logger.info("   ❌ Missing or empty description")
                checks_passed = False

        # Check security schemes
        if "components" in spec and "securitySchemes" in spec["components"]:
            schemes = spec["components"]["securitySchemes"]
            logger.info("   ✅ Security schemes defined: {', '.join(schemes.keys())}")

            if "HTTPBearer" in schemes:
                bearer = schemes["HTTPBearer"]
                if bearer.get("type") == "http" and bearer.get("scheme") == "bearer":
                    logger.info("   ✅ HTTPBearer properly configured")
                else:
                    logger.info("   ⚠️  HTTPBearer configuration may be incorrect")
                    checks_passed = False
        else:
            logger.info("   ❌ No security schemes defined")
            checks_passed = False

        # Check paths
        if "paths" in spec:
            len(spec["paths"])
            logger.info("   ✅ Endpoints documented: {path_count}")

            # Count protected endpoints
            protected_count = 0
            for _path, methods in spec["paths"].items():
                for _method, details in methods.items():
                    if "security" in details:
                        protected_count += 1

            logger.info("   ✅ Protected endpoints: {protected_count}")
        else:
            logger.info("   ❌ No paths defined")
            checks_passed = False

        # Check tags
        if "tags" in spec:
            len(spec["tags"])
            logger.info("   ✅ Tags defined: {tag_count}")
        else:
            logger.info("   ⚠️  No tags defined")

        # Check contact info
        if "contact" in spec.get("info", {}):
            contact = spec["info"]["contact"]
            if "name" in contact and "email" in contact:
                logger.info("   ✅ Contact info: {contact['name']} ({contact['email']})")
            else:
                logger.info("   ⚠️  Incomplete contact info")
        else:
            logger.info("   ⚠️  No contact info")

        # Check license
        if "license" in spec.get("info", {}):
            license_info = spec["info"]["license"]
            if "name" in license_info:
                logger.info("   ✅ License: {license_info['name']}")
            else:
                logger.info("   ⚠️  Incomplete license info")
        else:
            logger.info("   ⚠️  No license info")

        return checks_passed

    except requests.exceptions.RequestException:
        logger.info("   ❌ Request failed: {e}")
        return False
    except Exception:
        logger.info("   ❌ Error parsing spec: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify API documentation setup")
    parser.add_argument(
        "--url", type=str, default="http://localhost:8000", help="Base URL of the API (default: http://localhost:8000)"
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("API Documentation Verification")
    logger.info("=" * 70)
    logger.info("\nTarget URL: {args.url}")

    all_checks_passed = True

    # Check Swagger UI
    swagger_checks = check_endpoint(args.url, "/docs", ["swagger", "openapi"])
    all_checks_passed = all_checks_passed and swagger_checks

    # Check ReDoc
    redoc_checks = check_endpoint(args.url, "/redoc", ["redoc", "openapi"])
    all_checks_passed = all_checks_passed and redoc_checks

    # Check OpenAPI spec
    spec_checks = check_openapi_spec(args.url)
    all_checks_passed = all_checks_passed and spec_checks

    # Summary
    logger.info("\n" + "=" * 70)
    if all_checks_passed:
        logger.info("✅ All checks passed!")
        logger.info("\n📖 Documentation is accessible at:")
        logger.info("   Swagger UI: {args.url}/docs")
        logger.info("   ReDoc:      {args.url}/redoc")
        logger.info("   OpenAPI:    {args.url}/api/v1/openapi.json")
        logger.info("\n💡 To use authentication in Swagger UI:")
        logger.info("   1. Click the 'Authorize' button")
        logger.info("   2. Enter your JWT token (get it from /api/v1/auth/login)")
        logger.info("   3. Click 'Authorize' to apply")
        return 0
    else:
        logger.info("❌ Some checks failed")
        logger.info("\n⚠️  Please ensure:")
        logger.info("   1. The backend server is running")
        logger.info("   2. The server is accessible at the specified URL")
        logger.info("   3. All required configuration is in place")
        return 1


if __name__ == "__main__":
    sys.exit(main())
