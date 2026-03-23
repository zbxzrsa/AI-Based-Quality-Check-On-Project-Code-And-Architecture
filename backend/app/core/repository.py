"""
Base Repository Pattern for Database Operations

Provides a generic repository base class that eliminates repetitive CRUD patterns
and database transaction management code throughout the codebase.

Example:
    class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
        def __init__(self, db: Session):
            super().__init__(User, db)
        
        async def get_by_email(self, email: str) -> Optional[User]:
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
"""

from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from fastapi import HTTPException

ModelType = TypeVar("ModelType", bound=Any)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic repository base class for database CRUD operations.
    
    Provides common database operations with automatic error handling
    and transaction management.
    
    Attributes:
        model: The SQLAlchemy model class
        db: The async database session
    
    Example:
        class ProjectRepository(BaseRepository[Project, ProjectCreate, ProjectUpdate]):
            async def get_by_name(self, name: str) -> Optional[Project]:
                result = await self.db.execute(
                    select(Project).where(Project.name == name)
                )
                return result.scalar_one_or_none()
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Initialize the repository.
        
        Args:
            model: The SQLAlchemy model class
            db: The async database session
        """
        self.model = model
        self.db = db

    async def get(self, id: str) -> Optional[ModelType]:
        """
        Get a single record by ID.
        
        Args:
            id: The record ID
            
        Returns:
            The model instance or None if not found
        """
        try:
            result = await self.db.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        **filters: Any
    ) -> List[ModelType]:
        """
        Get multiple records with optional filtering and pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Additional filter criteria
            
        Returns:
            List of model instances
        """
        try:
            query = select(self.model)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)
            
            query = query.offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            await self.db.rollback()
            raise e

    async def create(self, schema: CreateSchemaType) -> ModelType:
        """
        Create a new record.
        
        Args:
            schema: The creation schema with data
            
        Returns:
            The created model instance
        """
        try:
            instance = self.model(**schema.model_dump())
            self.db.add(instance)
            await self.db.commit()
            await self.db.refresh(instance)
            return instance
        except Exception as e:
            await self.db.rollback()
            raise e

    async def update(
        self, 
        id: str, 
        schema: UpdateSchemaType,
        raise_not_found: bool = True
    ) -> Optional[ModelType]:
        """
        Update an existing record.
        
        Args:
            id: The record ID
            schema: The update schema with data
            raise_not_found: Whether to raise 404 if record not found
            
        Returns:
            The updated model instance or None if not found
        """
        try:
            instance = await self.get(id)
            
            if not instance:
                if raise_not_found:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"{self.model.__name__} not found"
                    )
                return None
            
            update_data = schema.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(instance, key, value)
            
            await self.db.commit()
            await self.db.refresh(instance)
            return instance
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete(self, id: str, raise_not_found: bool = True) -> bool:
        """
        Delete a record.
        
        Args:
            id: The record ID
            raise_not_found: Whether to raise 404 if record not found
            
        Returns:
            True if deleted, False if not found
        """
        try:
            instance = await self.get(id)
            
            if not instance:
                if raise_not_found:
                    raise HTTPException(
                        status_code=404,
                        detail=f"{self.model.__name__} not found"
                    )
                return False
            
            await self.db.delete(instance)
            await self.db.commit()
            return True
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise e

    async def exists(self, id: str) -> bool:
        """
        Check if a record exists.
        
        Args:
            id: The record ID
            
        Returns:
            True if exists, False otherwise
        """
        instance = await self.get(id)
        return instance is not None
