"""
Shared Constants Module

This module centralizes all constants used across the application
to avoid duplication and ensure consistency.
"""

# =============================================================================
# API Constants
# =============================================================================

API_VERSION = "1.0.0"
API_TITLE = "Code Quality Check API"
API_DESCRIPTION = "AI-based quality check on project code and architecture"

# API Prefixes
API_V1_PREFIX = "/api/v1"

# =============================================================================
# Pagination Constants
# =============================================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1

# =============================================================================
# Cache Constants
# =============================================================================

CACHE_TTL_SHORT = 60  # 1 minute
CACHE_TTL_MEDIUM = 300  # 5 minutes
CACHE_TTL_LONG = 3600  # 1 hour
CACHE_TTL_DAY = 86400  # 24 hours

# =============================================================================
# Rate Limiting Constants
# =============================================================================

DEFAULT_RATE_LIMIT = 100
DEFAULT_RATE_LIMIT_PERIOD = 60  # seconds

# =============================================================================
# Analysis Constants
# =============================================================================

MAX_FILES_PER_ANALYSIS = 50
MAX_FILE_SIZE = 1024 * 1024  # 1MB
MAX_ANALYSIS_TIMEOUT = 300  # seconds

# =============================================================================
# Code Review Constants
# =============================================================================

MAX_COMMENTS_PER_REVIEW = 100
MAX_REVIEW_DEPTH = 10

# =============================================================================
# Security Constants
# =============================================================================

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
JWT_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30
MAX_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_MINUTES = 30

# =============================================================================
# Webhook Constants
# =============================================================================

WEBHOOK_TIMEOUT = 30  # seconds
WEBHOOK_RETRY_COUNT = 3
WEBHOOK_RETRY_DELAY = 5  # seconds

# =============================================================================
# Task Queue Constants
# =============================================================================

TASK_PRIORITY_HIGH = 1
TASK_PRIORITY_MEDIUM = 5
TASK_PRIORITY_LOW = 10

TASK_STATUS_PENDING = "pending"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

# =============================================================================
# Database Constants
# =============================================================================

DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 3600

# =============================================================================
# LLM Constants
# =============================================================================

LLM_DEFAULT_MODEL = "gpt-4"
LLM_DEFAULT_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 2000
LLM_TIMEOUT = 60  # seconds

# =============================================================================
# Graph Database Constants
# =============================================================================

NEO4J_DEFAULT_HOST = "localhost"
NEO4J_DEFAULT_PORT = 7687
NEO4J_DATABASE = "neo4j"

# =============================================================================
# HTTP Status Codes
# =============================================================================

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503

# =============================================================================
# Logging Constants
# =============================================================================

LOG_FORMAT_JSON = "json"
LOG_FORMAT_TEXT = "text"
LOG_DEFAULT_LEVEL = "INFO"

# =============================================================================
# Feature Flags
# =============================================================================

FEATURE_ANALYSIS_QUEUE = "analysis_queue"
FEATURE_AB_TESTING = "ab_testing"
FEATURE_ADVANCED_METRICS = "advanced_metrics"
