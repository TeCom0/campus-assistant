-- A2.3's content check (rule item 4 in CLAUDE.md): the same output before and after the
-- in-place migration, on the old schema and the new. fingerprint.sql hashes whole rows, and
-- the migration adds `source` to course_prerequisites, so that table is hashed here on its
-- old columns (the new one is checked on its own after the migration: the old schema has no
-- column to name). The other tables gain no column, so their whole rows are hashed, as in
-- fingerprint.sql.
SELECT 'course_prerequisites (course_code, prerequisite_code)', count(*),
       md5(coalesce(string_agg(t.course_code || '|' || t.prerequisite_code, ',' ORDER BY t.course_code, t.prerequisite_code), ''))
FROM course_prerequisites t
UNION ALL
SELECT 'courses', count(*), md5(coalesce(string_agg(t::text, ',' ORDER BY code), ''))
FROM courses t
UNION ALL
SELECT 'document_chunks', count(*), md5(coalesce(string_agg(t::text, ',' ORDER BY source, chunk_index, model_name), ''))
FROM document_chunks t
UNION ALL
SELECT 'document_editions', count(*), md5(coalesce(string_agg(t::text, ',' ORDER BY id), ''))
FROM document_editions t
UNION ALL
SELECT 'documents', count(*), md5(coalesce(string_agg(t::text, ',' ORDER BY id), ''))
FROM documents t
ORDER BY 1;
