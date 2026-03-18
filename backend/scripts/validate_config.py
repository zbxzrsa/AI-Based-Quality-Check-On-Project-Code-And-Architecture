#!/usr/bin/env python3
"""
Configuration Validation CLI Tool

Command-line tool to validate environment configuration for backend-frontend
connectivity. Provides detailed validation reports and supports different
validation modes.

Usage:
    python backend/scripts/validate_config.py [options]

Options:
    --mode MODE         Validation mode: all, required, ports, urls (default: all)
    --verbose, -v       Enable verbose output
    --json              Output results in JSON format
    --help, -h          Show this help message

Examples:
    # Validate all configuration
    python backend/scripts/validate_config.py

    # Validate only required variables
    python backend/scripts/validate_config.py --mode required

    # Validate with verbose output
    python backend/scripts/validate_config.py --verbose

    # Output as JSON
    python backend/scripts/validate_config.py --json

Validates Requirements: 10.1, 10.5
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config_validator import ConfigValidator, ValidationResult


def setup_logging(verbose: bool = False) -> None:
    """
    Setup logging configuration.

    Args:
        verbose: Enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def validate_configuration(mode: str = "all", verbose: bool = False) -> int:
    """
    Validate configuration and return exit code.

    Args:
        mode: Validation mode (all, required, ports, urls)
        verbose: Enable verbose output

    Returns:
        0 if validation passes, 1 if validation fails

    Validates Requirements: 10.1, 10.5
    """
    setup_logging(verbose)

    validator = ConfigValidator()

    # Run validation based on mode
    if mode == "all":
        result = validator.validate_all()
    elif mode == "required":
        validator.validate_required_vars()
        result = validator.result
        result.is_valid = not result.has_errors()
    elif mode == "ports":
        validator.validate_port_conflicts()
        result = validator.result
        result.is_valid = not result.has_errors()
    elif mode == "urls":
        validator.validate_urls()
        result = validator.result
        result.is_valid = not result.has_errors()
    else:
        logging.error(f"Invalid validation mode: {mode}")
        return 1

    # Return exit code based on validation result
    return 0 if result.is_valid else 1


def print_validation_report(result: ValidationResult, json_output: bool = False) -> None:
    """
    Print formatted validation report.

    Args:
        result: ValidationResult to format and display
        json_output: Output in JSON format instead of human-readable

    Validates Requirements: 10.5
    """
    if json_output:
        # Output as JSON
        report = {
            "is_valid": result.is_valid,
            "status": "PASSED" if result.is_valid else "FAILED",
            "errors": result.errors,
            "warnings": result.warnings,
            "config_summary": result.config_summary,
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
        }
        logger.info(str(json.dumps(report, indent=2)))
    else:
        # Output human-readable format
        validator = ConfigValidator()
        validator.result = result
        report_text = validator.format_validation_report()

        # Handle Unicode encoding issues on Windows
        try:
            logger.info(report_text)
        except UnicodeEncodeError:
            # Replace emoji characters with ASCII equivalents
            report_text = report_text.replace("✅", "[PASS]").replace("❌", "[FAIL]")
            logger.info(report_text)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Validate environment configuration for backend-frontend connectivity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate all configuration
  python backend/scripts/validate_config.py

  # Validate only required variables
  python backend/scripts/validate_config.py --mode required

  # Validate with verbose output
  python backend/scripts/validate_config.py --verbose

  # Output as JSON
  python backend/scripts/validate_config.py --json

Validation Modes:
  all       - Validate all configuration (default)
  required  - Validate only required environment variables
  ports     - Validate only port configurations
  urls      - Validate only URL formats and accessibility
        """,
    )

    parser.add_argument(
        "--mode", choices=["all", "required", "ports", "urls"], default="all", help="Validation mode (default: all)"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    return parser.parse_args()


def main() -> int:
    """
    Main entry point for configuration validation CLI.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    args = parse_arguments()

    # Run validation
    exit_code = validate_configuration(mode=args.mode, verbose=args.verbose)

    # Get the result for printing
    validator = ConfigValidator()

    # Re-run validation to get the result (since validate_configuration doesn't return it)
    if args.mode == "all":
        result = validator.validate_all()
    elif args.mode == "required":
        validator.validate_required_vars()
        result = validator.result
        result.is_valid = not result.has_errors()
    elif args.mode == "ports":
        validator.validate_port_conflicts()
        result = validator.result
        result.is_valid = not result.has_errors()
    elif args.mode == "urls":
        validator.validate_urls()
        result = validator.result
        result.is_valid = not result.has_errors()
    else:
        return 1

    # Print report
    print_validation_report(result, json_output=args.json)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
