# CRECE v2.0 — PostgreSQL with PostGIS + pgvector
# Base: PostGIS 16-3.4 + pgvector compiled from source
FROM postgis/postgis:16-3.4

# Install build deps including LLVM 13 (required by PG16 JIT)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        postgresql-server-dev-16 \
        clang-13 \
        llvm-13 \
        llvm-13-dev \
        git \
        ca-certificates \
    && git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make USE_PGXS=1 \
    && make USE_PGXS=1 install \
    && rm -rf /tmp/pgvector \
    && apt-get purge -y build-essential postgresql-server-dev-16 git \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
