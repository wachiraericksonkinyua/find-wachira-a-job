CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS project_chunks (
    chunk_hash TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL
);

CREATE INDEX IF NOT EXISTS project_chunks_embedding_idx
    ON project_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    name TEXT NOT NULL,
    company TEXT,
    contact TEXT NOT NULL,
    role TEXT,
    preferred_time TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS pet_leads (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    type TEXT NOT NULL,
    note TEXT
);

CREATE INDEX IF NOT EXISTS bookings_created_at_idx
    ON bookings (created_at DESC);

CREATE INDEX IF NOT EXISTS pet_leads_created_at_idx
    ON pet_leads (created_at DESC);
