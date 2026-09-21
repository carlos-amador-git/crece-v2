# CRECE v2.0 — PostgreSQL with PostGIS + pgvector
# Base: PostGIS 16-3.4 (Debian bullseye) + pgvector desde el repo PGDG
FROM postgis/postgis:16-3.4

# pgvector viene empaquetado en apt.postgresql.org, que esta imagen ya tiene
# configurado (su propio PostGIS sale de ahí: 3.4.3+dfsg-2.pgdg110+1). Antes
# se compilaba desde fuente, lo que obligaba a instalar build-essential,
# clang-13, llvm-13, llvm-13-dev y git — y `postgresql-server-dev-16` arrastra
# además llvm-16 entero. Eran cientos de MB desempaquetados en cada build para
# producir una extensión que el repo ya publica, en contra de la regla 1 de
# CLAUDE.md (no reimplementar lo que una librería/paquete ya resuelve).
#
# Ese RUN es el que voló el deploy del 2026-09-21 (apt exit 100). El error
# resultó transitorio — `apt-get update` y un install --dry-run corren limpios
# en el mismo host — pero era con diferencia el paso más pesado y frágil del
# build, sobre un VPS que ronda los 500 MB de RAM libre. Instalar el paquete
# lo reduce a una descarga.
#
# Versión: 0.8.6-1.pgdg11+1 (verificado en el índice de bullseye-pgdg). Sube
# desde la 0.8.0 que se compilaba. Es un salto de patch dentro de 0.8.x: el
# formato del índice HNSW no cambia, así que `topic_trends.topic_embedding`
# (Vector(384) + HNSW, migración b2c3d4e5f6a7) sigue siendo válido.
# En una base ya inicializada, `pg_extension` conserva 0.8.0 hasta que se
# corra `ALTER EXTENSION vector UPDATE`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
