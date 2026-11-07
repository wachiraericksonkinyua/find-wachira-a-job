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

-- Talent Board, Roast Wall, admin-managed projects, reactions, and audit log.
CREATE TABLE IF NOT EXISTS board_submissions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    pitch TEXT NOT NULL,
    link TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    takedown_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS roast_wall (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    advice TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL,
    moderated_at TIMESTAMPTZ,
    moderation_note TEXT
);

CREATE TABLE IF NOT EXISTS portfolio_projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    problem TEXT NOT NULL,
    build TEXT NOT NULL,
    outcome TEXT NOT NULL,
    stack TEXT NOT NULL DEFAULT '[]',
    repo_url TEXT,
    demo_url TEXT,
    status TEXT NOT NULL DEFAULT 'published',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS project_reactions (
    id BIGSERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    reaction TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT,
    detail TEXT
);

CREATE INDEX IF NOT EXISTS board_submissions_status_idx
    ON board_submissions (status, created_at DESC);
CREATE INDEX IF NOT EXISTS roast_wall_status_idx
    ON roast_wall (status, created_at DESC);
CREATE INDEX IF NOT EXISTS project_reactions_project_idx
    ON project_reactions (project_id, reaction);
CREATE INDEX IF NOT EXISTS admin_audit_log_created_idx
    ON admin_audit_log (created_at DESC);
