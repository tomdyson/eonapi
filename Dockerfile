# Multi-stage build for eonapi deployment
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (including UI extras)
RUN uv sync --frozen --no-dev --extra ui

# Copy application code
COPY eonapi ./eonapi
COPY main.py ./

# Production stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install cron for scheduled tasks
RUN apt-get update && \
    apt-get install -y --no-install-recommends cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/eonapi /app/eonapi
COPY --from=builder /app/main.py /app/main.py
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose port for web UI
EXPOSE 8000

# Use entrypoint script to run both web UI and scheduled stats
ENTRYPOINT ["/app/docker-entrypoint.sh"]
