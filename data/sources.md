# Data Sources

Public Al Akhawayn University (AUI) documents used for ingestion. Only public pages/PDFs —
no personal student data. Each row should be verified live (HTTP 200) before use.

| Category                     | Title                              | URL                                                                                          | Language | Format |
|-------------------------------|-------------------------------------|-----------------------------------------------------------------------------------------------|----------|--------|
| Academic policies / catalog   | AUI Academic Catalog 2024-2025      | https://aui.ma/hubfs/ACADEMIC%20CATALOG%202024-2025.pdf?hsLang=en                             | English  | PDF    |
| Fellowships / scholarships    | Prestigious Scholarships            | https://aui.ma/prestigious-scholarship                                                        | English  | HTML   |
| Fellowships / scholarships    | Graduate Scholarships               | https://aui.ma/admission-aid/graduates/scholarships                                           | English  | HTML   |

## Notes
- Checked 2026-09-29: all three URLs above returned HTTP 200.
- The Academic Catalog PDF covers both academic policies (add/drop, academic integrity, grading,
  graduation requirements, etc.) and the course catalog itself, so it seeds both categories from
  CLAUDE.md's scope in one document.
- More sources (e.g. French-language pages, additional fellowship listings) will be added
  incrementally as later Phase 1 steps process these first few successfully.
