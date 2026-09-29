CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_chunks (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    chunk_index INT NOT NULL,
    text TEXT NOT NULL,
    pages INT[] NOT NULL DEFAULT '{}',
    language TEXT NOT NULL,
    model_name TEXT NOT NULL,
    embedding VECTOR({embedding_dim}) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, chunk_index, model_name)
);

-- Full-text (keyword) search. A generated column, kept in sync automatically
-- by Postgres whenever `text` changes -- ingestion never computes this
-- itself. Hardcoded to English since every current source document is
-- English; revisit as per-row (via the `language` column) once French
-- source documents actually exist.
ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS text_search tsvector
    GENERATED ALWAYS AS (to_tsvector('english', text)) STORED;

CREATE INDEX IF NOT EXISTS document_chunks_text_search_idx
    ON document_chunks USING GIN (text_search);
