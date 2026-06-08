# SEPEHR Backend — Dockerfile
# Multi-stage build for minimal production image

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencies stage ────────────────────────────────────────────────────────
FROM base AS deps

WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ── Production stage ──────────────────────────────────────────────────────────
FROM base AS production

WORKDIR /app

# Copy installed packages
COPY --from=deps /install /usr/local

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r sepehr && useradd -r -g sepehr -d /app -s /sbin/nologin sepehr \
    && chown -R sepehr:sepehr /app

USER sepehr

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Use Gunicorn with Uvicorn workers for production
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--keepalive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
