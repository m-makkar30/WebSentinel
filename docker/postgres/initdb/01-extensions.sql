-- Runs once, on first initialization of an empty Postgres data directory
-- (via /docker-entrypoint-initdb.d). Enables the pgvector extension used by
-- the semantic-diff layer. Django migrations also guard this with
-- `CREATE EXTENSION IF NOT EXISTS vector` so existing databases stay covered.
CREATE EXTENSION IF NOT EXISTS vector;
