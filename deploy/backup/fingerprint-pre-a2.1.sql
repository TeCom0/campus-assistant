-- The fingerprint as it was before A2.1, for a dump taken before the registry tables
-- existed. Only the restore drill uses it, and only with --pre-a2-1 (deploy/DEPLOY.md).
SELECT 'course_prerequisites', count(*), md5(coalesce(string_agg(t::text, ',' ORDER BY course_code, prerequisite_code), ''))
FROM course_prerequisites t
UNION ALL
SELECT 'courses', count(*), md5(coalesce(string_agg(t::text, ',' ORDER BY code), ''))
FROM courses t
UNION ALL
SELECT 'document_chunks', count(*), md5(coalesce(string_agg(t::text, ',' ORDER BY source, chunk_index, model_name), ''))
FROM document_chunks t
ORDER BY 1;
