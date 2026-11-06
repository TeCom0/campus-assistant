-- One line per table: its row count and an md5 of its whole rows, ordered. A whole
-- row includes the embeddings, which hashing only the text would miss. Used by the
-- backup script as proof, and by the restore drill to compare with production.
SELECT 'course_prerequisites', count(*), md5(coalesce(string_agg(t::text, ',' ORDER BY course_code, prerequisite_code), ''))
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
