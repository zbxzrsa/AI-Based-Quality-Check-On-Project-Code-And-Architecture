# Multi-stage Dockerfile for optimized production deployment
# Validates Requirements: 10.1, 10.2, 10.3, 10.4, 10.5

# Stage 1: Builder
# Use Python 3.11 slim-bookworm image for better compatibility
FROM python:3.14-slim-bookworm AS builder

# Set working directory
WORKDIR /build

# Install build dependencies with security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Stage 2: Runtime
# Use Python 3.11 slim-bookworm for compatibility with pydantic-core
FROM python:3.14-slim-bookworm

# Set working directory
WORKDIR /app

# Security: Upgrade all packages to latest versions
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy application code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# Create non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/logs && chown appuser:appuser /app/logs && \
    touch app.log && chown appuser:appuser app.log

# Create tmp directory for writable operations (when using readOnlyRootFilesystem in K8s)
RUN mkdir -p /tmp/app && chown appuser:appuser /tmp/app

USER root

# Health check using curl with better error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Expose port
EXPOSE 8000

# Run application with proper settings for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
