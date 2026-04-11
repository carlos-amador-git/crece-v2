# CRECE v2.0 — Backend Dockerfile (Multi-stage)
# Build:   docker build -t crece-backend ./backend
# Runtime: Non-root user, minimal attack surface

# ── Stage 1: Builder ──────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies for asyncpg, geoalchemy2, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libgeos-dev \
        libproj-dev \
        gdal-bin \
        libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --prefix=/install .[ml,nlp]

# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.12/site-packages:$PYTHONPATH"

WORKDIR /app

# Install only runtime libraries (no compilers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        libgeos-c1v5 \
        libproj25 \
        gdal-bin \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /install

# Create non-root user
RUN groupadd -r crece && useradd -r -g crece -d /app -s /sbin/nologin crece

# Copy application code
COPY --chown=crece:crece . .

USER crece

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
