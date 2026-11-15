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

-- Where the chunk sits in its document (app/ingestion/chunk.py): the level
-- the rules apply to, and the nearest heading above its first line. Both are
-- also written into `text` as a "Section: ..." line, so search and the model
-- see them; the columns allow filtering by level in SQL. Added like
-- text_search, so re-running this file on an existing table is safe.
ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS level TEXT NOT NULL DEFAULT 'general'
    CHECK (level IN ('general', 'undergraduate', 'graduate'));
ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS section TEXT;
-- Every heading the chunk spans (section first): metadata for source cards
-- only, not part of `text`, so it can change without re-embedding.
ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS sections TEXT[] NOT NULL DEFAULT '{}';

-- One row per question the public demo accepted (app/limits.py): the global
-- daily cap and the per-IP rate limit are counted from it. The IP is stored
-- only as a keyed hash, and rows older than 2 days are deleted on insert.
CREATE TABLE IF NOT EXISTS question_log (
    id BIGSERIAL PRIMARY KEY,
    asked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS question_log_asked_at_idx ON question_log (asked_at);


-- The registry (app/registry.py). Descriptive fields are copied from
-- data/registry.toml by `python -m app.registry sync`; `status` and the activation
-- fields live only here, so a rollback needs no redeploy. A document is a lasting
-- thing ("Academic Catalog"), an edition one version of it.
-- owning_department is NULL until AUI confirms it: a placeholder string could end up
-- in a code-written "confirm with [office]" line.
-- Before the content tables below: their `source` columns point at an edition.
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    owning_department TEXT,
    audience TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK (visibility IN ('public', 'non_public')),
    time_sensitive BOOLEAN NOT NULL,
    title JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS document_editions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    label TEXT NOT NULL,
    card_title TEXT NOT NULL,
    effective_from DATE,
    review_by DATE,
    retrieved_at DATE NOT NULL,
    last_updated DATE,
    language TEXT NOT NULL,
    format TEXT NOT NULL CHECK (format IN ('pdf', 'html')),
    source_url TEXT NOT NULL,
    fallback_url TEXT,
    course_tables BOOLEAN NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'superseded', 'withdrawn')),
    sha256 TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    quality_report JSONB NOT NULL,
    activated_by TEXT,
    activated_at TIMESTAMPTZ
);

-- At most one active edition per document, guaranteed by the database. A partial
-- index: only active rows take part, so a document can keep any number of others.
CREATE UNIQUE INDEX IF NOT EXISTS one_active_edition
    ON document_editions (document_id) WHERE status = 'active';

-- Structured course data (code, title, credits, prerequisites), for the
-- query_courses agent tool. Deliberately doesn't store full course
-- descriptions -- that free text is already in document_chunks (Phase 1)
-- and searchable via search_documents; this table is for the structured
-- facts that need real SQL, especially prerequisite chain-following.
-- See app/ingestion/courses.py.
-- Per edition (A2.3): `source` is the edition the course was extracted from, so
-- two catalog editions can each hold their own ACC 2302. A database made before
-- A2.3 is converted in place further down; the columns stay in the same order
-- either way, so a fresh database and a converted one hash the same.
CREATE TABLE IF NOT EXISTS courses (
    code TEXT NOT NULL,
    department TEXT NOT NULL,
    title TEXT NOT NULL,
    credits INT NOT NULL,
    prerequisites_text TEXT,
    corequisites_text TEXT,
    page INT,
    source TEXT NOT NULL,
    CONSTRAINT courses_pkey PRIMARY KEY (source, code)
);

-- Normalized prerequisite edges extracted from courses.prerequisites_text,
-- for recursive chain-following. prerequisite_code is deliberately NOT a
-- foreign key: a small number of referenced codes don't resolve to an
-- extracted course row (format variations in the source catalog), and
-- we'd rather keep the real reference than silently drop it.
-- `source` is the edition of the course that has the prerequisite, and the
-- foreign key keeps the edge inside that edition: an edge can't point from one
-- catalog's course into another's.
CREATE TABLE IF NOT EXISTS course_prerequisites (
    course_code TEXT NOT NULL,
    prerequisite_code TEXT NOT NULL,
    source TEXT NOT NULL,
    CONSTRAINT course_prerequisites_pkey PRIMARY KEY (source, course_code, prerequisite_code),
    CONSTRAINT course_prerequisites_course_fkey
        FOREIGN KEY (source, course_code) REFERENCES courses (source, code)
);

-- A2.3, in place, on a database made before it: courses keyed on code alone, and
-- edges with no source. Guarded by the missing column, so it runs once; init_schema
-- sends this whole file as one batch, which Postgres runs as one transaction, so a
-- failure anywhere leaves the old tables as they were. The backfill takes each
-- edge's source from its course, which the old foreign key guarantees exists, and
-- SET NOT NULL fails loudly if one didn't.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'course_prerequisites'
          AND column_name = 'source'
    ) THEN
        ALTER TABLE course_prerequisites DROP CONSTRAINT course_prerequisites_course_code_fkey;
        ALTER TABLE course_prerequisites DROP CONSTRAINT course_prerequisites_pkey;
        ALTER TABLE course_prerequisites ADD COLUMN source TEXT;
        UPDATE course_prerequisites cp SET source = c.source
            FROM courses c WHERE c.code = cp.course_code;
        ALTER TABLE course_prerequisites ALTER COLUMN source SET NOT NULL;
        ALTER TABLE courses DROP CONSTRAINT courses_pkey;
        ALTER TABLE courses ADD CONSTRAINT courses_pkey PRIMARY KEY (source, code);
        ALTER TABLE course_prerequisites ADD CONSTRAINT course_prerequisites_pkey
            PRIMARY KEY (source, course_code, prerequisite_code);
        ALTER TABLE course_prerequisites ADD CONSTRAINT course_prerequisites_course_fkey
            FOREIGN KEY (source, course_code) REFERENCES courses (source, code);
    END IF;
END
$$;

-- Every content row belongs to an edition the registry knows (A2.3). Added here
-- rather than in the CREATE TABLEs, so a fresh database and one made before A2.3
-- end with the same constraint, by name. Adding it checks every existing row, so a
-- source the registry doesn't have stops the migration. No ON DELETE: an edition
-- with rows can't be deleted, only marked superseded or withdrawn.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_constraint
        WHERE conname = 'document_chunks_source_fkey'
          AND conrelid = 'document_chunks'::regclass
    ) THEN
        ALTER TABLE document_chunks ADD CONSTRAINT document_chunks_source_fkey
            FOREIGN KEY (source) REFERENCES document_editions (id);
    END IF;
    IF NOT EXISTS (
        SELECT FROM pg_constraint
        WHERE conname = 'courses_source_fkey' AND conrelid = 'courses'::regclass
    ) THEN
        ALTER TABLE courses ADD CONSTRAINT courses_source_fkey
            FOREIGN KEY (source) REFERENCES document_editions (id);
    END IF;
END
$$;
