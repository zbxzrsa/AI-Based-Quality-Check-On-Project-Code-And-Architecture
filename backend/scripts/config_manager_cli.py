#!/usr/bin/env python3
"""
Configuration Manager CLI Tool

Command-line interface for the unified configuration management system.
Provides commands for loading, validating, generating, and managing configurations.

Usage:
    python config_manager_cli.py load --environment development
    python config_manager_cli.py validate
    python config_manager_cli.py generate --service frontend --format env
    python config_manager_cli.py export --service backend --output backend.env
    python config_manager_cli.py status
    python config_manager_cli.py watch --enable

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.configuration_manager import ConfigurationManager, get_configuration_manager, initialize_configuration
from app.core.service_config_generator import (
    ServiceConfigGenerator,
    export_service_configuration,
    generate_service_configuration,
    get_service_config_generator,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ConfigManagerCLI:
    """Command-line interface for configuration management"""

    def __init__(self):
        self.config_manager: ConfigurationManager | None = None
        self.service_generator: ServiceConfigGenerator | None = None

    def setup_managers(self, project_path: str | None = None):
        """Setup configuration managers"""
        if project_path:
            project_path = Path(project_path)
            self.config_manager = ConfigurationManager(project_path)
        else:
            self.config_manager = get_configuration_manager()

        self.service_generator = get_service_config_generator()

    def load_configuration(self, environment: str = "development", enable_hot_reload: bool = False) -> bool:
        """
        Load configuration for specified environment

        Args:
            environment: Target environment
            enable_hot_reload: Whether to enable hot reloading

        Returns:
            True if successful
        """
        try:
            logger.info("Loading configuration for environment: {environment}")

            initialize_configuration(environment, enable_hot_reload)

            logger.info("✅ Configuration loaded successfully")
            logger.info("   - Total entries: {len(config)}")
            logger.info("   - Environment: {environment}")
            logger.info("   - Hot reload: {'enabled' if enable_hot_reload else 'disabled'}")

            # Show summary
            self.config_manager.get_configuration_summary()
            logger.info("   - Sources: {summary['sources']}")
            logger.info("   - Conflicts resolved: {summary['conflicts_resolved']}")
            logger.info("   - Secret keys: {summary['secret_keys']}")

            return True

        except Exception as e:
            logger.info("❌ Failed to load configuration: {e}")
            logger.error(f"Configuration loading failed: {e}")
            return False

    def validate_configuration(self) -> bool:
        """
        Validate current configuration

        Returns:
            True if validation passes
        """
        try:
            logger.info("Validating configuration...")

            if not self.config_manager:
                logger.info("❌ Configuration not loaded. Run 'load' command first.")
                return False

            # Get validation summary
            self.config_manager.get_configuration_summary()

            logger.info("✅ Configuration validation completed")
            logger.info("   - Total entries: {summary['total_entries']}")
            logger.info("   - Conflicts resolved: {summary['conflicts_resolved']}")
            logger.info("   - Secret keys: {summary['secret_keys']}")

            # Show conflicts if any
            if self.config_manager.conflicts:
                logger.info("\n📋 Resolved conflicts ({len(self.config_manager.conflicts)}):")
                for _conflict in self.config_manager.conflicts:
                    logger.info("   - {conflict.key}: {conflict.resolution_reason}")

            return True

        except Exception as e:
            logger.info("❌ Configuration validation failed: {e}")
            logger.error(f"Configuration validation failed: {e}")
            return False

    def generate_service_config(self, service_name: str, format: str = "env", include_deps: bool = True) -> bool:
        """
        Generate configuration for a specific service

        Args:
            service_name: Name of the service
            format: Output format (env, json, yaml)
            include_deps: Whether to include dependencies

        Returns:
            True if successful
        """
        try:
            logger.info("Generating configuration for service: {service_name}")

            if not self.config_manager:
                logger.info("❌ Configuration not loaded. Run 'load' command first.")
                return False

            # Generate service configuration
            generate_service_configuration(service_name, include_deps)

            logger.info("✅ Service configuration generated")
            logger.info("   - Service: {service_config.service_name}")
            logger.info("   - Configuration keys: {len(service_config.config)}")
            logger.info("   - Dependencies: {service_config.dependencies}")
            logger.info("   - Required keys: {len(service_config.required_keys)}")
            logger.info("   - Optional keys: {len(service_config.optional_keys)}")

            # Export in requested format
            config_content = export_service_configuration(service_name, format)

            logger.info("\n📄 Configuration ({format.upper()} format):")
            logger.info("-" * 50)
            logger.info(config_content)
            logger.info("-" * 50)

            return True

        except Exception as e:
            logger.info("❌ Failed to generate service configuration: {e}")
            logger.error(f"Service configuration generation failed: {e}")
            return False

    def export_service_config(self, service_name: str, output_file: str, format: str = "env") -> bool:
        """
        Export service configuration to file

        Args:
            service_name: Name of the service
            output_file: Output file path
            format: Output format

        Returns:
            True if successful
        """
        try:
            logger.info("Exporting {service_name} configuration to: {output_file}")

            if not self.config_manager:
                logger.info("❌ Configuration not loaded. Run 'load' command first.")
                return False

            output_path = Path(output_file)

            # Export configuration
            export_service_configuration(service_name, format, output_path)

            logger.info("✅ Configuration exported successfully")
            logger.info("   - Service: {service_name}")
            logger.info("   - Format: {format}")
            logger.info("   - Output file: {output_path.absolute()}")
            logger.info("   - File size: {output_path.stat().st_size} bytes")

            return True

        except Exception as e:
            logger.info("❌ Failed to export service configuration: {e}")
            logger.error(f"Service configuration export failed: {e}")
            return False

    def show_status(self) -> bool:
        """
        Show configuration system status

        Returns:
            True if successful
        """
        try:
            logger.info("Configuration System Status")
            logger.info("=" * 50)

            if not self.config_manager:
                logger.info("❌ Configuration not loaded")
                return False

            # Configuration manager status
            summary = self.config_manager.get_configuration_summary()
            logger.info("Configuration Manager:")
            logger.info("   - Total entries: {summary['total_entries']}")
            logger.info("   - Conflicts resolved: {summary['conflicts_resolved']}")
            logger.info("   - Hot reloading: {'enabled' if summary['hot_reloading_enabled'] else 'disabled'}")
            logger.info("   - Secret keys: {summary['secret_keys']}")

            # Sources breakdown
            logger.info("\nConfiguration Sources:")
            for _source, _count in summary["sources"].items():
                logger.info("   - {source}: {count} entries")

            # Service generator status
            if self.service_generator:
                all_status = self.service_generator.get_all_service_status()
                logger.info("\nRegistered Services ({len(all_status)}):")

                for _service_name, status in all_status.items():
                    "🟢" if status["is_active"] else "🔴"
                    logger.info("   {active_indicator} {service_name} ({status['type']})")
                    logger.info("      - Dependencies: {len(status['dependencies'])}")
                    logger.info("      - Required keys: {len(status['required_keys'])}")
                    logger.info("      - Optional keys: {len(status['optional_keys'])}")
                    if status["last_update"]:
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(status["last_update"]))
                        logger.info("      - Last update: {last_update}")

            return True

        except Exception as e:
            logger.info("❌ Failed to show status: {e}")
            logger.error(f"Status display failed: {e}")
            return False

    def manage_hot_reload(self, enable: bool) -> bool:
        """
        Enable or disable hot reloading

        Args:
            enable: Whether to enable hot reloading

        Returns:
            True if successful
        """
        try:
            if not self.config_manager:
                logger.info("❌ Configuration not loaded. Run 'load' command first.")
                return False

            if enable:
                logger.info("Enabling configuration hot reloading...")
                self.config_manager.enable_hot_reloading()
                logger.info("✅ Hot reloading enabled")
                logger.info("   Configuration files will be monitored for changes")
            else:
                logger.info("Disabling configuration hot reloading...")
                self.config_manager.disable_hot_reloading()
                logger.info("✅ Hot reloading disabled")

            return True

        except Exception as e:
            logger.info("❌ Failed to manage hot reload: {e}")
            logger.error(f"Hot reload management failed: {e}")
            return False

    def list_services(self) -> bool:
        """
        List all registered services

        Returns:
            True if successful
        """
        try:
            logger.info("Registered Services")
            logger.info("=" * 50)

            if not self.service_generator:
                logger.info("❌ Service generator not initialized")
                return False

            all_status = self.service_generator.get_all_service_status()

            if not all_status:
                logger.info("No services registered")
                return True

            for _service_name, status in all_status.items():
                "🟢" if status["is_active"] else "🔴"
                logger.info("\n{active_indicator} {service_name}")
                logger.info("   Type: {status['type']}")
                logger.info(
                    "   Dependencies: {', '.join(status['dependencies']) if status['dependencies'] else 'None'}"
                )
                logger.info("   Required keys: {len(status['required_keys'])}")
                logger.info("   Optional keys: {len(status['optional_keys'])}")

                if status["config_file_path"]:
                    logger.info("   Config file: {status['config_file_path']}")

                if status["health_check_url"]:
                    logger.info("   Health check: {status['health_check_url']}")

                if status["last_update"]:
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(status["last_update"]))
                    logger.info("   Last update: {last_update}")

            return True

        except Exception as e:
            logger.info("❌ Failed to list services: {e}")
            logger.error(f"Service listing failed: {e}")
            return False

    def update_configuration(self, key: str, value: str) -> bool:
        """
        Update a configuration value

        Args:
            key: Configuration key
            value: New value

        Returns:
            True if successful
        """
        try:
            logger.info("Updating configuration: {key}")

            if not self.config_manager:
                logger.info("❌ Configuration not loaded. Run 'load' command first.")
                return False

            # Update configuration
            self.config_manager.update_configuration({key: value})

            logger.info("✅ Configuration updated successfully")
            logger.info("   - Key: {key}")
            logger.info("   - Value: {'***' if 'SECRET' in key or 'PASSWORD' in key else value}")

            return True

        except Exception as e:
            logger.info("❌ Failed to update configuration: {e}")
            logger.error(f"Configuration update failed: {e}")
            return False


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="Configuration Manager CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s load --environment development
  %(prog)s validate
  %(prog)s generate --service frontend --format env
  %(prog)s export --service backend --output backend.env
  %(prog)s status
  %(prog)s watch --enable
  %(prog)s services
  %(prog)s update --key JWT_SECRET --value new_secret_value
        """,
    )

    parser.add_argument("--project-path", type=str, help="Path to project root directory")

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Load command
    load_parser = subparsers.add_parser("load", help="Load configuration")
    load_parser.add_argument(
        "--environment",
        "-e",
        default="development",
        choices=["development", "staging", "production"],
        help="Target environment",
    )
    load_parser.add_argument("--hot-reload", action="store_true", help="Enable hot reloading")

    # Validate command
    subparsers.add_parser("validate", help="Validate configuration")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate service configuration")
    generate_parser.add_argument("--service", "-s", required=True, help="Service name")
    generate_parser.add_argument("--format", "-f", default="env", choices=["env", "json", "yaml"], help="Output format")
    generate_parser.add_argument("--no-deps", action="store_true", help="Exclude dependencies")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export service configuration to file")
    export_parser.add_argument("--service", "-s", required=True, help="Service name")
    export_parser.add_argument("--output", "-o", required=True, help="Output file path")
    export_parser.add_argument("--format", "-f", default="env", choices=["env", "json", "yaml"], help="Output format")

    # Status command
    subparsers.add_parser("status", help="Show configuration system status")

    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Manage hot reloading")
    watch_group = watch_parser.add_mutually_exclusive_group(required=True)
    watch_group.add_argument("--enable", action="store_true", help="Enable hot reloading")
    watch_group.add_argument("--disable", action="store_true", help="Disable hot reloading")

    # Services command
    subparsers.add_parser("services", help="List registered services")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update configuration value")
    update_parser.add_argument("--key", "-k", required=True, help="Configuration key")
    update_parser.add_argument("--value", "-v", required=True, help="New value")

    return parser


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create CLI instance
    cli = ConfigManagerCLI()

    # Setup managers
    cli.setup_managers(args.project_path)

    # Execute command
    success = False

    try:
        if args.command == "load":
            success = cli.load_configuration(args.environment, args.hot_reload)

        elif args.command == "validate":
            success = cli.validate_configuration()

        elif args.command == "generate":
            success = cli.generate_service_config(args.service, args.format, not args.no_deps)

        elif args.command == "export":
            success = cli.export_service_config(args.service, args.output, args.format)

        elif args.command == "status":
            success = cli.show_status()

        elif args.command == "watch":
            success = cli.manage_hot_reload(args.enable)

        elif args.command == "services":
            success = cli.list_services()

        elif args.command == "update":
            success = cli.update_configuration(args.key, args.value)

        else:
            parser.print_help()
            success = False

    except KeyboardInterrupt:
        logger.info("\n⚠️  Operation cancelled by user")
        success = False

    except Exception as e:
        logger.info("❌ Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}")
        success = False

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
