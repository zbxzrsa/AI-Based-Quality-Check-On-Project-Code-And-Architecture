"""
Database configuration validation with environment variable support.
"""

import os
from typing import List
from app.database.models import DatabaseConfig, CompatibilityResult, get_python_version


class ConfigurationValidator:
    """Validates database configuration settings and environment variables."""
    
    REQUIRED_ENV_VARS = {
        'POSTGRES_HOST': 'PostgreSQL host address',
        'POSTGRES_DB': 'PostgreSQL database name',
        'POSTGRES_USER': 'PostgreSQL username',
        'POSTGRES_PASSWORD': 'PostgreSQL password',
        'NEO4J_URI': 'Neo4j connection URI',
        'NEO4J_USER': 'Neo4j username',
        'NEO4J_PASSWORD': 'Neo4j password',
        'REDIS_HOST': 'Redis host address'
    }
    
    def validate_environment_variables(self) -> List[str]:
        """Validate that all required environment variables are present."""
        errors = []
        
        for var_name, description in self.REQUIRED_ENV_VARS.items():
            value = os.environ.get(var_name)
            if not value or not value.strip():
                errors.append(
                    f"Required environment variable '{var_name}' is missing or empty. "
                    f"Description: {description}"
                )
        
        return errors
    
    def check_python_asyncpg_compatibility(self) -> CompatibilityResult:
        """Check Python and asyncpg version compatibility."""
        python_version = get_python_version()
        issues = []
        recommendations = []
        
        try:
            import asyncpg
            asyncpg_version = asyncpg.__version__
        except ImportError:
            return CompatibilityResult(
                is_compatible=False,
                python_version=python_version,
                asyncpg_version="not installed",
                issues=["asyncpg is not installed"],
                recommendations=["Install asyncpg: pip install asyncpg"]
            )
        
        is_compatible = len(issues) == 0
        
        return CompatibilityResult(
            is_compatible=is_compatible,
            python_version=python_version,
            asyncpg_version=asyncpg_version,
            issues=issues,
            recommendations=recommendations
        )
    
    def validate_database_config(self, config: DatabaseConfig) -> List[str]:
        """Validate a DatabaseConfig object."""
        errors = []
        
        if not config.postgresql_dsn or not config.postgresql_dsn.strip():
            errors.append("PostgreSQL DSN cannot be empty")
        
        if not config.neo4j_uri or not config.neo4j_uri.strip():
            errors.append("Neo4j URI cannot be empty")
        
        return errors
    
    def validate_configuration_conflicts(self) -> List[str]:
        """Check for configuration conflicts that would prevent startup."""
        conflicts = []
        
        environment = os.environ.get('ENVIRONMENT', 'development')
        
        if environment == 'production':
            jwt_secret = os.environ.get('JWT_SECRET', '')
            if len(jwt_secret) < 32:
                conflicts.append(
                    "Security conflict: JWT_SECRET must be at least 32 characters in production"
                )
            
            # Production database requirements
            if os.environ.get('POSTGRES_PASSWORD') == 'password':
                conflicts.append(
                    "Security conflict: Default password 'password' not allowed in production"
                )
            
            if os.environ.get('NEO4J_PASSWORD') == 'password':
                conflicts.append(
                    "Security conflict: Default Neo4j password 'password' not allowed in production"
                )
        
        # Pool size conflicts
        try:
            pool_min = int(os.environ.get('DB_POOL_MIN_SIZE', 5))
            pool_max = int(os.environ.get('DB_POOL_MAX_SIZE', 20))
            if pool_max < pool_min:
                conflicts.append(
                    f"Configuration conflict: DB_POOL_MAX_SIZE ({pool_max}) must be >= DB_POOL_MIN_SIZE ({pool_min})"
                )
        except (ValueError, TypeError):
            pass  # Invalid values will be caught by other validation
        
        # Retry configuration conflicts
        try:
            base_delay = float(os.environ.get('DB_RETRY_BASE_DELAY', 1.0))
            max_delay = float(os.environ.get('DB_RETRY_MAX_DELAY', 60.0))
            if max_delay < base_delay:
                conflicts.append(
                    f"Configuration conflict: DB_RETRY_MAX_DELAY ({max_delay}) must be >= DB_RETRY_BASE_DELAY ({base_delay})"
                )
        except (ValueError, TypeError):
            # If we can't parse the values, that's also a conflict
            base_delay_str = os.environ.get('DB_RETRY_BASE_DELAY', '1.0')
            max_delay_str = os.environ.get('DB_RETRY_MAX_DELAY', '60.0')
            conflicts.append(
                f"Configuration conflict: Invalid retry delay values - DB_RETRY_BASE_DELAY='{base_delay_str}', DB_RETRY_MAX_DELAY='{max_delay_str}'"
            )
        
        return conflicts
    
    def get_configuration_template(self, environment: str = 'development') -> dict:
        """Get configuration template with recommended values for environment."""
        templates = {
            'development': {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_PORT': '5432',
                'POSTGRES_DB': 'ai_code_review_dev',
                'POSTGRES_USER': 'dev_user',
                'POSTGRES_PASSWORD': 'dev_password',
                'NEO4J_URI': 'bolt://localhost:7687',
                'NEO4J_USER': 'neo4j',
                'NEO4J_PASSWORD': 'dev_password',
                'REDIS_HOST': 'localhost',
                'REDIS_PORT': '6379',
                'REDIS_PASSWORD': '',
                'DB_CONNECTION_TIMEOUT': '30',
                'DB_POOL_MIN_SIZE': '5',
                'DB_POOL_MAX_SIZE': '20',
                'DB_MAX_RETRIES': '3',
                'DB_RETRY_BASE_DELAY': '1.0',
                'DB_RETRY_MAX_DELAY': '60.0',
                'DB_RETRY_BACKOFF_MULTIPLIER': '2.0'
            },
            'staging': {
                'POSTGRES_HOST': 'staging-postgres.example.com',
                'POSTGRES_PORT': '5432',
                'POSTGRES_DB': 'ai_code_review_staging',
                'POSTGRES_USER': 'staging_user',
                'POSTGRES_PASSWORD': '${POSTGRES_PASSWORD}',
                'NEO4J_URI': 'bolt://staging-neo4j.example.com:7687',
                'NEO4J_USER': 'neo4j',
                'NEO4J_PASSWORD': '${NEO4J_PASSWORD}',
                'REDIS_HOST': 'staging-redis.example.com',
                'REDIS_PORT': '6379',
                'REDIS_PASSWORD': '${REDIS_PASSWORD}',
                'DB_CONNECTION_TIMEOUT': '30',
                'DB_POOL_MIN_SIZE': '10',
                'DB_POOL_MAX_SIZE': '50',
                'DB_MAX_RETRIES': '5',
                'DB_RETRY_BASE_DELAY': '1.0',
                'DB_RETRY_MAX_DELAY': '120.0',
                'DB_RETRY_BACKOFF_MULTIPLIER': '2.0'
            },
            'production': {
                'POSTGRES_HOST': 'prod-postgres.example.com',
                'POSTGRES_PORT': '5432',
                'POSTGRES_DB': 'ai_code_review_prod',
                'POSTGRES_USER': 'prod_user',
                'POSTGRES_PASSWORD': '${POSTGRES_PASSWORD}',
                'NEO4J_URI': 'bolt+s://prod-neo4j.example.com:7687',
                'NEO4J_USER': 'neo4j',
                'NEO4J_PASSWORD': '${NEO4J_PASSWORD}',
                'REDIS_HOST': 'prod-redis.example.com',
                'REDIS_PORT': '6379',
                'REDIS_PASSWORD': '${REDIS_PASSWORD}',
                'DB_CONNECTION_TIMEOUT': '60',
                'DB_POOL_MIN_SIZE': '20',
                'DB_POOL_MAX_SIZE': '100',
                'DB_MAX_RETRIES': '5',
                'DB_RETRY_BASE_DELAY': '2.0',
                'DB_RETRY_MAX_DELAY': '300.0',
                'DB_RETRY_BACKOFF_MULTIPLIER': '2.5'
            }
        }
        
        return templates.get(environment, templates['development'])