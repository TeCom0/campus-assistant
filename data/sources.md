# Data sources

The list of documents is `data/registry.toml`: what each one is, where it comes from, and its
checksum. It is the only list, so it can't disagree with a second one. A test keeps this file free of
URLs.

## Rules

- Only public Al Akhawayn University (AUI) documents, with no personal student data.
- `backend/app/registry.py` refuses a URL that isn't https on the university's own host, and refuses
  any document not marked public.

## Notes

- The Academic Catalog PDF covers both academic policies (add/drop, academic integrity, grading,
  graduation requirements, etc.) and the course catalog itself, so it seeds both in one document.
- Every source was checked on 2026-09-29, the date in each edition's `retrieved_at`: all answered with
  HTTP 200.
