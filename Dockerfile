# Multi-stage build for eonapi deployment
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (including UI extras)
RUN uv sync --frozen --no-dev --extra ui

# Copy application code
COPY eonapi ./eonapi
COPY main.py ./

# Production stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/eonapi /app/eonapi
COPY --from=builder /app/main.py /app/main.py
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose port for web UI
EXPOSE 8000

# Run the web UI
CMD ["uvicorn", "eonapi.server:app", "--host", "0.0.0.0", "--port", "8000"]
