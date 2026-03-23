"""
Package Installer Service for Library Management

This service installs packages using package managers (npm, pip) and handles
dependency file updates, backup/rollback operations, and installation verification.
"""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from app.schemas.library import LibraryMetadata, InstallationResult, InstalledLibrary
from app.models.library import ProjectContext, RegistryType


logger = logging.getLogger(__name__)


class PackageInstallerError(Exception):
    """Base exception for package installation errors"""
    pass


class FileOperationError(PackageInstallerError):
    """Error during file operations (backup, update, restore)"""
    pass


class CommandExecutionError(PackageInstallerError):
    """Error executing package manager commands"""
    pass


class InstallationVerificationError(PackageInstallerError):
    """Error verifying package installation"""
    pass


class FileManager:
    """
    Utility class for file operations with backup/restore capabilities
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize FileManager
        
        Args:
            project_root: Root directory of the project (defaults to current working directory)
        """
        self.project_root = Path(project_root or os.getcwd())
        logger.debug(f"FileManager initialized with project root: {self.project_root}")
    
    def create_backup(self, file_path: str) -> str:
        """
        Create a backup of the specified file
        
        Args:
            file_path: Path to file relative to project root
            
        Returns:
            Path to backup file
            
        Raises:
            FileOperationError: If backup creation fails
        """
        try:
            source_path = self.project_root / file_path
            
            if not source_path.exists():
                raise FileOperationError(f"Source file does not exist: {file_path}")
            
            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source_path.name}.backup_{timestamp}"
            backup_path = source_path.parent / backup_name
            
            # Copy file to backup location
            shutil.copy2(source_path, backup_path)
            
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            raise FileOperationError(f"Backup creation failed: {e}")
    
    def restore_from_backup(self, backup_path: str) -> None:
        """
        Restore file from backup
        
        Args:
            backup_path: Path to backup file
            
        Raises:
            FileOperationError: If restore fails
        """
        try:
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                raise FileOperationError(f"Backup file does not exist: {backup_path}")
            
            # Determine original file path by removing backup suffix
            original_name = backup_file.name.split('.backup_')[0]
            original_path = backup_file.parent / original_name
            
            # Restore file
            shutil.copy2(backup_file, original_path)
            
            logger.info(f"Restored file from backup: {original_path}")
            
        except Exception as e:
            logger.error(f"Failed to restore from backup {backup_path}: {e}")
            raise FileOperationError(f"Restore failed: {e}")
    
    def read_file(self, file_path: str) -> str:
        """
        Read file content
        
        Args:
            file_path: Path to file relative to project root
            
        Returns:
            File content as string
            
        Raises:
            FileOperationError: If file reading fails
        """
        try:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                raise FileOperationError(f"File does not exist: {file_path}")
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise FileOperationError(f"File read failed: {e}")
    
    def write_file(self, file_path: str, content: str) -> None:
        """
        Write content to file
        
        Args:
            file_path: Path to file relative to project root
            content: Content to write
            
        Raises:
            FileOperationError: If file writing fails
        """
        try:
            full_path = self.project_root / file_path
            
            # Ensure parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"Wrote file: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            raise FileOperationError(f"File write failed: {e}")
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists
        
        Args:
            file_path: Path to file relative to project root
            
        Returns:
            True if file exists, False otherwise
        """
        full_path = self.project_root / file_path
        return full_path.exists() and full_path.is_file()


class CommandExecutor:
    """
    Utility class for executing package manager commands
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize CommandExecutor
        
        Args:
            project_root: Root directory of the project (defaults to current working directory)
        """
        self.project_root = Path(project_root or os.getcwd())
        logger.debug(f"CommandExecutor initialized with project root: {self.project_root}")
    
    async def execute_command(
        self,
        command: List[str],
        working_dir: str,
        timeout: float = 300.0
    ) -> Tuple[int, str, str]:
        """
        Execute command asynchronously
        
        Args:
            command: Command and arguments as list
            working_dir: Working directory relative to project root
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
            
        Raises:
            CommandExecutionError: If command execution fails
        """
        try:
            full_working_dir = self.project_root / working_dir
            
            if not full_working_dir.exists():
                raise CommandExecutionError(f"Working directory does not exist: {working_dir}")
            
            logger.info(f"Executing command: {' '.join(command)} in {full_working_dir}")
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(full_working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return_code = process.returncode
                stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
                stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
                
                logger.debug(
                    f"Command completed with return code {return_code}, "
                    f"stdout: {len(stdout_str)} chars, stderr: {len(stderr_str)} chars"
                )
                
                return return_code, stdout_str, stderr_str
                
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()
                raise CommandExecutionError(f"Command timed out after {timeout} seconds")
                
        except Exception as e:
            if isinstance(e, CommandExecutionError):
                raise
            logger.error(f"Failed to execute command {command}: {e}")
            raise CommandExecutionError(f"Command execution failed: {e}")


class PackageInstaller:
    """
    Service to install packages using package managers
    
    This service provides methods to:
    - Install libraries by updating dependency files and executing package manager commands
    - Create backups before modifications and rollback on failure
    - Verify installation by checking if packages are accessible
    - Update lock files after successful installation
    """
    
    # Configuration for different project contexts
    CONTEXT_CONFIG = {
        ProjectContext.FRONTEND: {
            'dependency_file': 'frontend/package.json',
            'lock_file': 'frontend/package-lock.json',
            'working_dir': 'frontend',
            'install_command': ['npm', 'install'],
            'verify_command': ['npm', 'list', '--depth=0']
        },
        ProjectContext.BACKEND: {
            'dependency_file': 'backend/requirements.txt',
            'lock_file': 'backend/poetry.lock',  # or requirements.lock if using pip-tools
            'working_dir': 'backend',
            'install_command': ['pip', 'install', '-r', 'requirements.txt'],
            'verify_command': ['pip', 'list']
        },
        ProjectContext.SERVICES: {
            'dependency_file': 'services/package.json',
            'lock_file': 'services/package-lock.json',
            'working_dir': 'services',
            'install_command': ['npm', 'install'],
            'verify_command': ['npm', 'list', '--depth=0']
        }
    }
    
    def __init__(
        self,
        file_manager: Optional[FileManager] = None,
        command_executor: Optional[CommandExecutor] = None,
        project_root: Optional[str] = None
    ):
        """
        Initialize PackageInstaller
        
        Args:
            file_manager: File manager instance (creates new one if None)
            command_executor: Command executor instance (creates new one if None)
            project_root: Root directory of the project
        """
        self.project_root = project_root or os.getcwd()
        self.file_manager = file_manager or FileManager(self.project_root)
        self.command_executor = command_executor or CommandExecutor(self.project_root)
        
        logger.debug(f"PackageInstaller initialized with project root: {self.project_root}")
    
    async def install(
        self,
        library: LibraryMetadata,
        project_context: ProjectContext,
        version: Optional[str] = None
    ) -> InstallationResult:
        """
        Install library by updating dependency file and executing package manager commands
        
        This method performs the following steps:
        1. Create backup of dependency file
        2. Update dependency file with new library
        3. Execute package manager install command
        4. Verify installation
        5. Update lock files
        6. Rollback on failure
        
        Args:
            library: Library metadata to install
            project_context: Target project context (backend, frontend, services)
            version: Specific version to install (overrides library.version)
            
        Returns:
            InstallationResult with success status and details
        """
        backup_path = None
        install_version = version or library.version
        
        try:
            logger.info(
                f"Starting installation of {library.name}@{install_version} "
                f"in {project_context.value} context"
            )
            
            # Get configuration for project context
            if project_context not in self.CONTEXT_CONFIG:
                raise PackageInstallerError(f"Unsupported project context: {project_context}")
            
            config = self.CONTEXT_CONFIG[project_context]
            
            # Step 1: Create backup of dependency file
            backup_path = await asyncio.to_thread(self.file_manager.create_backup, config['dependency_file'])
            
            # Step 2: Update dependency file
            await self._update_dependency_file(
                config['dependency_file'],
                library.name,
                install_version,
                library.registry_type
            )
            
            # Step 3: Execute install command
            return_code, stdout, stderr = await self.command_executor.execute_command(
                config['install_command'],
                config['working_dir']
            )
            
            if return_code != 0:
                raise CommandExecutionError(
                    f"Package manager install failed with return code {return_code}. "
                    f"stderr: {stderr}"
                )
            
            # Step 4: Verify installation
            await self._verify_installation(library.name, project_context)
            
            # Step 5: Update lock files (if they exist)
            await self._update_lock_files(project_context)
            
            # Create installed library record
            installed_library = InstalledLibrary(
                project_id="default",  # This should come from context in real implementation
                name=library.name,
                version=install_version,
                registry_type=library.registry_type,
                project_context=project_context,
                description=library.description,
                license=library.license,
                installed_at=datetime.now(),
                installed_by="system",  # This should come from auth context
                uri=f"{library.registry_type.value}:{library.name}@{install_version}",
                metadata={
                    'dependencies': [dep.dict() for dep in library.dependencies],
                    'homepage': library.homepage,
                    'repository': library.repository
                }
            )
            
            logger.info(f"Successfully installed {library.name}@{install_version}")
            
            return InstallationResult(
                success=True,
                installed_library=installed_library,
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"Installation failed for {library.name}@{install_version}: {e}")
            
            # Rollback on failure
            if backup_path:
                try:
                    await asyncio.to_thread(self.rollback, backup_path)
                    logger.info("Successfully rolled back changes")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
            
            return InstallationResult(
                success=False,
                installed_library=None,
                errors=[str(e)]
            )
    
    async def _update_dependency_file(
        self,
        file_path: str,
        library_name: str,
        version: str,
        registry_type: RegistryType
    ) -> None:
        """
        Update dependency file with new library
        
        Args:
            file_path: Path to dependency file
            library_name: Name of library to add
            version: Version to install
            registry_type: Type of registry (npm, pypi, etc.)
            
        Raises:
            FileOperationError: If file update fails
        """
        try:
            if file_path.endswith('package.json'):
                await self._update_package_json(file_path, library_name, version)
            elif file_path.endswith('requirements.txt'):
                await self._update_requirements_txt(file_path, library_name, version)
            else:
                raise FileOperationError(f"Unsupported dependency file type: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to update dependency file {file_path}: {e}")
            raise FileOperationError(f"Dependency file update failed: {e}")
    
    async def _update_package_json(
        self,
        file_path: str,
        library_name: str,
        version: str
    ) -> None:
        """
        Update package.json with new dependency
        
        Args:
            file_path: Path to package.json file
            library_name: Name of npm package
            version: Version specifier (e.g., "^18.0.0")
        """
        try:
            # Read existing package.json
            content = await asyncio.to_thread(self.file_manager.read_file, file_path)
            package_data = json.loads(content)
            
            # Ensure dependencies section exists
            if 'dependencies' not in package_data:
                package_data['dependencies'] = {}
            
            # Add new dependency
            package_data['dependencies'][library_name] = version
            
            # Write updated package.json
            updated_content = json.dumps(package_data, indent=2, ensure_ascii=False)
            await asyncio.to_thread(self.file_manager.write_file, file_path, updated_content)
            
            logger.info(f"Added {library_name}@{version} to {file_path}")
            
        except json.JSONDecodeError as e:
            raise FileOperationError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise FileOperationError(f"Failed to update package.json: {e}")
    
    async def _update_requirements_txt(
        self,
        file_path: str,
        library_name: str,
        version: str
    ) -> None:
        """
        Update requirements.txt with new dependency
        
        Args:
            file_path: Path to requirements.txt file
            library_name: Name of PyPI package
            version: Version specifier (e.g., "==4.2.0")
        """
        try:
            # Read existing requirements.txt
            if await asyncio.to_thread(self.file_manager.file_exists, file_path):
                content = await asyncio.to_thread(self.file_manager.read_file, file_path)
                lines = content.strip().split('\n') if content.strip() else []
            else:
                lines = []
            
            # Remove existing entry for this package (if any)
            lines = [line for line in lines if not line.strip().startswith(f"{library_name}==")]
            
            # Add new requirement
            requirement_line = f"{library_name}=={version}"
            lines.append(requirement_line)
            
            # Write updated requirements.txt
            updated_content = '\n'.join(lines) + '\n'
            await asyncio.to_thread(self.file_manager.write_file, file_path, updated_content)
            
            logger.info(f"Added {requirement_line} to {file_path}")
            
        except Exception as e:
            raise FileOperationError(f"Failed to update requirements.txt: {e}")
    
    async def _verify_installation(
        self,
        library_name: str,
        project_context: ProjectContext
    ) -> None:
        """
        Verify that the library was installed successfully
        
        Args:
            library_name: Name of library to verify
            project_context: Project context
            
        Raises:
            InstallationVerificationError: If verification fails
        """
        try:
            config = self.CONTEXT_CONFIG[project_context]
            
            # Execute verification command
            return_code, stdout, stderr = await self.command_executor.execute_command(
                config['verify_command'],
                config['working_dir']
            )
            
            if return_code != 0:
                raise InstallationVerificationError(
                    f"Verification command failed with return code {return_code}. "
                    f"stderr: {stderr}"
                )
            
            # Check if library appears in output
            if library_name not in stdout:
                raise InstallationVerificationError(
                    f"Library {library_name} not found in installed packages"
                )
            
            logger.info(f"Verified installation of {library_name}")
            
        except Exception as e:
            if isinstance(e, InstallationVerificationError):
                raise
            logger.error(f"Failed to verify installation of {library_name}: {e}")
            raise InstallationVerificationError(f"Verification failed: {e}")
    
    async def _update_lock_files(self, project_context: ProjectContext) -> None:
        """
        Update lock files after successful installation
        
        Args:
            project_context: Project context
        """
        try:
            config = self.CONTEXT_CONFIG[project_context]
            lock_file = config['lock_file']
            
            # Check if lock file exists
            if not await asyncio.to_thread(self.file_manager.file_exists, lock_file):
                logger.debug(f"Lock file {lock_file} does not exist, skipping update")
                return
            
            if project_context in [ProjectContext.FRONTEND, ProjectContext.SERVICES]:
                # For npm projects, package-lock.json is updated automatically by npm install
                logger.debug(f"Lock file {lock_file} updated automatically by npm")
            elif project_context == ProjectContext.BACKEND:
                # For Python projects, we might need to update poetry.lock or similar
                # This depends on the specific setup (poetry, pip-tools, etc.)
                logger.debug(f"Lock file {lock_file} handling not implemented for Python projects")
            
        except Exception as e:
            # Lock file update failure is not critical, just log it
            logger.warning(f"Failed to update lock files for {project_context.value}: {e}")
    
    async def rollback(self, backup_path: str) -> None:
        """
        Restore dependency file from backup
        
        Args:
            backup_path: Path to backup file
            
        Raises:
            FileOperationError: If rollback fails
        """
        try:
            logger.info(f"Rolling back changes from backup: {backup_path}")
            self.file_manager.restore_from_backup(backup_path)
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise FileOperationError(f"Rollback failed: {e}")