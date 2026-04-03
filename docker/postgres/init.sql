-- CRECE v2.0 — PostgreSQL Init Script
-- Runs on first container initialization only

-- PostGIS: spatial data types and functions
CREATE EXTENSION IF NOT EXISTS postgis;

-- pg_trgm: trigram matching for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- pgcrypto: UUID generation and hashing functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- btree_gist: GiST index support for exclusion constraints
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Verify extensions loaded
DO $$
BEGIN
    RAISE NOTICE 'CRECE v2.0 — Extensions loaded:';
    RAISE NOTICE '  postgis:    %', (SELECT extversion FROM pg_extension WHERE extname = 'postgis');
    RAISE NOTICE '  pg_trgm:    %', (SELECT extversion FROM pg_extension WHERE extname = 'pg_trgm');
    RAISE NOTICE '  pgcrypto:   %', (SELECT extversion FROM pg_extension WHERE extname = 'pgcrypto');
    RAISE NOTICE '  btree_gist: %', (SELECT extversion FROM pg_extension WHERE extname = 'btree_gist');
END
$$;
