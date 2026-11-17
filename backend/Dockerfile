# ==============================================================================
# Michito B2B Lead Intelligence Engine — Production Multi-Stage Dockerfile
# Python 3.13 Slim • Non-Root Security • Container & Cloud Run Compatible
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build & Dependency Wheel Compiler
# ------------------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies for C-extensions (psycopg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Final Minimal Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.13-slim AS runner

WORKDIR /app

# Install runtime system libraries (libpq for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user
RUN groupadd -r michito && useradd -r -g michito -d /app -s /sbin/nologin michito

# Copy virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set environment paths and flags
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/backend \
    PORT=8000

# Copy application source code, modules, configurations, and data
COPY --chown=michito:michito backend/src/ /app/src/
COPY --chown=michito:michito backend/campaigns/ /app/campaigns/
COPY --chown=michito:michito backend/templates/ /app/templates/
COPY --chown=michito:michito backend/data/ /app/data/
COPY --chown=michito:michito backend/*.py /app/
COPY --chown=michito:michito clients/ /app/clients/
COPY --chown=michito:michito backend/requirements.txt /app/

# Create deliverables outputs directory with appropriate write permissions
RUN mkdir -p /app/outputs && chown -R michito:michito /app/outputs /app/data

USER michito

# Expose HTTP port for Web API
EXPOSE 8000 8080

# Healthcheck validating API responsiveness
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/docs || exit 1

# Default Command: Launches FastAPI Web API Service
# (Can be overridden to run the worker: python order_worker.py --daemon)
CMD exec uvicorn src.entrypoints.api.main:app --host 0.0.0.0 --port ${PORT}
