"""
Database helper utilities to eliminate repetitive query patterns.

This module provides reusable database query functions following the DRY principle.
"""
from typing import TypeVar, Type, Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status


T = TypeVar('T')


async def get_or_404_async(
    db: AsyncSession,
    model: Type[T],
    id_value: Any,
    id_field: str = "id",
    error_message: Optional[str] = None
) -> T:
    """
    Get entity by ID or raise 404 error (async version).
    
    Args:
        db: Async database session
        model: SQLAlchemy model class
        id_value: ID value to search for
        id_field: Name of the ID field (default: "id")
        error_message: Custom error message (default: "{Model} not found")
        
    Returns:
        Model instance
        
    Raises:
        HTTPException: 404 if entity not found
    """
    if error_message is None:
        error_message = f"{model.__name__} not found"
    
    # Convert string UUID to UUID object if needed
    if id_field == "id" and isinstance(id_value, str):
        try:
            id_value = UUID(id_value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {model.__name__} ID format"
            )
    
    stmt = select(model).where(getattr(model, id_field) == id_value)
    result = await db.execute(stmt)
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_message
        )
    
    return entity


def get_or_404_sync(
    db: Session,
    model: Type[T],
    id_value: Any,
    id_field: str = "id",
    error_message: Optional[str] = None
) -> T:
    """
    Get entity by ID or raise 404 error (sync version).
    
    Args:
        db: Sync database session
        model: SQLAlchemy model class
        id_value: ID value to search for
        id_field: Name of the ID field (default: "id")
        error_message: Custom error message (default: "{Model} not found")
        
    Returns:
        Model instance
        
    Raises:
        HTTPException: 404 if entity not found
    """
    if error_message is None:
        error_message = f"{model.__name__} not found"
    
    entity = db.query(model).filter(getattr(model, id_field) == id_value).first()
    
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_message
        )
    
    return entity


async def get_by_field_async(
    db: AsyncSession,
    model: Type[T],
    field_name: str,
    field_value: Any,
    error_if_not_found: bool = False,
    error_message: Optional[str] = None
) -> Optional[T]:
    """
    Get entity by any field (async version).
    
    Args:
        db: Async database session
        model: SQLAlchemy model class
        field_name: Name of the field to search
        field_value: Value to search for
        error_if_not_found: Raise 404 if not found
        error_message: Custom error message
        
    Returns:
        Model instance or None
        
    Raises:
        HTTPException: 404 if entity not found and error_if_not_found=True
    """
    stmt = select(model).where(getattr(model, field_name) == field_value)
    result = await db.execute(stmt)
    entity = result.scalar_one_or_none()
    
    if not entity and error_if_not_found:
        msg = error_message or f"{model.__name__} not found"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg
        )
    
    return entity


def get_by_field_sync(
    db: Session,
    model: Type[T],
    field_name: str,
    field_value: Any,
    error_if_not_found: bool = False,
    error_message: Optional[str] = None
) -> Optional[T]:
    """
    Get entity by any field (sync version).
    
    Args:
        db: Sync database session
        model: SQLAlchemy model class
        field_name: Name of the field to search
        field_value: Value to search for
        error_if_not_found: Raise 404 if not found
        error_message: Custom error message
        
    Returns:
        Model instance or None
        
    Raises:
        HTTPException: 404 if entity not found and error_if_not_found=True
    """
    entity = db.query(model).filter(getattr(model, field_name) == field_value).first()
    
    if not entity and error_if_not_found:
        msg = error_message or f"{model.__name__} not found"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg
        )
    
    return entity


def check_unique_field_sync(
    db: Session,
    model: Type[T],
    field_name: str,
    field_value: Any,
    error_message: Optional[str] = None
) -> None:
    """
    Check if field value is unique, raise 400 if already exists.
    
    Args:
        db: Sync database session
        model: SQLAlchemy model class
        field_name: Name of the field to check
        field_value: Value to check for uniqueness
        error_message: Custom error message
        
    Raises:
        HTTPException: 400 if value already exists
    """
    existing = db.query(model).filter(getattr(model, field_name) == field_value).first()
    
    if existing:
        msg = error_message or f"{field_name.capitalize()} already exists"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )


async def check_unique_field_async(
    db: AsyncSession,
    model: Type[T],
    field_name: str,
    field_value: Any,
    error_message: Optional[str] = None
) -> None:
    """
    Check if field value is unique, raise 400 if already exists (async version).
    
    Args:
        db: Async database session
        model: SQLAlchemy model class
        field_name: Name of the field to check
        field_value: Value to check for uniqueness
        error_message: Custom error message
        
    Raises:
        HTTPException: 400 if value already exists
    """
    stmt = select(model).where(getattr(model, field_name) == field_value)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        msg = error_message or f"{field_name.capitalize()} already exists"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
