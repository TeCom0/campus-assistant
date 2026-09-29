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
