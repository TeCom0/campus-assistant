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

-- Limits on what one mistake or abuse can hold. Half of max_connections, so the API
-- can't starve the owner's backups and migrations. Every query the API runs takes
-- milliseconds, so 5 s is far past normal. Each request opens new connections, so
-- this applies to the next one, with no API restart.
ALTER ROLE campus_api CONNECTION LIMIT 50;
ALTER ROLE campus_api SET statement_timeout = '5s';

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

-- From nothing every time, so the rights end up exactly as written here, even if
-- someone added one by hand or a later version of this file drops one. This whole
-- file runs as one statement batch, in one implicit transaction, so the API never
-- sees the moment between the revoke and the grants.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM campus_api;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM campus_api;

GRANT SELECT ON document_chunks, courses, course_prerequisites TO campus_api;
GRANT SELECT, INSERT, DELETE ON question_log TO campus_api;
GRANT USAGE ON SEQUENCE question_log_id_seq TO campus_api;
