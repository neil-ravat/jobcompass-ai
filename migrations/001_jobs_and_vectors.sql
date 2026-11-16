CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE jobs (
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    application_url TEXT NOT NULL,
    salary_min NUMERIC CHECK (salary_min >= 0),
    salary_max NUMERIC CHECK (salary_max >= 0),
    currency TEXT,
    salary_period TEXT,
    location_restrictions JSONB,
    timezone_restrictions JSONB,
    source_updated_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    status_checked_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('open', 'closed', 'expired', 'unverified', 'missing_from_feed')),
    is_active BOOLEAN NOT NULL,
    content_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    PRIMARY KEY (source, source_id)
);

CREATE TABLE source_snapshots (
    source TEXT PRIMARY KEY,
    metadata JSONB NOT NULL
);

CREATE TABLE job_embeddings (
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    model TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source, source_id, model),
    FOREIGN KEY (source, source_id) REFERENCES jobs(source, source_id) ON DELETE CASCADE
);

CREATE INDEX jobs_active_expiry ON jobs (is_active, expires_at);
-- Exact cosine search is intentional for the small MVP corpus; no approximate index.
