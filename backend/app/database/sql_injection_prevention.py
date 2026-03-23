"""
SQL Injection Prevention Utilities

This module provides utilities to prevent SQL injection attacks by:
1. Validating all SQL identifiers (table names, column names)
2. Ensuring parameterized queries are used
3. Providing safe query builders
4. Auditing raw SQL usage

Requirements:
- 2.10: Sanitize all user input to prevent SQL injection attacks
- 8.7: Validate and sanitize all user input to prevent injection attacks
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from functools import wraps
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ClauseElement

logger = logging.getLogger(__name__)


class SQLInjectionError(ValueError):
    """Raised when potential SQL injection is detected"""
    pass


def validate_sql_identifier(identifier: str) -> str:
    """
    Validate SQL identifier (table name, column name, etc.)
    
    Only allows alphanumeric characters and underscores.
    Must start with a letter or underscore.
    
    Args:
        identifier: SQL identifier to validate
        
    Returns:
        Validated identifier
        
    Raises:
        SQLInjectionError: If identifier contains invalid characters
        
    Requirements:
        - 2.10: Prevent SQL injection attacks
        - 8.7: Prevent injection attacks
    """
    if not identifier:
        raise SQLInjectionError("SQL identifier cannot be empty")
    
    # Only allow alphanumeric characters and underscores
    # Must start with letter or underscore
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
        raise SQLInjectionError(
            f"Invalid SQL identifier: '{identifier}'. "
            "Only alphanumeric characters and underscores are allowed, "
            "and it must start with a letter or underscore."
        )
    
    # Check for SQL keywords that shouldn't be used as identifiers
    sql_keywords = {
        'select', 'insert', 'update', 'delete', 'drop', 'create',
        'alter', 'truncate', 'union', 'exec', 'execute'
    }
    
    if identifier.lower() in sql_keywords:
        raise SQLInjectionError(
            f"SQL keyword '{identifier}' cannot be used as an identifier"
        )
    
    return identifier


def validate_order_by(order_by: str, allowed_columns: List[str]) -> str:
    """
    Validate ORDER BY clause to prevent SQL injection
    
    Args:
        order_by: ORDER BY clause (e.g., "name ASC", "created_at DESC")
        allowed_columns: List of allowed column names
        
    Returns:
        Validated ORDER BY clause
        
    Raises:
        SQLInjectionError: If ORDER BY contains invalid content
    """
    if not order_by:
        return ""
    
    # Parse ORDER BY clause
    parts = order_by.strip().split()
    
    if len(parts) == 0:
        return ""
    
    if len(parts) > 2:
        raise SQLInjectionError("Invalid ORDER BY clause format")
    
    column = parts[0]
    direction = parts[1].upper() if len(parts) == 2 else "ASC"
    
    # Validate column name
    if column not in allowed_columns:
        raise SQLInjectionError(
            f"Column '{column}' not allowed in ORDER BY. "
            f"Allowed columns: {', '.join(allowed_columns)}"
        )
    
    # Validate direction
    if direction not in ('ASC', 'DESC'):
        raise SQLInjectionError(
            f"Invalid sort direction: '{direction}'. Must be ASC or DESC"
        )
    
    return f"{column} {direction}"


def validate_limit_offset(limit: Optional[int], offset: Optional[int]) -> Tuple[int, int]:
    """
    Validate LIMIT and OFFSET values
    
    Args:
        limit: LIMIT value
        offset: OFFSET value
        
    Returns:
        Tuple of (validated_limit, validated_offset)
        
    Raises:
        SQLInjectionError: If values are invalid
    """
    # Validate limit
    if limit is not None:
        if not isinstance(limit, int):
            raise SQLInjectionError("LIMIT must be an integer")
        if limit < 0:
            raise SQLInjectionError("LIMIT cannot be negative")
        if limit > 10000:
            raise SQLInjectionError("LIMIT cannot exceed 10000")
    else:
        limit = 100  # Default limit
    
    # Validate offset
    if offset is not None:
        if not isinstance(offset, int):
            raise SQLInjectionError("OFFSET must be an integer")
        if offset < 0:
            raise SQLInjectionError("OFFSET cannot be negative")
    else:
        offset = 0
    
    return limit, offset


def build_safe_where_clause(filters: Dict[str, Any], allowed_columns: List[str]) -> Tuple[str, Dict[str, Any]]:
    """
    Build a safe WHERE clause from filters
    
    Args:
        filters: Dictionary of column: value filters
        allowed_columns: List of allowed column names
        
    Returns:
        Tuple of (where_clause, parameters)
        
    Raises:
        SQLInjectionError: If filters contain invalid columns
        
    Example:
        filters = {"status": "active", "user_id": 123}
        allowed = ["status", "user_id", "created_at"]
        clause, params = build_safe_where_clause(filters, allowed)
        # Returns: ("status = :status AND user_id = :user_id", {"status": "active", "user_id": 123})
    """
    if not filters:
        return "", {}
    
    where_parts = []
    parameters = {}
    
    for column, value in filters.items():
        # Validate column name
        if column not in allowed_columns:
            raise SQLInjectionError(
                f"Column '{column}' not allowed in WHERE clause. "
                f"Allowed columns: {', '.join(allowed_columns)}"
            )
        
        # Use parameterized query
        where_parts.append(f"{column} = :{column}")
        parameters[column] = value
    
    where_clause = " AND ".join(where_parts)
    return where_clause, parameters


def audit_raw_sql(func):
    """
    Decorator to audit raw SQL usage
    
    Logs all raw SQL queries for security review.
    Use this decorator on any function that executes raw SQL.
    
    Requirements:
        - 8.7: Audit SQL query usage
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Log the function call
        logger.warning(
            f"Raw SQL execution in {func.__module__}.{func.__name__}. "
            "Ensure parameterized queries are used."
        )
        return await func(*args, **kwargs)
    
    return wrapper


class SafeQueryBuilder:
    """
    Safe query builder that prevents SQL injection
    
    This class provides methods to build SQL queries safely using
    parameterized queries and validated identifiers.
    
    Requirements:
        - 2.10: Prevent SQL injection attacks
        - 8.7: Prevent injection attacks
    """
    
    def __init__(self, table_name: str, allowed_columns: List[str]):
        """
        Initialize safe query builder
        
        Args:
            table_name: Name of the table
            allowed_columns: List of allowed column names
        """
        self.table_name = validate_sql_identifier(table_name)
        self.allowed_columns = [validate_sql_identifier(col) for col in allowed_columns]
    
    def build_select(
        self,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a safe SELECT query
        
        Args:
            columns: List of columns to select (None = all)
            filters: Dictionary of column: value filters
            order_by: ORDER BY clause
            limit: LIMIT value
            offset: OFFSET value
            
        Returns:
            Tuple of (query_string, parameters)
        """
        # Validate and build SELECT clause
        if columns:
            validated_columns = [
                validate_sql_identifier(col) for col in columns
                if col in self.allowed_columns
            ]
            if not validated_columns:
                raise SQLInjectionError("No valid columns specified")
            select_clause = ", ".join(validated_columns)
        else:
            select_clause = "*"
        
        query = f"SELECT {select_clause} FROM {self.table_name}"
        parameters = {}
        
        # Add WHERE clause
        if filters:
            where_clause, where_params = build_safe_where_clause(filters, self.allowed_columns)
            if where_clause:
                query += f" WHERE {where_clause}"
                parameters.update(where_params)
        
        # Add ORDER BY clause
        if order_by:
            validated_order = validate_order_by(order_by, self.allowed_columns)
            if validated_order:
                query += f" ORDER BY {validated_order}"
        
        # Add LIMIT and OFFSET
        validated_limit, validated_offset = validate_limit_offset(limit, offset)
        query += f" LIMIT {validated_limit} OFFSET {validated_offset}"
        
        return query, parameters
    
    def build_count(self, filters: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Build a safe COUNT query
        
        Args:
            filters: Dictionary of column: value filters
            
        Returns:
            Tuple of (query_string, parameters)
        """
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        parameters = {}
        
        if filters:
            where_clause, where_params = build_safe_where_clause(filters, self.allowed_columns)
            if where_clause:
                query += f" WHERE {where_clause}"
                parameters.update(where_params)
        
        return query, parameters


async def execute_safe_query(
    db: AsyncSession,
    query: str,
    parameters: Dict[str, Any]
) -> Any:
    """
    Execute a parameterized query safely
    
    Args:
        db: Database session
        query: SQL query with parameter placeholders
        parameters: Query parameters
        
    Returns:
        Query result
        
    Requirements:
        - 2.10: Use parameterized queries
    """
    try:
        result = await db.execute(text(query), parameters)
        return result
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Parameters: {parameters}")
        raise


def validate_sqlalchemy_query(query: ClauseElement) -> bool:
    """
    Validate that a SQLAlchemy query uses parameterized queries
    
    Args:
        query: SQLAlchemy query object
        
    Returns:
        True if query is safe, False otherwise
    """
    # Compile the query to check for parameter binding
    compiled = query.compile(compile_kwargs={"literal_binds": False})
    
    # Check if query has parameters (good - using parameterized queries)
    has_params = bool(compiled.params)
    
    # Check for string concatenation patterns (bad - potential SQL injection)
    query_str = str(compiled)
    dangerous_patterns = [
        r'\+\s*["\']',  # String concatenation with +
        r'%s',          # Python string formatting
        r'\.format\(',  # String format method
        r'f["\']',      # f-strings
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query_str):
            logger.warning(f"Potential SQL injection pattern detected: {pattern}")
            return False
    
    return True


# Export all public functions and classes
__all__ = [
    'SQLInjectionError',
    'validate_sql_identifier',
    'validate_order_by',
    'validate_limit_offset',
    'build_safe_where_clause',
    'audit_raw_sql',
    'SafeQueryBuilder',
    'execute_safe_query',
    'validate_sqlalchemy_query',
]
