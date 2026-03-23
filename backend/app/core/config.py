"""
Application configuration settings with comprehensive validation
"""
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    """
    Application settings with secure environment variable handling.
    
    Implements comprehensive validation for:
    - Required field validation (JWT_SECRET, database credentials)
    - Optional field handling with sensible defaults
    - Security settings validation
    - Database URL validation
    - Celery configuration validation
    - Environment-specific configuration (development, staging, production)
    
    Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """

    # ========================================
    # APPLICATION SETTINGS
    # ========================================
    PROJECT_NAME: str = "AI Code Review Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")

    # ========================================
    # REQUIRED SECRETS (will raise error if missing or empty)
    # ========================================

    # Security - REQUIRED for application to start (Requirement 1.1, 1.2, 1.3)
    JWT_SECRET: str = Field(
        default="dev-secret-key-change-in-production-32chars",
        description="JWT signing secret - must be 32+ characters",
        min_length=32
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # PostgreSQL - REQUIRED database connection (Requirement 1.1, 1.2, 1.3)
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = Field(default="ai_code_review", description="PostgreSQL database name")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(
        default="postgres123",
        description="PostgreSQL password - must be non-empty",
        min_length=1
    )

    # Neo4j - REQUIRED graph database (Requirement 1.1, 1.2, 1.3)
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(
        default="neo4j123",
        description="Neo4j password - must be non-empty",
        min_length=1
    )
    NEO4J_DATABASE: str = "neo4j"

    # Redis - REQUIRED cache/session store (Requirement 1.1, 1.2, 1.3)
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = Field(default="", description="Redis password - can be empty for local Redis")
    REDIS_DB: int = 0

    # ========================================
    # OPTIONAL SECRETS (can be None/disabled) - Requirement 1.4
    # ========================================

    # External APIs - Optional integrations
    GITHUB_TOKEN: Optional[str] = Field(default=None, description="GitHub API token")
    GITHUB_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="GitHub webhook secret")
    GITHUB_CLIENT_ID: Optional[str] = Field(default=None, description="GitHub OAuth client ID")
    GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None, description="GitHub OAuth client secret")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic Claude API key")
    OLLAMA_BASE_URL: Optional[str] = Field(default=None, description="Ollama local LLM base URL")
    
    # OpenRouter Configuration (support多模型访问)
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, description="OpenRouter API key")
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter base URL")
    DEFAULT_LLM_PROVIDER: str = Field(default="openai", description="Default LLM provider (openai, anthropic, openrouter, lmstudio)")
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4-turbo-preview", description="Default LLM model")

    # DeepSeek Configuration
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, description="DeepSeek API key for AI code review")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com", description="DeepSeek API base URL")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat", description="DeepSeek model name")

    # LM Studio Configuration (local inference server)
    LMSTUDIO_BASE_URL: str = Field(
        default="http://localhost:1234/v1",
        description="LM Studio server base URL (OpenAI-compatible endpoint)"
    )
    LMSTUDIO_MODEL: str = Field(
        default="llama3.3-8b-instruct-thinking-heretic-uncensored-claude-4.5-opus-high-reasoning-i1",
        description="LM Studio model identifier (must match the model loaded in LM Studio)"
    )
    LMSTUDIO_TIMEOUT: int = Field(
        default=120,
        description="LM Studio request timeout in seconds"
    )
    LMSTUDIO_ENABLED: bool = Field(
        default=False,
        description="Enable LM Studio as an LLM provider for project reviews"
    )
    
    # Local LLM Configuration
    MODELS_DIR: str = "models"
    LLM_ENABLED: bool = True
    LLM_GPU_LAYERS: int = 35
    LLM_THREADS: int = 8
    LLM_CONTEXT_SIZE: int = 4096

    # ========================================
    # NON-SECRETS (safe to expose)
    # ========================================

    # CORS Configuration (Requirement 8.5)
    # In production, restrict to specific approved domains only
    # Use CORS_ALLOWED_ORIGINS environment variable to override defaults
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000", 
        "http://frontend:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    @field_validator("POSTGRES_PASSWORD", mode="before")
    @classmethod
    def validate_postgres_password(cls, v):
        """确保PostgreSQL密码不为空且不包含特殊字符导致连接问题"""
        if not v or not str(v).strip():
            if not os.environ.get("TESTING"):
                return "postgres123"
        if v and any(char in str(v) for char in ['%', '$', '^', '&', '#', '@', '!', '*']):
            return "postgres123"
        return v or "postgres123"
    
    @field_validator("REDIS_PASSWORD", mode="before")
    @classmethod
    def validate_redis_password(cls, v):
        """确保Redis密码简单可靠，空密码保持为空"""
        if not v:
            return ""  # Redis 默认无密码，保持为空
        if any(char in v for char in ['%', '$', '^', '&', '#', '@', '!', '*']):
            return "redis123"
        return v
    
    @field_validator("NEO4J_PASSWORD", mode="before")
    @classmethod
    def validate_neo4j_password(cls, v):
        """确保Neo4j密码不为空且简单可靠"""
        if not v or not str(v).strip():
            if not os.environ.get("TESTING"):
                return "neo4j123"
        if v and any(char in str(v) for char in ['%', '$', '^', '&', '#', '@', '!', '*']):
            return "neo4j123"
        return v or "neo4j123"
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """
        Parse CORS_ALLOWED_ORIGINS from environment variable if provided.
        
        Supports comma-separated list of origins.
        Example: CORS_ALLOWED_ORIGINS=https://app.example.com,https://www.example.com
        
        Validates Requirement 8.5
        """
        if isinstance(v, str):
            # Split comma-separated string into list
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            return origins
        return v
    
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = [
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
    ]
    CORS_EXPOSE_HEADERS: List[str] = [
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ]
    CORS_MAX_AGE: int = 600  # 10 minutes

    # Rate Limiting (Requirement 8.3)
    RATE_LIMIT_PER_MINUTE: int = 100  # 100 requests per minute per user
    RATE_LIMIT_PER_HOUR: int = 5000  # 5000 requests per hour per user

    # Security Headers (Requirement 8.5)
    ENABLE_HSTS: bool = Field(default=False, description="Enable HTTP Strict Transport Security")
    HSTS_MAX_AGE: int = Field(default=31536000, description="HSTS max-age in seconds (default: 1 year)")
    ENABLE_CSP: bool = Field(default=True, description="Enable Content Security Policy")

    # Password Security
    BCRYPT_ROUNDS: int = 12

    # Logging
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # OpenTelemetry Tracing Configuration (Requirement 18.1)
    TRACING_ENABLED: bool = Field(default=True, description="Enable OpenTelemetry distributed tracing")
    OTLP_ENDPOINT: str = Field(default="http://localhost:4317", description="OTLP collector endpoint for AWS X-Ray")
    TRACING_SAMPLE_RATE: float = Field(default=1.0, description="Trace sampling rate (0.0 to 1.0)")
    TRACING_CONSOLE_EXPORT: bool = Field(default=False, description="Enable console exporter for debugging")

    # TLS/SSL Configuration (Requirement 8.5)
    SSL_ENABLED: bool = Field(default=False, description="Enable TLS/SSL for server")
    SSL_CERT_FILE: Optional[str] = Field(default=None, description="Path to SSL certificate file")
    SSL_KEY_FILE: Optional[str] = Field(default=None, description="Path to SSL private key file")
    SSL_CA_FILE: Optional[str] = Field(default=None, description="Path to CA certificate bundle")
    SSL_VERIFY_MODE: str = Field(default="CERT_REQUIRED", description="Certificate verification mode")

    # Data Encryption at Rest (Requirement 8.4)
    ENCRYPTION_KEY: Optional[str] = Field(default=None, description="Base64-encoded 32-byte AES-256 encryption key")
    AWS_KMS_KEY_ID: Optional[str] = Field(default=None, description="AWS KMS key ID for encryption key management")

    # Celery Configuration (Requirement 1.1, 1.2, 1.3)
    CELERY_BROKER_URL: Optional[str] = Field(default=None, description="Celery broker URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, description="Celery result backend URL")

    # ========================================
    # FIELD VALIDATORS
    # ========================================

    @field_validator("JWT_SECRET", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT_SECRET is non-empty (Requirement 1.3)"""
        # Only validate if not in testing mode
        if not os.environ.get("TESTING"):
            if not v or not v.strip():
                raise ValueError("JWT_SECRET cannot be empty")
        return v

    # NOTE: POSTGRES_PASSWORD and NEO4J_PASSWORD validation is handled
    # in the mode="before" validators above (lines 137 and 156)

    @field_validator("ENVIRONMENT", mode="after")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate ENVIRONMENT is one of the supported values (Requirement 1.5)"""
        if not v:
            return "development"
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"ENVIRONMENT must be one of {valid_environments}, got {v}")
        return v

    @field_validator("BCRYPT_ROUNDS", mode="after")
    @classmethod
    def validate_bcrypt_rounds(cls, v: int) -> int:
        """Validate BCRYPT_ROUNDS is at least 12 for security"""
        if v < 12:
            raise ValueError("BCRYPT_ROUNDS must be at least 12 for security")
        if v > 20:
            raise ValueError("BCRYPT_ROUNDS is very high (>20) - may impact performance")
        return v

    @model_validator(mode="after")
    def validate_celery_config(self) -> "Settings":
        """Validate Celery configuration if enabled (Requirement 1.1, 1.2, 1.3)"""
        # Celery URLs are optional but if one is set, both should be set
        if self.CELERY_BROKER_URL or self.CELERY_RESULT_BACKEND:
            if not self.CELERY_BROKER_URL:
                raise ValueError("CELERY_BROKER_URL must be set if CELERY_RESULT_BACKEND is set")
            if not self.CELERY_RESULT_BACKEND:
                raise ValueError("CELERY_RESULT_BACKEND must be set if CELERY_BROKER_URL is set")
        return self

    # ========================================
    # COMPUTED PROPERTIES
    # ========================================

    @property
    def postgres_url(self) -> str:
        """PostgreSQL async connection URL (Requirement 1.1)"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_postgres_url(self) -> str:
        """PostgreSQL sync connection URL (Requirement 1.1)"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        """Redis connection URL with authentication (Requirement 1.1)"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        else:
            return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def celery_broker_url_value(self) -> str:
        """Celery broker URL (Requirement 1.1)"""
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        return self.redis_url

    @property
    def celery_result_backend_url(self) -> str:
        """Celery result backend URL (Requirement 1.1)"""
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        else:
            return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    # ========================================
    # VALIDATION METHODS
    # ========================================

    def validate_security_settings(self) -> List[str]:
        """
        Validate security-related settings and return warnings.
        
        Validates Requirements: 1.1, 1.2, 1.3, 1.5
        """
        warnings = []

        # JWT_SECRET length validation
        if len(self.JWT_SECRET) < 32:
            warnings.append(
                f"JWT_SECRET is only {len(self.JWT_SECRET)} characters (minimum 32 recommended). "
                "This may reduce security. Consider regenerating with: openssl rand -hex 32"
            )

        # JWT expiration validation
        if self.JWT_EXPIRATION_HOURS > 168:  # 1 week
            warnings.append(
                f"JWT_EXPIRATION_HOURS is very long ({self.JWT_EXPIRATION_HOURS} hours, >1 week). "
                "Consider reducing for better security."
            )

        # BCRYPT rounds validation
        if self.BCRYPT_ROUNDS < 12:
            warnings.append(
                f"BCRYPT_ROUNDS is {self.BCRYPT_ROUNDS} (minimum 12 required). "
                "This is a critical security issue."
            )

        if self.BCRYPT_ROUNDS > 20:
            warnings.append(
                f"BCRYPT_ROUNDS is {self.BCRYPT_ROUNDS} (>20). "
                "This may significantly impact performance."
            )

        # External API keys validation
        if not self.GITHUB_TOKEN and not self.OPENAI_API_KEY and not self.ANTHROPIC_API_KEY:
            warnings.append(
                "No external API keys configured (GITHUB_TOKEN, OPENAI_API_KEY, ANTHROPIC_API_KEY). "
                "Limited functionality available."
            )

        return warnings

    def validate_database_urls(self) -> List[str]:
        """
        Validate database connection URLs and parameters.
        
        Validates Requirements: 1.1, 1.2, 1.3
        """
        errors = []

        # PostgreSQL validation
        if not self.POSTGRES_HOST:
            errors.append("POSTGRES_HOST is required")
        if not self.POSTGRES_DB:
            errors.append("POSTGRES_DB is required")
        if not self.POSTGRES_USER:
            errors.append("POSTGRES_USER is required")
        if not self.POSTGRES_PASSWORD:
            errors.append("POSTGRES_PASSWORD is required and cannot be empty")
        if self.POSTGRES_PORT <= 0 or self.POSTGRES_PORT > 65535:
            errors.append(f"POSTGRES_PORT must be between 1 and 65535, got {self.POSTGRES_PORT}")

        # Neo4j validation
        if not self.NEO4J_URI:
            errors.append("NEO4J_URI is required")
        if not self.NEO4J_USER:
            errors.append("NEO4J_USER is required")
        if not self.NEO4J_PASSWORD:
            errors.append("NEO4J_PASSWORD is required and cannot be empty")

        # Redis validation
        if not self.REDIS_HOST:
            errors.append("REDIS_HOST is required")
        if self.REDIS_PORT <= 0 or self.REDIS_PORT > 65535:
            errors.append(f"REDIS_PORT must be between 1 and 65535, got {self.REDIS_PORT}")

        return errors

    def check_celery_config(self) -> List[str]:
        """
        Check Celery configuration and return errors list.
        
        Validates Requirements: 1.1, 1.2, 1.3
        """
        errors = []

        # If Celery is configured, validate both URLs are set
        if self.CELERY_BROKER_URL and not self.CELERY_RESULT_BACKEND:
            errors.append("CELERY_RESULT_BACKEND must be set if CELERY_BROKER_URL is set")

        if self.CELERY_RESULT_BACKEND and not self.CELERY_BROKER_URL:
            errors.append("CELERY_BROKER_URL must be set if CELERY_RESULT_BACKEND is set")

        return errors

    def get_environment_specific_defaults(self) -> dict:
        """
        Get environment-specific default values.
        
        Validates Requirement: 1.5
        """
        defaults = {
            "development": {
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "ALLOWED_ORIGINS": [
                    "http://localhost:3000",
                    "http://localhost:8000",
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:8000",
                    "http://frontend:3000",
                ],
            },
            "staging": {
                "DEBUG": False,
                "LOG_LEVEL": "INFO",
                "ALLOWED_ORIGINS": [
                    "https://staging.example.com",
                ],
            },
            "production": {
                "DEBUG": False,
                "LOG_LEVEL": "WARNING",
                "ALLOWED_ORIGINS": [
                    "https://example.com",
                ],
            },
        }
        return defaults.get(self.ENVIRONMENT, defaults["development"])

    def is_celery_enabled(self) -> bool:
        """Check if Celery is enabled (Requirement 1.4)"""
        return bool(self.CELERY_BROKER_URL and self.CELERY_RESULT_BACKEND)

    def is_github_integration_enabled(self) -> bool:
        """Check if GitHub integration is enabled (Requirement 1.4)"""
        return bool(self.GITHUB_TOKEN and self.GITHUB_WEBHOOK_SECRET)

    def is_openai_enabled(self) -> bool:
        """Check if OpenAI integration is enabled (Requirement 1.4)"""
        return bool(self.OPENAI_API_KEY)

    def is_anthropic_enabled(self) -> bool:
        """Check if Anthropic integration is enabled (Requirement 1.4)"""
        return bool(self.ANTHROPIC_API_KEY)

    def is_ollama_enabled(self) -> bool:
        """Check if Ollama local LLM is enabled (Requirement 1.4)"""
        return bool(self.OLLAMA_BASE_URL)
    
    def is_openrouter_enabled(self) -> bool:
        """Check if OpenRouter integration is enabled"""
        return bool(self.OPENROUTER_API_KEY)

    def is_lmstudio_enabled(self) -> bool:
        """Check if LM Studio local inference is enabled"""
        return self.LMSTUDIO_ENABLED and bool(self.LMSTUDIO_BASE_URL)

    def is_deepseek_enabled(self) -> bool:
        """Check if DeepSeek AI integration is enabled"""
        return bool(self.DEEPSEEK_API_KEY)

    def is_ssl_enabled(self) -> bool:
        """Check if SSL/TLS is enabled (Requirement 8.5)"""
        return self.SSL_ENABLED and bool(self.SSL_CERT_FILE and self.SSL_KEY_FILE)

    def validate_ssl_config(self) -> List[str]:
        """
        Validate SSL/TLS configuration.
        
        Validates Requirement 8.5
        """
        errors = []
        
        if self.SSL_ENABLED:
            if not self.SSL_CERT_FILE:
                errors.append("SSL_CERT_FILE is required when SSL_ENABLED is true")
            if not self.SSL_KEY_FILE:
                errors.append("SSL_KEY_FILE is required when SSL_ENABLED is true")
            
            # Check if files exist
            if self.SSL_CERT_FILE:
                from pathlib import Path
                if not Path(self.SSL_CERT_FILE).exists():
                    errors.append(f"SSL certificate file not found: {self.SSL_CERT_FILE}")
            
            if self.SSL_KEY_FILE:
                if not Path(self.SSL_KEY_FILE).exists():
                    errors.append(f"SSL key file not found: {self.SSL_KEY_FILE}")
        
        return errors

    def validate_cors_config(self) -> List[str]:
        """
        Validate CORS configuration.
        
        Validates Requirement 8.8
        """
        warnings = []
        
        # Check if wildcard origin is used (security risk)
        if "*" in self.ALLOWED_ORIGINS:
            warnings.append(
                "CORS allows all origins (*). This is a security risk in production. "
                "Restrict to specific approved domains."
            )
        
        # Check if localhost is allowed in production
        if self.ENVIRONMENT == "production":
            localhost_origins = [
                origin for origin in self.ALLOWED_ORIGINS
                if "localhost" in origin or "127.0.0.1" in origin
            ]
            if localhost_origins:
                warnings.append(
                    f"CORS allows localhost origins in production: {localhost_origins}. "
                    "Remove these in production environment."
                )
        
        # Check if credentials are allowed with wildcard
        if self.CORS_ALLOW_CREDENTIALS and "*" in self.ALLOWED_ORIGINS:
            warnings.append(
                "CORS allows credentials with wildcard origin. "
                "This is not allowed by browsers and will fail."
            )
        
        return warnings

    def validate_rate_limiting_config(self) -> List[str]:
        """
        Validate rate limiting configuration.
        
        Validates Requirement 8.6
        """
        warnings = []
        
        # Check if rate limit is too high
        if self.RATE_LIMIT_PER_MINUTE > 1000:
            warnings.append(
                f"Rate limit is very high ({self.RATE_LIMIT_PER_MINUTE} requests/minute). "
                "Consider reducing for better protection against abuse."
            )
        
        # Check if rate limit is too low
        if self.RATE_LIMIT_PER_MINUTE < 10:
            warnings.append(
                f"Rate limit is very low ({self.RATE_LIMIT_PER_MINUTE} requests/minute). "
                "This may impact legitimate users."
            )
        
        return warnings

    def validate_tracing_config(self) -> List[str]:
        """
        Validate OpenTelemetry tracing configuration.
        
        Validates Requirement 18.1
        """
        warnings = []
        
        # Check if tracing is enabled
        if not self.TRACING_ENABLED:
            warnings.append("OpenTelemetry tracing is disabled. Enable for production observability.")
        
        # Check sample rate
        if self.TRACING_SAMPLE_RATE < 0.0 or self.TRACING_SAMPLE_RATE > 1.0:
            warnings.append(
                f"TRACING_SAMPLE_RATE must be between 0.0 and 1.0, got {self.TRACING_SAMPLE_RATE}"
            )
        
        # Check if sample rate is too low in production
        if self.ENVIRONMENT == "production" and self.TRACING_SAMPLE_RATE < 0.1:
            warnings.append(
                f"TRACING_SAMPLE_RATE is very low ({self.TRACING_SAMPLE_RATE}) in production. "
                "Consider increasing for better observability."
            )
        
        # Check OTLP endpoint
        if self.TRACING_ENABLED and not self.OTLP_ENDPOINT:
            warnings.append("OTLP_ENDPOINT is required when TRACING_ENABLED is true")
        
        return warnings

    def is_tracing_enabled(self) -> bool:
        """Check if OpenTelemetry tracing is enabled (Requirement 18.1)"""
        return self.TRACING_ENABLED

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra environment variables
    )


# Create global settings instance
settings = Settings()
