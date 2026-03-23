"""
Library Repository Service for database operations on library metadata
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.exc import IntegrityError

from app.models.library import Library, LibraryDependency, ProjectContext
from app.schemas.library import InstalledLibrary, Dependency
from app.core.logging import get_logger

logger = get_logger(__name__)


class LibraryRepository:
    """Database operations for library metadata"""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session
        
        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    async def save_library(self, library: InstalledLibrary) -> int:
        """
        Insert library record into database
        
        Args:
            library: Library information to store
            
        Returns:
            int: ID of the created library record
            
        Raises:
            ValueError: If unique constraint violation occurs
            RuntimeError: If database operation fails
        """
        try:
            # Create library record
            db_library = Library(
                project_id=library.project_id,
                name=library.name,
                version=library.version,
                registry_type=library.registry_type,
                project_context=library.project_context,
                description=library.description,
                license=library.license,
                installed_at=library.installed_at,
                installed_by=library.installed_by,
                uri=library.uri,
                library_metadata=library.metadata or {}
            )
            
            self.db.add(db_library)
            await self.db.flush()  # Get the ID without committing
            
            library_id = db_library.id
            
            logger.info(
                f"Library saved: {library.name}@{library.version} "
                f"(ID: {library_id}, project: {library.project_id}, "
                f"context: {library.project_context.value})"
            )
            
            return library_id
            
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            if "unique constraint" in error_msg.lower():
                raise ValueError(
                    f"Library {library.name} is already installed in "
                    f"{library.project_context.value} context for project {library.project_id}"
                )
            else:
                logger.error(f"Database integrity error saving library: {error_msg}")
                raise RuntimeError(f"Failed to save library: {error_msg}")
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error saving library: {e}")
            raise RuntimeError(f"Failed to save library: {str(e)}")

    async def get_libraries_by_project(
        self,
        project_id: str,
        context: Optional[ProjectContext] = None
    ) -> List[InstalledLibrary]:
        """
        Query installed libraries for a project
        
        Args:
            project_id: Project identifier
            context: Optional project context filter
            
        Returns:
            List[InstalledLibrary]: List of installed libraries
        """
        try:
            # Build query
            query = select(Library).where(Library.project_id == project_id)
            
            if context:
                query = query.where(Library.project_context == context)
            
            # Order by installation date (newest first)
            query = query.order_by(Library.installed_at.desc())
            
            # Execute query
            result = await self.db.execute(query)
            db_libraries = result.scalars().all()
            
            # Convert to schema objects
            libraries = []
            for db_lib in db_libraries:
                library = InstalledLibrary(
                    id=db_lib.id,
                    project_id=db_lib.project_id,
                    name=db_lib.name,
                    version=db_lib.version,
                    registry_type=db_lib.registry_type,
                    project_context=db_lib.project_context,
                    description=db_lib.description or "",
                    license=db_lib.license or "",
                    installed_at=db_lib.installed_at,
                    installed_by=db_lib.installed_by,
                    uri=db_lib.uri,
                    metadata=db_lib.library_metadata
                )
                libraries.append(library)
            
            logger.info(
                f"Retrieved {len(libraries)} libraries for project {project_id}"
                f"{f' (context: {context.value})' if context else ''}"
            )
            
            return libraries
            
        except Exception as e:
            logger.error(f"Error retrieving libraries for project {project_id}: {e}")
            raise RuntimeError(f"Failed to retrieve libraries: {str(e)}")

    async def get_library_by_name(
        self,
        project_id: str,
        name: str,
        context: ProjectContext
    ) -> Optional[InstalledLibrary]:
        """
        Get specific library by name and context
        
        Args:
            project_id: Project identifier
            name: Library name
            context: Project context
            
        Returns:
            Optional[InstalledLibrary]: Library if found, None otherwise
        """
        try:
            query = select(Library).where(
                and_(
                    Library.project_id == project_id,
                    Library.name == name,
                    Library.project_context == context
                )
            )
            
            result = await self.db.execute(query)
            db_library = result.scalar_one_or_none()
            
            if not db_library:
                logger.debug(
                    f"Library not found: {name} in {context.value} "
                    f"context for project {project_id}"
                )
                return None
            
            library = InstalledLibrary(
                id=db_library.id,
                project_id=db_library.project_id,
                name=db_library.name,
                version=db_library.version,
                registry_type=db_library.registry_type,
                project_context=db_library.project_context,
                description=db_library.description or "",
                license=db_library.license or "",
                installed_at=db_library.installed_at,
                installed_by=db_library.installed_by,
                uri=db_library.uri,
                metadata=db_library.library_metadata
            )
            
            logger.debug(
                f"Found library: {name}@{library.version} "
                f"(ID: {library.id})"
            )
            
            return library
            
        except Exception as e:
            logger.error(
                f"Error retrieving library {name} for project {project_id}: {e}"
            )
            raise RuntimeError(f"Failed to retrieve library: {str(e)}")

    async def update_library_version(
        self,
        library_id: int,
        new_version: str
    ) -> None:
        """
        Update library version
        
        Args:
            library_id: Library record ID
            new_version: New version string
            
        Raises:
            ValueError: If library not found
            RuntimeError: If database operation fails
        """
        try:
            # Check if library exists
            query = select(Library).where(Library.id == library_id)
            result = await self.db.execute(query)
            db_library = result.scalar_one_or_none()
            
            if not db_library:
                raise ValueError(f"Library with ID {library_id} not found")
            
            # Update version
            update_query = (
                update(Library)
                .where(Library.id == library_id)
                .values(version=new_version)
            )
            
            await self.db.execute(update_query)
            
            logger.info(
                f"Updated library version: {db_library.name} "
                f"{db_library.version} -> {new_version} (ID: {library_id})"
            )
            
        except ValueError:
            raise  # Re-raise ValueError as-is
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating library version: {e}")
            raise RuntimeError(f"Failed to update library version: {str(e)}")

    async def save_dependencies(
        self,
        library_id: int,
        dependencies: List[Dependency]
    ) -> None:
        """
        Save library dependencies to library_dependencies table
        
        Args:
            library_id: Library record ID
            dependencies: List of dependencies to save
            
        Raises:
            ValueError: If library not found
            RuntimeError: If database operation fails
        """
        try:
            # Check if library exists
            query = select(Library).where(Library.id == library_id)
            result = await self.db.execute(query)
            db_library = result.scalar_one_or_none()
            
            if not db_library:
                raise ValueError(f"Library with ID {library_id} not found")
            
            # Delete existing dependencies for this library
            delete_query = delete(LibraryDependency).where(
                LibraryDependency.library_id == library_id
            )
            await self.db.execute(delete_query)
            
            # Insert new dependencies
            for dep in dependencies:
                db_dependency = LibraryDependency(
                    library_id=library_id,
                    dependency_name=dep.name,
                    dependency_version=dep.version,
                    is_direct=dep.is_direct
                )
                self.db.add(db_dependency)
            
            logger.info(
                f"Saved {len(dependencies)} dependencies for library "
                f"{db_library.name} (ID: {library_id})"
            )
            
        except ValueError:
            raise  # Re-raise ValueError as-is
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error saving dependencies: {e}")
            raise RuntimeError(f"Failed to save dependencies: {str(e)}")

    async def get_library_dependencies(
        self,
        library_id: int
    ) -> List[Dependency]:
        """
        Get dependencies for a library
        
        Args:
            library_id: Library record ID
            
        Returns:
            List[Dependency]: List of library dependencies
            
        Raises:
            ValueError: If library not found
            RuntimeError: If database operation fails
        """
        try:
            # Check if library exists
            library_query = select(Library).where(Library.id == library_id)
            library_result = await self.db.execute(library_query)
            db_library = library_result.scalar_one_or_none()
            
            if not db_library:
                raise ValueError(f"Library with ID {library_id} not found")
            
            # Get dependencies
            deps_query = select(LibraryDependency).where(
                LibraryDependency.library_id == library_id
            ).order_by(LibraryDependency.dependency_name)
            
            result = await self.db.execute(deps_query)
            db_dependencies = result.scalars().all()
            
            # Convert to schema objects
            dependencies = []
            for db_dep in db_dependencies:
                dependency = Dependency(
                    name=db_dep.dependency_name,
                    version=db_dep.dependency_version,
                    is_direct=db_dep.is_direct
                )
                dependencies.append(dependency)
            
            logger.debug(
                f"Retrieved {len(dependencies)} dependencies for library "
                f"{db_library.name} (ID: {library_id})"
            )
            
            return dependencies
            
        except ValueError:
            raise  # Re-raise ValueError as-is
        except Exception as e:
            logger.error(f"Error retrieving dependencies: {e}")
            raise RuntimeError(f"Failed to retrieve dependencies: {str(e)}")

    async def delete_library(
        self,
        library_id: int
    ) -> bool:
        """
        Delete library and its dependencies
        
        Args:
            library_id: Library record ID
            
        Returns:
            bool: True if library was deleted, False if not found
            
        Raises:
            RuntimeError: If database operation fails
        """
        try:
            # Check if library exists
            query = select(Library).where(Library.id == library_id)
            result = await self.db.execute(query)
            db_library = result.scalar_one_or_none()
            
            if not db_library:
                logger.debug(f"Library with ID {library_id} not found for deletion")
                return False
            
            library_name = db_library.name
            library_version = db_library.version
            
            # Delete library (dependencies will be cascade deleted)
            delete_query = delete(Library).where(Library.id == library_id)
            await self.db.execute(delete_query)
            
            logger.info(
                f"Deleted library: {library_name}@{library_version} "
                f"(ID: {library_id})"
            )
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting library: {e}")
            raise RuntimeError(f"Failed to delete library: {str(e)}")

    async def get_libraries_by_user(
        self,
        installed_by: str,
        project_id: Optional[str] = None
    ) -> List[InstalledLibrary]:
        """
        Get libraries installed by a specific user
        
        Args:
            installed_by: User identifier
            project_id: Optional project filter
            
        Returns:
            List[InstalledLibrary]: List of libraries installed by user
        """
        try:
            query = select(Library).where(Library.installed_by == installed_by)
            
            if project_id:
                query = query.where(Library.project_id == project_id)
            
            # Order by installation date (newest first)
            query = query.order_by(Library.installed_at.desc())
            
            result = await self.db.execute(query)
            db_libraries = result.scalars().all()
            
            # Convert to schema objects
            libraries = []
            for db_lib in db_libraries:
                library = InstalledLibrary(
                    id=db_lib.id,
                    project_id=db_lib.project_id,
                    name=db_lib.name,
                    version=db_lib.version,
                    registry_type=db_lib.registry_type,
                    project_context=db_lib.project_context,
                    description=db_lib.description or "",
                    license=db_lib.license or "",
                    installed_at=db_lib.installed_at,
                    installed_by=db_lib.installed_by,
                    uri=db_lib.uri,
                    metadata=db_lib.library_metadata
                )
                libraries.append(library)
            
            logger.info(
                f"Retrieved {len(libraries)} libraries installed by user {installed_by}"
                f"{f' in project {project_id}' if project_id else ''}"
            )
            
            return libraries
            
        except Exception as e:
            logger.error(f"Error retrieving libraries by user {installed_by}: {e}")
            raise RuntimeError(f"Failed to retrieve libraries: {str(e)}")

    async def get_libraries_by_date_range(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime,
        context: Optional[ProjectContext] = None
    ) -> List[InstalledLibrary]:
        """
        Get libraries installed within a date range
        
        Args:
            project_id: Project identifier
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            context: Optional project context filter
            
        Returns:
            List[InstalledLibrary]: List of libraries installed in date range
        """
        try:
            query = select(Library).where(
                and_(
                    Library.project_id == project_id,
                    Library.installed_at >= start_date,
                    Library.installed_at <= end_date
                )
            )
            
            if context:
                query = query.where(Library.project_context == context)
            
            # Order by installation date (newest first)
            query = query.order_by(Library.installed_at.desc())
            
            result = await self.db.execute(query)
            db_libraries = result.scalars().all()
            
            # Convert to schema objects
            libraries = []
            for db_lib in db_libraries:
                library = InstalledLibrary(
                    id=db_lib.id,
                    project_id=db_lib.project_id,
                    name=db_lib.name,
                    version=db_lib.version,
                    registry_type=db_lib.registry_type,
                    project_context=db_lib.project_context,
                    description=db_lib.description or "",
                    license=db_lib.license or "",
                    installed_at=db_lib.installed_at,
                    installed_by=db_lib.installed_by,
                    uri=db_lib.uri,
                    metadata=db_lib.library_metadata
                )
                libraries.append(library)
            
            logger.info(
                f"Retrieved {len(libraries)} libraries for project {project_id} "
                f"between {start_date} and {end_date}"
                f"{f' (context: {context.value})' if context else ''}"
            )
            
            return libraries
            
        except Exception as e:
            logger.error(
                f"Error retrieving libraries by date range for project {project_id}: {e}"
            )
            raise RuntimeError(f"Failed to retrieve libraries: {str(e)}")