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
