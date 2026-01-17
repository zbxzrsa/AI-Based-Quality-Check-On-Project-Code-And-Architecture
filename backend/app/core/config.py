"""
Application configuration settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings with secure environment variable handling"""

    # Application
    PROJECT_NAME: str = "AI Code Review Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # ========================================
    # REQUIRED SECRETS (will raise error if missing)
    # ========================================

    # Security - REQUIRED for application to start
    JWT_SECRET: str  # JWT signing secret
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # PostgreSQL - REQUIRED database connection
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str  # REQUIRED

    # Neo4j - REQUIRED graph database
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str  # REQUIRED
    NEO4J_DATABASE: str = "neo4j"

    # Redis - REQUIRED cache/session store
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str  # REQUIRED
    REDIS_DB: int = 0

    # ========================================
    # OPTIONAL SECRETS (can be None/disabled)
    # ========================================

    # External APIs - Optional integrations
    GITHUB_TOKEN: Optional[str] = None  # For GitHub API access
    GITHUB_WEBHOOK_SECRET: Optional[str] = None  # For webhook verification
    OPENAI_API_KEY: Optional[str] = None  # For OpenAI integration
    ANTHROPIC_API_KEY: Optional[str] = None  # For Anthropic Claude

    # ========================================
    # NON-SECRETS (safe to expose)
    # ========================================

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://frontend:3000",
    ]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    NODE_ENV: str = "development"

    # ========================================
    # COMPUTED PROPERTIES
    # ========================================

    @property
    def postgres_url(self) -> str:
        """PostgreSQL async connection URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_postgres_url(self) -> str:
        """PostgreSQL sync connection URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        """Redis connection URL with authentication"""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def celery_broker_url(self) -> str:
        """Celery broker URL (Redis)"""
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        """Celery result backend URL (Redis)"""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    # ========================================
    # VALIDATION METHODS
    # ========================================

    def validate_security_settings(self) -> List[str]:
        """Validate security-related settings and return warnings"""
        warnings = []

        if len(self.JWT_SECRET) < 32:
            warnings.append("JWT_SECRET should be at least 32 characters long")

        if self.JWT_EXPIRATION_HOURS > 168:  # 1 week
            warnings.append("JWT_EXPIRATION_HOURS is very long (>1 week)")

        if not self.GITHUB_TOKEN and not self.OPENAI_API_KEY and not self.ANTHROPIC_API_KEY:
            warnings.append("No external API keys configured - limited functionality")

        return warnings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra environment variables
    )


settings = Settings()
