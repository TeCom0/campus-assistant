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

-- Structured course data (code, title, credits, prerequisites), for the
-- query_courses agent tool. Deliberately doesn't store full course
-- descriptions -- that free text is already in document_chunks (Phase 1)
-- and searchable via search_documents; this table is for the structured
-- facts that need real SQL, especially prerequisite chain-following.
-- See app/ingestion/courses.py.
CREATE TABLE IF NOT EXISTS courses (
    code TEXT PRIMARY KEY,
    department TEXT NOT NULL,
    title TEXT NOT NULL,
    credits INT NOT NULL,
    prerequisites_text TEXT,
    corequisites_text TEXT,
    page INT,
    source TEXT NOT NULL
);

-- Normalized prerequisite edges extracted from courses.prerequisites_text,
-- for recursive chain-following. prerequisite_code is deliberately NOT a
-- foreign key: a small number of referenced codes don't resolve to an
-- extracted course row (format variations in the source catalog), and
-- we'd rather keep the real reference than silently drop it.
CREATE TABLE IF NOT EXISTS course_prerequisites (
    course_code TEXT NOT NULL REFERENCES courses(code),
    prerequisite_code TEXT NOT NULL,
    PRIMARY KEY (course_code, prerequisite_code)
);
