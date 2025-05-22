# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

# Set build arguments and environment variables
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Install system build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/poetry \
    poetry config installer.max-workers 10 && \
    poetry install --no-interaction --no-root --only main && \
    poetry export -f requirements.txt --output requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHON_ENV=production \
    PATH="/usr/local/bin:$PATH"

# Install runtime system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    wget \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create and switch to non-root user
RUN useradd -m -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /app/requirements.txt .
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser ./app ./app
COPY --chown=appuser:appuser ./main.py ./main.py
COPY --chown=appuser:appuser ./entrypoint.sh ./entrypoint.sh
COPY --chown=appuser:appuser ./alembic.ini ./alembic.ini
COPY --chown=appuser:appuser ./migrations ./migrations
# Switch to non-root user
USER appuser

RUN chmod +x ./entrypoint.sh

# Command to run the application
ENTRYPOINT ["./entrypoint.sh"]
