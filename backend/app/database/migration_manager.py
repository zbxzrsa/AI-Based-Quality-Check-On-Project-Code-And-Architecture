"""
Database migration manager for automatic application of Alembic migrations
"""
import logging
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import subprocess
import sys
from datetime import datetime
import json
import os

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text, inspect

from app.core.config import settings
from app.utils.encoding_validator import EncodingValidator, EncodingValidationResult, EncodingFixResult

logger = logging.getLogger(__name__)


@dataclass
class MigrationStatus:
    """Status of database migrations"""
    pending_count: int
    applied_count: int
    current_version: Optional[str]
    is_up_to_date: bool
    errors: List[str]
    encoding_issues: List[EncodingValidationResult] = None
    encoding_fixes_applied: List[EncodingFixResult] = None
    
    def __post_init__(self):
        """Initialize encoding_issues and encoding_fixes_applied if not provided"""
        if self.encoding_issues is None:
            self.encoding_issues = []
        if self.encoding_fixes_applied is None:
            self.encoding_fixes_applied = []
    
    def __str__(self) -> str:
        """String representation of migration status"""
        status_str = f"Migrations: {self.applied_count} applied"
        if self.pending_count > 0:
            status_str += f", {self.pending_count} pending"
        if self.current_version:
            status_str += f", current version: {self.current_version}"
        if self.encoding_issues:
            invalid_count = sum(1 for issue in self.encoding_issues if not issue.is_valid)
            if invalid_count > 0:
                status_str += f", {invalid_count} encoding issue(s)"
        if self.encoding_fixes_applied:
            fixed_count = sum(1 for fix in self.encoding_fixes_applied if fix.success)
            if fixed_count > 0:
                status_str += f", {fixed_count} encoding fix(es) applied"
        if self.errors:
            status_str += f", {len(self.errors)} error(s)"
        return status_str


class MigrationManager:
    """Manages database migrations using Alembic"""
    
    def __init__(self):
        """Initialize migration manager"""
        self.alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"
        self.alembic_config = Config(str(self.alembic_ini_path))
        self.alembic_config.set_main_option('sqlalchemy.url', settings.sync_postgres_url)
        self.encoding_validator = EncodingValidator()
        
        # Backup directory
        self.backup_dir = Path(__file__).parent.parent.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    async def check_pending_migrations(self) -> List[str]:
        """
        Check for pending migrations
        
        Returns:
            List of pending migration identifiers
        """
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            
            # Get the current database revision
            from sqlalchemy import create_engine
            engine = create_engine(settings.sync_postgres_url)
            
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_revision = context.get_current_revision()
            
            engine.dispose()
            
            # Get all revisions
            all_revisions = list(script_dir.walk_revisions())
            
            # Find pending revisions
            pending = []
            found_current = False
            
            for revision in reversed(all_revisions):
                if current_revision is None:
                    # No migrations applied yet, all are pending
                    pending.append(revision.revision)
                elif revision.revision == current_revision:
                    found_current = True
                    break
                elif found_current:
                    break
                else:
                    pending.append(revision.revision)
            
            return pending
            
        except Exception as e:
            logger.error(f"Error checking pending migrations: {e}")
            return []
    
    async def apply_pending_migrations(self) -> 'MigrationStatus':
        """
        Apply all pending migrations
        
        Returns:
            MigrationStatus with results of migration application
        """
        errors = []
        encoding_fixes_applied = []
        
        try:
            # First validate migration file encoding
            logger.info("Validating migration file encoding before applying migrations")
            encoding_issues = await self.validate_migration_files()
            
            # Check for encoding problems that would prevent migration execution
            critical_encoding_issues = [issue for issue in encoding_issues if not issue.is_valid]
            if critical_encoding_issues:
                logger.warning(f"Found {len(critical_encoding_issues)} files with encoding issues, attempting to fix...")
                
                # Attempt to fix encoding issues
                for issue in critical_encoding_issues:
                    fix_result = await self.fix_migration_file_encoding(Path(issue.file_path))
                    encoding_fixes_applied.append(fix_result)
                    
                    if not fix_result.success:
                        error_msg = f"Cannot fix encoding issues in {issue.file_path}: {', '.join(fix_result.errors)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                # Re-validate after fixes
                if not errors:  # Only if all fixes were successful
                    logger.info("Re-validating migration files after encoding fixes")
                    encoding_issues = await self.validate_migration_files()
                    remaining_issues = [issue for issue in encoding_issues if not issue.is_valid]
                    
                    if remaining_issues:
                        error_msg = f"Still have encoding issues in {len(remaining_issues)} file(s) after fix attempts"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        
                        for issue in remaining_issues:
                            logger.error(f"  {issue.file_path}: {', '.join(issue.errors)}")
                        
                        # Return status with encoding issues
                        status = await self.get_migration_status()
                        status.errors.extend(errors)
                        status.encoding_fixes_applied = encoding_fixes_applied
                        return status
                else:
                    # Return status with fix failures
                    status = await self.get_migration_status()
                    status.errors.extend(errors)
                    status.encoding_fixes_applied = encoding_fixes_applied
                    return status
            
            # Check if alembic_version table exists
            from sqlalchemy import create_engine
            engine = create_engine(settings.sync_postgres_url)
            
            with engine.connect() as connection:
                inspector = inspect(connection)
                tables = inspector.get_table_names()
                
                if 'alembic_version' not in tables:
                    logger.info("Creating alembic_version table")
                    connection.execute(text("""
                        CREATE TABLE alembic_version (
                            version_num varchar(32) not null,
                            primary key (version_num)
                        )
                    """))
                    connection.commit()
            
            engine.dispose()
            
            # Run alembic upgrade
            logger.info("Applying pending migrations")
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=str(self.alembic_ini_path.parent.parent),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                error_msg = f"Migration failed: {result.stderr}"
                logger.error(error_msg)
                errors.append(error_msg)
            else:
                logger.info("Migrations applied successfully")
                logger.debug(f"Migration output: {result.stdout}")
            
        except subprocess.TimeoutExpired:
            error_msg = "Migration timeout (exceeded 300 seconds)"
            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error applying migrations: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Get migration status
        status = await self.get_migration_status()
        status.errors.extend(errors)
        status.encoding_fixes_applied = encoding_fixes_applied
        
        return status
    
    async def get_migration_status(self) -> MigrationStatus:
        """
        Get current migration status
        
        Returns:
            MigrationStatus with current migration information
        """
        errors = []
        pending_count = 0
        applied_count = 0
        current_version = None
        encoding_issues = []
        
        try:
            from sqlalchemy import create_engine
            engine = create_engine(settings.sync_postgres_url)
            
            with engine.connect() as connection:
                # Get current revision
                try:
                    context = MigrationContext.configure(connection)
                    current_version = context.get_current_revision()
                except Exception as e:
                    logger.warning(f"Could not get current revision: {e}")
                
                # Count applied migrations
                try:
                    result = connection.execute(text(
                        "SELECT COUNT(*) FROM alembic_version"
                    ))
                    applied_count = result.scalar() or 0
                except Exception:
                    applied_count = 0
            
            engine.dispose()
            
            # Get pending migrations
            pending = await self.check_pending_migrations()
            pending_count = len(pending)
            
            # Validate migration file encoding
            encoding_issues = await self.validate_migration_files()
            
        except Exception as e:
            error_msg = f"Error getting migration status: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        is_up_to_date = pending_count == 0 and len(errors) == 0 and all(issue.is_valid for issue in encoding_issues)
        
        return MigrationStatus(
            pending_count=pending_count,
            applied_count=applied_count,
            current_version=current_version,
            is_up_to_date=is_up_to_date,
            errors=errors,
            encoding_issues=encoding_issues
        )
    
    async def validate_migration_files(self) -> List[EncodingValidationResult]:
        """
        Validate UTF-8 encoding of all migration files
        
        Returns:
            List of EncodingValidationResult for each migration file
        """
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            versions_dir = Path(script_dir.dir)
            
            if not versions_dir.exists():
                logger.warning(f"Migration versions directory does not exist: {versions_dir}")
                return []
            
            # Validate all Python files in versions directory
            results = self.encoding_validator.validate_directory_encoding(versions_dir, "*.py")
            
            # Log any encoding issues found
            for result in results:
                if not result.is_valid:
                    logger.warning(f"Encoding issue in migration file: {result}")
                    # Get problematic lines for detailed error reporting
                    problematic_lines = self.encoding_validator.get_problematic_lines(Path(result.file_path))
                    for line_num, line_content, error_desc in problematic_lines:
                        logger.error(f"  Line {line_num}: {error_desc}")
                        logger.debug(f"  Content: {line_content[:100]}...")
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating migration files: {e}")
            return [EncodingValidationResult(
                is_valid=False,
                detected_encoding=None,
                confidence=0.0,
                errors=[f"Error validating migration files: {e}"],
                file_path="migration_directory"
            )]
    
    async def validate_migration_file(self, file_path: Path) -> EncodingValidationResult:
        """
        Validate UTF-8 encoding of a specific migration file
        
        Args:
            file_path: Path to the migration file to validate
            
        Returns:
            EncodingValidationResult for the file
        """
        try:
            result = self.encoding_validator.validate_file_encoding(file_path)
            
            if not result.is_valid:
                logger.warning(f"Migration file encoding validation failed: {result}")
                # Get detailed error information
                problematic_lines = self.encoding_validator.get_problematic_lines(file_path)
                for line_num, line_content, error_desc in problematic_lines:
                    logger.error(f"  Line {line_num} in {file_path.name}: {error_desc}")
            else:
                logger.debug(f"Migration file encoding validation passed: {file_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating migration file {file_path}: {e}")
            return EncodingValidationResult(
                is_valid=False,
                detected_encoding=None,
                confidence=0.0,
                errors=[f"Error validating file: {e}"],
                file_path=str(file_path)
            )
    
    async def fix_migration_file_encoding(self, file_path: Path) -> EncodingFixResult:
        """
        Attempt to fix encoding issues in a migration file
        
        Args:
            file_path: Path to the migration file to fix
            
        Returns:
            EncodingFixResult with details of the fix attempt
        """
        try:
            logger.info(f"Attempting to fix encoding issues in {file_path}")
            
            # Use the encoding validator to fix the file
            fix_result = self.encoding_validator.fix_encoding_issues(file_path)
            
            if fix_result.success and fix_result.fixed_content is not None:
                # Write the fixed content back to the file with proper UTF-8 encoding
                success = self.encoding_validator.create_utf8_file(file_path, fix_result.fixed_content)
                
                if success:
                    logger.info(f"Successfully fixed encoding in {file_path} (converted from {fix_result.original_encoding})")
                    
                    # Validate the fixed file
                    validation_result = await self.validate_migration_file(file_path)
                    if not validation_result.is_valid:
                        fix_result.success = False
                        fix_result.errors.append(f"Fixed file still has encoding issues: {validation_result.errors}")
                        logger.error(f"Fixed file {file_path} still has encoding issues")
                else:
                    fix_result.success = False
                    fix_result.errors.append("Failed to write fixed content to file")
                    logger.error(f"Failed to write fixed content to {file_path}")
            
            return fix_result
            
        except Exception as e:
            logger.error(f"Error fixing encoding for migration file {file_path}: {e}")
            return EncodingFixResult(
                success=False,
                original_encoding=None,
                fixed_content=None,
                errors=[f"Error fixing encoding: {e}"]
            )
    
    async def create_migration_file(self, file_path: Path, content: str) -> bool:
        """
        Create a new migration file with proper UTF-8 encoding
        
        Args:
            file_path: Path where to create the migration file
            content: Migration file content
            
        Returns:
            True if file was created successfully with proper UTF-8 encoding, False otherwise
        """
        try:
            logger.info(f"Creating new migration file with UTF-8 encoding: {file_path}")
            
            # Use the encoding validator to create the file with proper UTF-8 encoding
            success = self.encoding_validator.create_utf8_file(file_path, content)
            
            if success:
                # Validate the created file
                validation_result = await self.validate_migration_file(file_path)
                if validation_result.is_valid:
                    logger.info(f"Successfully created UTF-8 migration file: {file_path}")
                    return True
                else:
                    logger.error(f"Created migration file {file_path} failed UTF-8 validation: {validation_result.errors}")
                    return False
            else:
                logger.error(f"Failed to create migration file: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating migration file {file_path}: {e}")
            return False
    
    async def validate_before_migration_execution(self, migration_files: List[Path]) -> List[EncodingValidationResult]:
        """
        Validate file encoding before migration execution
        
        Args:
            migration_files: List of migration files to validate
            
        Returns:
            List of EncodingValidationResult for each file
        """
        logger.info(f"Validating encoding for {len(migration_files)} migration files before execution")
        
        validation_results = []
        
        for file_path in migration_files:
            try:
                result = await self.validate_migration_file(file_path)
                validation_results.append(result)
                
                if not result.is_valid:
                    logger.error(f"Migration file {file_path} has encoding issues and cannot be executed safely")
                    
            except Exception as e:
                logger.error(f"Error validating migration file {file_path}: {e}")
                validation_results.append(EncodingValidationResult(
                    is_valid=False,
                    detected_encoding=None,
                    confidence=0.0,
                    errors=[f"Validation error: {e}"],
                    file_path=str(file_path)
                ))
        
        # Log summary
        invalid_count = sum(1 for result in validation_results if not result.is_valid)
        if invalid_count > 0:
            logger.warning(f"Found {invalid_count} migration files with encoding issues")
        else:
            logger.info("All migration files passed encoding validation")
        
        return validation_results
    
    async def handle_non_utf8_characters(self, file_path: Path, strategy: str = "convert") -> EncodingFixResult:
        """
        Handle non-UTF-8 characters in migration files
        
        Args:
            file_path: Path to the migration file
            strategy: Strategy for handling non-UTF-8 characters ("convert" or "reject")
            
        Returns:
            EncodingFixResult with details of the handling
        """
        try:
            logger.info(f"Handling non-UTF-8 characters in {file_path} using strategy: {strategy}")
            
            # First validate the file to see if it has issues
            validation_result = await self.validate_migration_file(file_path)
            
            if validation_result.is_valid:
                # File is already valid UTF-8, no action needed
                return EncodingFixResult(
                    success=True,
                    original_encoding=validation_result.detected_encoding,
                    fixed_content=None,
                    errors=[]
                )
            
            if strategy == "reject":
                # Reject files with non-UTF-8 characters
                error_msg = f"File {file_path} contains non-UTF-8 characters and is rejected"
                logger.error(error_msg)
                return EncodingFixResult(
                    success=False,
                    original_encoding=validation_result.detected_encoding,
                    fixed_content=None,
                    errors=[error_msg]
                )
            
            elif strategy == "convert":
                # Attempt to convert the file to UTF-8
                return await self.fix_migration_file_encoding(file_path)
            
            else:
                error_msg = f"Unknown strategy for handling non-UTF-8 characters: {strategy}"
                logger.error(error_msg)
                return EncodingFixResult(
                    success=False,
                    original_encoding=validation_result.detected_encoding,
                    fixed_content=None,
                    errors=[error_msg]
                )
                
        except Exception as e:
            logger.error(f"Error handling non-UTF-8 characters in {file_path}: {e}")
            return EncodingFixResult(
                success=False,
                original_encoding=None,
                fixed_content=None,
                errors=[f"Error handling non-UTF-8 characters: {e}"]
            )
    
    async def rollback_migration(self, revision: str) -> bool:
        """
        Rollback database to a specific migration revision
        
        Args:
            revision: Target revision to rollback to (e.g., "abc123" or "-1" for previous)
            
        Returns:
            True if rollback was successful, False otherwise
        """
        try:
            logger.info(f"Rolling back database to revision: {revision}")
            
            # Create backup before rollback
            backup_id = await self.create_backup()
            if not backup_id:
                logger.error("Failed to create backup before rollback, aborting")
                return False
            
            logger.info(f"Created backup {backup_id} before rollback")
            
            # Run alembic downgrade
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "downgrade", revision],
                cwd=str(self.alembic_ini_path.parent.parent),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"Rollback failed: {result.stderr}")
                logger.info(f"Backup {backup_id} is available for manual restoration")
                return False
            
            logger.info(f"Successfully rolled back to revision {revision}")
            logger.debug(f"Rollback output: {result.stdout}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Rollback timeout (exceeded 300 seconds)")
            return False
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False
    
    async def create_backup(self) -> Optional[str]:
        """
        Create a backup of the PostgreSQL database
        
        Returns:
            Backup ID (timestamp-based) if successful, None otherwise
        """
        try:
            # Generate backup ID based on timestamp
            backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"postgres_backup_{backup_id}.sql"
            
            logger.info(f"Creating database backup: {backup_id}")
            
            # Use pg_dump to create backup
            env = os.environ.copy()
            env['PGPASSWORD'] = settings.POSTGRES_PASSWORD
            
            result = subprocess.run(
                [
                    "pg_dump",
                    "-h", settings.POSTGRES_HOST,
                    "-p", str(settings.POSTGRES_PORT),
                    "-U", settings.POSTGRES_USER,
                    "-d", settings.POSTGRES_DB,
                    "-F", "c",  # Custom format (compressed)
                    "-f", str(backup_path)
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                logger.error(f"Backup failed: {result.stderr}")
                return None
            
            # Create metadata file
            metadata = {
                "backup_id": backup_id,
                "timestamp": datetime.now().isoformat(),
                "database": settings.POSTGRES_DB,
                "host": settings.POSTGRES_HOST,
                "backup_file": str(backup_path),
                "size_bytes": backup_path.stat().st_size if backup_path.exists() else 0
            }
            
            metadata_path = self.backup_dir / f"postgres_backup_{backup_id}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Backup created successfully: {backup_id} ({metadata['size_bytes']} bytes)")
            return backup_id
            
        except subprocess.TimeoutExpired:
            logger.error("Backup timeout (exceeded 600 seconds)")
            return None
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    async def restore_backup(self, backup_id: str) -> bool:
        """
        Restore database from a backup
        
        Args:
            backup_id: Backup ID to restore from
            
        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            backup_path = self.backup_dir / f"postgres_backup_{backup_id}.sql"
            metadata_path = self.backup_dir / f"postgres_backup_{backup_id}.json"
            
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            logger.info(f"Restoring database from backup: {backup_id}")
            
            # Load metadata
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                logger.info(f"Backup metadata: {metadata}")
            
            # Use pg_restore to restore backup
            env = os.environ.copy()
            env['PGPASSWORD'] = settings.POSTGRES_PASSWORD
            
            # First, drop and recreate the database (requires superuser or database owner)
            # Note: This is a destructive operation
            logger.warning(f"Dropping and recreating database: {settings.POSTGRES_DB}")
            
            # Connect to postgres database to drop/create target database
            drop_result = subprocess.run(
                [
                    "psql",
                    "-h", settings.POSTGRES_HOST,
                    "-p", str(settings.POSTGRES_PORT),
                    "-U", settings.POSTGRES_USER,
                    "-d", "postgres",
                    "-c", f"DROP DATABASE IF EXISTS {settings.POSTGRES_DB};"
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if drop_result.returncode != 0:
                logger.error(f"Failed to drop database: {drop_result.stderr}")
                return False
            
            create_result = subprocess.run(
                [
                    "psql",
                    "-h", settings.POSTGRES_HOST,
                    "-p", str(settings.POSTGRES_PORT),
                    "-U", settings.POSTGRES_USER,
                    "-d", "postgres",
                    "-c", f"CREATE DATABASE {settings.POSTGRES_DB};"
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if create_result.returncode != 0:
                logger.error(f"Failed to create database: {create_result.stderr}")
                return False
            
            # Restore the backup
            result = subprocess.run(
                [
                    "pg_restore",
                    "-h", settings.POSTGRES_HOST,
                    "-p", str(settings.POSTGRES_PORT),
                    "-U", settings.POSTGRES_USER,
                    "-d", settings.POSTGRES_DB,
                    "-F", "c",  # Custom format
                    str(backup_path)
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                # pg_restore may return non-zero even on success due to warnings
                # Check if there are actual errors
                if "error" in result.stderr.lower():
                    logger.error(f"Restore failed: {result.stderr}")
                    return False
                else:
                    logger.warning(f"Restore completed with warnings: {result.stderr}")
            
            logger.info(f"Database restored successfully from backup: {backup_id}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Restore timeout (exceeded 600 seconds)")
            return False
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False


# Global migration manager instance
_migration_manager: Optional[MigrationManager] = None


def get_migration_manager() -> MigrationManager:
    """Get or create migration manager instance"""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager()
    return _migration_manager
