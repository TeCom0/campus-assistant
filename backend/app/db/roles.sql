-- The API's own role. Run by the owner, after schema.sql, by app/db/migrate.py,
-- which also sets the password. Idempotent: an existing volume never runs initdb
-- scripts, so this has to work on a database that is already there, every time.
--
-- The rights are exactly what the request path's queries use:
--   courses, course_prerequisites  SELECT   agent/tools.py
--   document_chunks                SELECT   retrieval/vector_search.py, keyword_search.py
--   question_log                   SELECT, INSERT, DELETE   limits.py
--   question_log_id_seq            USAGE    limits.py's INSERT leaves id to its default
-- No default privileges: a new table stays unreadable until it is granted here,
-- so a mistake fails closed.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'campus_api') THEN
        CREATE ROLE campus_api LOGIN;
    END IF;
END
$$;

ALTER ROLE campus_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

-- By default PUBLIC can connect and create temporary tables, which campus_api
-- would inherit. The owner is a superuser, so this doesn't affect it.
DO $$
BEGIN
    EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO campus_api', current_database());
END
$$;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO campus_api;

GRANT SELECT ON document_chunks, courses, course_prerequisites TO campus_api;
GRANT SELECT, INSERT, DELETE ON question_log TO campus_api;
GRANT USAGE ON SEQUENCE question_log_id_seq TO campus_api;
