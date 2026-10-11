# Campus AI Assistant (working name)

## What this project is
A multilingual (English/French) AI assistant for Al Akhawayn University students. It answers questions
about academic policies, the course catalog, and scholarships, always citing its sources, and uses an
agent to query structured data (e.g. "what are the prerequisites for ACC 2302?"). The goal is to deploy
it to real students through TeCom (the student tech club) and measure real usage.

It is also a portfolio project for AI Software Engineer internship applications, so it must
demonstrate: RAG, AI agents, hybrid search, REST APIs, a TypeScript frontend, tests, Docker, CI/CD,
and evaluation.

## Working style (IMPORTANT, follow strictly)
- This is a learning project. Youness must be able to understand and defend every line in an interview.
- Work in small steps. One step per turn. Never scaffold large parts of the project at once.
- Before writing code: explain what the step does, why, and which concepts are involved.
- After writing code: explain the key lines, then tell Youness exactly what to run to verify it.
- Wait for Youness to confirm the step works before moving to the next one.
- When introducing a new concept (embeddings, BM25, LangGraph state, etc.), explain it in depth first.
- Prefer clear, explicit code over clever abstractions.
- Commit after every working step with a clear conventional commit message (feat:, fix:, test:, docs:, chore:).

## Environment
- Windows, PowerShell. Python 3.12, Node 24, Git 2.49, Docker 28 (WSL2 backend), 16 GB RAM.
- GPU: AMD Radeon RX 7600S (8 GB dedicated) + integrated Radeon graphics. No NVIDIA/CUDA.
  Keep all ML workloads (embeddings, etc.) on CPU for now. If GPU acceleration would
  genuinely help later (e.g. embedding becomes a bottleneck), explain why and what setup
  it would require (e.g. ROCm) before doing anything — don't switch to GPU unprompted.
- Project lives OUTSIDE OneDrive (long-path issues).
- Give PowerShell commands, not bash, unless running inside a Docker container.
- If the Docker daemon isn't reachable, run `docker desktop start`, wait for `docker desktop status` to report running, then continue. Don't ask Youness to start it manually.
- Postgres (Docker) is mapped to host port **15432**, not 5432/5433/55432. History:
  5432 and 5433 both collided with native Postgres installs on this machine (misleading
  "password authentication failed" errors that were actually a wrong-server problem). Moved
  to 55432 to dodge that -- which then, after a reboot days later, landed inside a Windows/
  Hyper-V *dynamic port exclusion range* (`netsh interface ipv4 show excludedportrange
  protocol=tcp`), which silently blocks binding with no clear error until you look. Windows
  reserves chunks of the ephemeral range (49152-65535) for WSL2 NAT, and which chunks are
  excluded can shift on any reboot -- so any port up there is at risk, not just 55432
  specifically. 15432 sits below that whole range, structurally avoiding this class of
  problem rather than dodging today's specific exclusions.
  If a DB connection ever fails again: (1) check
  `Get-NetTCPConnection -LocalPort <port> -State Listen` -- if it's someone else's process,
  that's the native-Postgres-collision case; if there's no listener at all despite
  `docker compose ps` showing the mapping as up, check excluded port ranges next, and try
  `docker compose down && docker compose up -d db` (not just `restart` -- that can leave a
  stale binding) or `docker desktop restart` if that doesn't clear it. Don't assume
  credentials are wrong before ruling out the network layer.

## Stack
- Backend: Python 3.12, FastAPI
- Orchestration: LangChain + LangGraph
- LLM: Groq free tier (primary), Google Gemini Flash free tier (fallback).
  Provider must be switchable through one config value. Free tiers have tight daily token limits:
  cache where sensible, keep prompts lean, never loop on LLM calls without a cap.
- Embeddings: open-source multilingual model via sentence-transformers, running locally (CPU)
- Database: PostgreSQL + pgvector (vectors), Postgres full-text search or BM25 (keywords), normal
  tables for structured data (e.g. courses with codes/credits/prerequisites)
- Frontend: React + TypeScript (Vite), streaming chat UI with citations
- Quality: pytest (unit + integration), an evaluation set of questions with expected answers,
  ruff for linting
- Infra: Docker Compose (db + api + frontend), GitHub Actions CI (lint + tests)

## Architecture (target)
1. Ingestion: load public university documents (PDF/HTML) -> clean -> chunk -> embed -> store in pgvector
   with metadata (source, page, language, section).
2. Retrieval: hybrid search = vector similarity + keyword/BM25, merged (e.g. reciprocal rank fusion).
3. Generation: answer ONLY from retrieved chunks, cite sources, say "I don't know" when context is missing.
4. Agent (LangGraph): tools = search_documents, query_courses (SQL), and more later.
5. API: FastAPI endpoints (chat with streaming, health, ingestion trigger).
6. Frontend: React + TS chat interface showing sources.

## Data rules
- Only public university documents. No personal student data.
- Store raw source files in data/raw/ (gitignored if large), keep a data/sources.md listing each URL.
- Secrets in .env (gitignored). Provide .env.example.

## Phases
- [done ] Phase 0: repo setup, Python venv, dependencies, Docker Compose with Postgres + pgvector
- [done ] Phase 1: ingestion pipeline (load, chunk, embed, store)
- [done ] Phase 2: retrieval (vector, keyword, hybrid) + evaluation set to measure retrieval quality
- [done ] Phase 3: RAG answers with citations via FastAPI
- [done ] Phase 4: LangGraph agent with tools (docs search + SQL)
- [done ] Phase 5: React + TypeScript chat UI with streaming
- [done ] Phase 6: tests, Docker Compose for full stack, GitHub Actions CI
- [wip  ] Phase 7: README, architecture diagram, demo video, deployment for student pilot
  (README + diagram done)

## Current status

**Phases 0-6 done; Phase 7 in progress (README + diagrams done).** Session 2026-10-09: Phase 5
code walkthrough (2 bugs found and fixed), Phase 6 built and signed off (CI with 3 jobs, Docker
images, full stack in Compose, Markdown answers), README and architecture diagrams written.
Session 2026-10-11: Youness decided no students use it before a faithfulness baseline exists;
the faithfulness check is in progress (see next steps, item 1). Youness asked
to collect interview-style questions during walkthroughs and do one knowledge-check session at
the very end, rather than quizzing step by step.
Phases 0-3: repo/Docker setup, the full ingestion pipeline,
all three retrieval methods with a measured evaluation baseline, grounded/cited RAG generation.
Phase 4: the LangGraph agent, wired into `/chat`. Phase 5: the React + TS chat UI and multi-turn
history. Verifying Phase 5 in the browser (2026-10-06) found six bugs; all six are fixed (three
on 2026-10-06, three on 2026-10-08) and verified in the UI. The Phase 5 code walkthrough
(2026-10-09) found two more, both fixed (see the end of the bugs list). The repo is on GitHub
(private): see "GitHub" under open issues.

**Phase 4 summary:**
- Agent: `search_documents` (wraps `search_hybrid()`) + `query_courses` (structured lookup over
  real catalog course data -- 660 courses, 526 prerequisite edges extracted from
  data/processed/academic_catalog_2024_2025.txt, no fabricated rows; `follow_prerequisites=True`
  walks the full chain via a recursive CTE). Explicit `StateGraph` (not the `create_react_agent`
  shortcut) so the tool-calling loop stays visible -- see app/agent/. A `query_fellowships` tool
  was built then fully cancelled and cleaned up (AUI has no fellowship program); `query_courses`
  replaced it.
- `/chat` rewired to the agent, replacing Phase 3's direct-RAG path -- one streaming endpoint, not
  two parallel ones (app/generation.py is kept as an unused standalone comparison script, not
  deleted). SSE event format agreed and implemented:
  - `token` -- `{"text": "..."}` -- answer text, piece by piece
  - `tool_call` -- `{"tool": "...", "args": {...}, "label": "..."}` -- fires before the tool
    executes; `label` is server-built and localized to the question's detected language
  - `citations` -- `{"citations": [{"marker": N, "source": "...", "pages": [...]}]}` -- once,
    after the answer is complete; only the markers the answer cites, once each, sorted (so they
    can skip numbers). `N` is unique per passage across every tool call in the answer, not
    restarted per call, and a passage returned again keeps its first `N`
  - `done` -- `{}` -- stream finished normally
  - `error` -- `{"message": "..."}` -- fires even if tokens already streamed, so the UI can mark
    the answer interrupted rather than see a silent cutoff; full exception detail logged
    server-side only, never sent to the client
- **Bug 1 (ContextVar isolation):** LangChain runs every tool call via
  `contextvars.copy_context().run(...)`, so a plain `ContextVar.set()` made inside a tool call
  silently never propagates back out -- citation numbering was resetting to [1] on every tool
  call. Fixed by holding a *mutable* counter object in the ContextVar and mutating its attribute
  in place (copying a context copies the reference, not the object). Regression test
  (`test_survives_copy_context_boundary_like_langchain_tool_execution`) specifically crosses this
  boundary, since the other citation tests all pass even with the broken version.
- **Bug 2 (full-width brackets):** Unicode full-width brackets (e.g. "【4】") still appeared in the
  raw per-token stream despite strengthened prompt wording -- confirmed stochastic prompt-
  following isn't reliable enough for something this structurally important (the frontend needs
  to parse "[N]" for citation links). Fixed with deterministic normalization in app/main.py on
  every token, not relying on the LLM alone.
- First tests in the project: `backend/tests/test_citations.py` (pytest added as a dev
  dependency).

**Phase 5 summary (commits f7e9e6e, 24b6a56, ad45265):**
- frontend/ (Vite + React + TS). `chatStream.ts` POSTs to `/chat` and reads the SSE events;
  `App.tsx` renders tokens progressively, shows `tool_call` labels, turns `[N]` into a link only
  when a citation with marker N was received, lists sources as footnotes, and marks the answer
  interrupted on an `error` event, a failed request, or a stream that ends without `done`.
- Multi-turn: `ChatRequest.messages` is optional (role/content, oldest first), so single-turn
  callers still work. app/agent/history.py keeps the last `MAX_HISTORY_MESSAGES` (10) and strips
  `[N]` markers from earlier assistant turns (markers are per request, so old ones would point at
  the wrong source). The UI leaves interrupted answers out of the history. Tests: test_history.py.
- CORS allows the Vite dev origin (`CORS_ORIGINS` in config.py); the frontend calls
  `VITE_API_URL`, default `http://127.0.0.1:8000`.
- Run it, one terminal each: `docker compose up -d db` (repo root); in backend\ with the venv
  active, `uvicorn app.main:app --reload --port 8000`; in frontend\, `npm run dev`, then open
  http://localhost:5173.

**Bugs found while verifying Phase 5 (2026-10-06), fixed 2026-10-06 and 2026-10-08:**
- *Crash on a French question* (432d0af): the model ignored the prompt's "at most two searches",
  made 5 search calls, and 5 x (agent + tools) = 10 steps hit `recursion_limit` ->
  `GraphRecursionError` -> the answer ended in an error. Now `MAX_TOOL_ROUNDS = 3` is enforced in
  `_agent_node`: once used, the model is called with no tools bound and the conversation rewritten
  without tool-call structure (tool results passed as plain text), so it has to answer.
  `MAX_AGENT_STEPS` (10) stays as a backstop; a normal run is at most 7 steps. Lesson:
  `tool_choice="none"` was tried first and failed -- Groq *rejects* a tool call the model still
  generates ("Tool choice is none, but model called a tool"), it doesn't prevent it.
  Tests: test_tool_budget.py (fake model, no LLM calls).
- *Wrong prerequisites* (3b8895f): ACC 2302's answer said MTH 1303 AND 1304 AND 1305 were all
  required; the catalog says ACC 2301 needs any ONE. The chain was a flat list of codes, so the
  model never saw ACC 2301's "or" (it ignored a caution note asking it to look it up). Option B:
  each chain course is now listed once (shortest depth) with its own prerequisites in the
  catalog's exact wording. Deliberately NOT an AND/OR parser: the wording is genuinely ambiguous
  (78/468 prerequisite lines contain "or", 10 mix "and"/"or"; a comma means AND on some lines and
  OR on others), and a parser would turn that into confident wrong answers. The system prompt
  asks the agent to quote ambiguous or school-dependent wording and suggest an advisor. Cycle
  guard: the recursive CTE carries the walked path and won't follow an edge back into it (the old
  query only had the depth cap); depth < 10 stays as a backstop. Deepest chain: SCM 5305, 6
  levels, 20 courses, ~2.1k chars (~530 tokens, estimated at 4 chars/token -- no tokenizer
  installed). Tests: test_query_courses.py, the first tests that need Postgres -- skipped when
  it isn't reachable; the cycle test builds a cycle in a transaction that is always rolled back.
- *Missed course codes* (6fc9298): `COURSE_CODE_RE` required a space, so "CSC3326"/"MGT3301"
  made no edge. A scan of all 429 prerequisite texts found 4 such codes and no hyphenated or
  lowercase ones; the space is now optional, lowercase/hyphens still rejected on purpose (a
  case-insensitive pattern would read "and 2024" as a course). Re-seeded: 522 -> 526 edges, no
  cycles. Tests: test_course_extraction.py.
- *"Not in the catalog" for a real course* (0bc183a, 2026-10-08): the agent once called MTH 1305
  "Calculus I" (copied from MTH 1303). MTH 1305 has no course-description entry, so no `courses`
  row; it appears only in lists (line 6013 of the processed catalog: "Mathematics for Business")
  -- not a regex miss. Reproduced first: 6 agent runs after 3b8895f invented no title (0/3 on a
  full-chain question), so 3b8895f's per-course lines had already fixed that. But "not found in
  the structured catalog data" was passed on to students as "not located in the catalog", and a
  direct lookup said "No course found". Now `NO_DESCRIPTION_NOTE` in tools.py says such a code is
  referenced in the catalog with no description and tells the model not to state a title; the
  direct lookup uses it when the code appears in `course_prerequisites`, and points to
  search_documents. A title from line 6013 was deliberately not added (no hand-made rows).
  Tests: 3 more in test_query_courses.py.
- *Answer in the wrong language* (6aebc91, 2026-10-08): an English scholarship question was
  answered in French. The prompt asked the model to detect the language itself. Measured first: langdetect
  (used for the tool label) was confidently wrong on chat-length text -- "ACC 2302
  prerequisites" -> fr (prob 1.0), "graduation requirements for computer science" -> fr, "date
  limite inscription" -> en -- and neither a confidence threshold nor a minimum word count fixed
  it, so passing its output as an order would have forced wrong-language answers. Replaced by
  app/agent/language.py: counts English vs. French function words (+1 French for an accented
  letter), returns "en"/"fr", or None on a tie (e.g. "GPA?", "ACC 2302 prerequisites"). 0 wrong,
  4 unsure on 27 questions not used to tune the word lists. main.py passes it through LangGraph's
  run config (`configurable.language`, not graph state: fixed for the run, no node changes it);
  `_agent_node` tells the model the language, or keeps the old "detect it" rule when None. The
  tool label uses the same detection, so label and answer agree. langdetect dependency removed.
  Tests: test_language.py (incl. an end-to-end check that the real graph passes the config to
  the node). Verified in the UI: EN, FR, "ACC 2302 prerequisites" (label now EN), and an English
  follow-up after a French turn all answered in the right language.
- *Uncited and duplicate sources* (bd6abae, 2026-10-08): an answer listed every passage any tool
  returned -- 15 for "What is MTH 1305?", though its 3 searches returned only 10 distinct chunks (chunk
  1030 three times, each copy numbered as a new source). Now `citation_number_for(key)` in
  citations.py gives a passage one number per request (key: `(source, chunk_index)`, or
  `("course", code)`), via a dict on the same mutable ContextVar object as the counter; a repeated
  search passage is sent to the model as a one-line "same passage as returned by an earlier
  search" note instead of its full text (5 of those 15 results). main.py joins the streamed
  answer and sends only the citations it cites (`keep_cited`; reads `[3]` and `[2, 4]`), so an
  answer citing nothing lists no sources. App.tsx: `<li value={marker}>`, since footnotes are no
  longer 1..N. Not done: the frontend still links only single `[N]` markers, not `[2, 4]`.
  Verified in the UI: MTH 1305 answer listed 2 sources (it cited [2], [3]), down from 15.
- *Footnote links jumped to the first answer* (bbad7ae, 2026-10-09, found in the walkthrough):
  every answer rendered `id="source-1"`, and duplicate ids make the browser jump to the first
  one. Ids now include the message index (`source-3-1`) via one `sourceId()` helper used for
  both the link and the footnote. Verified in the UI.
- *`[2, 4]` markers survived into history* (5222397, 2026-10-09, found in the walkthrough):
  history.py had its own regex matching only `[3]`. It now builds its pattern from
  citations.py's `CITATION_MARKER_RE` (renamed from `_CITED_RE`), so both agree on what a
  marker is. Test: test_history.py.
- Test suite: 50 tests, all passing. The backend passes `ruff check` and
  `ruff format --check` (last three files formatted in ff27da3).

**Next steps, in order (agreed 2026-10-11):**
1. **Faithfulness check with a baseline score** -- students don't use the assistant before it
   exists. Measures how often cited answers contain claims their cited passages don't support.
   Design (agreed):
   - Eval set: `eval/faithfulness_eval_set.json`, 34 questions = 17 topics, each asked in EN
     and FR. `set`: `main` (13 topics, the baseline), `regression` (2 known past failures:
     international scholarships, MTH 1305), `unanswerable` (2: Fulbright, CSC 3326's
     instructor; correct behavior is "I don't know"). No expected answers; `notes` say where
     the answer lives and which traps to watch.
   - Stage 1: run the real graph (same config as /chat), save each answer + the passage text
     behind each [N] to JSON, per question, so a run can resume the next day if Groq's daily
     limit cuts it off. Two answers per question if the Groq budget allows (run-to-run
     variance); measure token use on a few questions first.
   - Claim splitting in code (sentences/bullets; a piece with [N] is checked against only the
     passages it cites; unmarked factual pieces counted as "uncited"; markers pointing at no
     passage fail automatically).
   - Judge: Gemini Flash (different family from the gpt-oss-20b generator). Strict: "partly
     supported" = unsupported; a rule stated more generally than its passage (e.g. graduate
     rules given as general rules) = unsupported. The judge quotes its evidence and code checks
     the quote is really in the passage.
   - Youness hand-labels ALL claims from the first run, blind (labelling file without the
     judge's verdicts); agreement computed only after Youness is done, reporting especially "judge
     said supported, human said unsupported".
   - Report EN and FR separately, `main` separately from regression/unanswerable. Headline:
     % of answers with >=1 unsupported cited claim. Results committed under eval/results/.
   - Pilot threshold: set after the baseline, before any fixes.
   - Steps: (1) eval set [done], (2) passage text in the citation artifact + stage 1 script,
     (3) claim splitting + deterministic checks + unit tests, (4) judge + quote check,
     (5) baseline run, blind hand labels, agreement, record.
2. **Rate limit + daily cap**: per-IP rate limit and a global daily question cap (protects the
   Groq free-tier quota); access code for the pilot.
3. **Deployment for the student pilot**, then the demo video against the deployed version.
   Decided: a VPS running the same docker-compose.yml; frontend and API on one origin with the
   API under /api (no CORS, VITE_API_URL="/api"); .env only on the server (chmod 600);
   access code; privacy-preserving usage logging (question, language, tools, latency; no IPs or
   identities; a notice in the UI). Still to do: compare Azure for Students ($100 credit, no
   card; how long $100 lasts for a VM with enough RAM -- the API needs ~1-1.5 GB) against
   Hetzner, with current prices; a visible UI disclaimer that this is an unofficial student
   project, not an AUI service. Youness is checking with TeCom about a domain and getting
   permission before going live.

**Phase 7 progress (2026-10-09):** README written (26995cd): what it does, stack, design
decisions, evaluation numbers, setup from a fresh clone (the DB starts empty: 5 ingestion
commands), Docker and dev run modes, known limitations, what data leaves the server. Two Mermaid
diagrams in it (0f2b90d): answering a question, and the ingestion pipeline. Checked rendering on
GitHub via a temporary branch before fast-forwarding main. No CI badge (private repo: badges
don't show to visitors) -- add one if the repo is made public.

**Seen during the Compose check (2026-10-09), not fixed:** a follow-up answer re-cited a fact
from the previous turn (ACC 2302's prerequisite) with this turn's [1], which points at the
ACC 2301 entry -- a mild case of the "wrong facts next to citations" issue below.

**Answers render as Markdown** (c0e0d7a, 2026-10-09): react-markdown in App.tsx (no raw HTML).
`linkCitationMarkers()` rewrites each `[N]` that has a received citation into a Markdown link
to its footnote before rendering; an `a` override in `markdownComponents` shows those as
superscripts. Still single markers only (`[2, 4]` stays plain text). Bundle 223 -> 341 kB.

**Phase 6 summary (done 2026-10-09):** GitHub Actions CI is green: `.github/workflows/ci.yml`, three
jobs on every push to main and every PR.
- `frontend`: Node 24, `npm ci` from the committed lockfile, `npm run lint` (oxlint), then
  `npm run build` (`tsc -b` type-check + Vite build).
- `lint`: installs only `ruff==0.16.9` (pinned to the local version -- a newer ruff can format
  differently; bump both together), runs `ruff check` + `ruff format --check`. ~10 s.
- `test`: `pgvector/pgvector:pg16` service container (health-checked), POSTGRES_* set in the
  workflow (a throwaway DB, not secrets), CPU-only torch installed first (a plain install pulls
  the multi-GB CUDA build), `pip install -e ".[dev]"`, then `python -m app.ingestion.courses`
  seeds the courses before `pytest -v -rs`. The seed step doubles as a reachability check, so
  the DB tests can't silently skip. ~1.5 min. All 50 tests run, 0 skipped.
- `data/processed/academic_catalog_2024_2025.txt` is now tracked (.gitignore exception) so CI
  seeds from the same text as local runs; regenerate and recommit it if clean.py changes.
- *Fresh-database bug* (6abec8a), found by the first CI run: `get_connection()` registered the
  vector type before the extension existed, so the setup scripts couldn't create the schema on a
  new database. They now use `get_connection(register_vector_type=False)`; `init_schema()`
  registers the type after schema.sql runs. Verified on a scratch database.
- **Docker** (06a087c, 9f3b677, b3f8b6c): `backend/Dockerfile` (python:3.12-slim;
  layers: CPU torch -> deps read from pyproject.toml -> e5 model downloaded at build time,
  `HF_HUB_OFFLINE=1` -> app/; non-root; 2.9 GB, mostly torch + model; a code-only rebuild takes
  ~5 s). `frontend/Dockerfile` (multi-stage: Node builds, nginx:stable-alpine serves dist/;
  93 MB; `VITE_API_URL` is a build arg baked into the bundle -- must be a URL the *browser*
  reaches). `docker-compose.yml`: `db` (+ pg_isready healthcheck), `api` (env_file .env, then
  overrides POSTGRES_HOST=db, POSTGRES_PORT=5432, CORS_ORIGINS for :8080; waits for db healthy;
  port 8000), `frontend` (port 8080). `CORS_ORIGINS` is now env-configurable in config.py
  (comma-separated, default = the Vite dev origins).
  - Full stack: `docker compose up -d` -> http://localhost:8080 (stop local uvicorn first; both
    want port 8000). Back to dev: `docker compose stop api frontend` (or `down`; the db volume
    survives either). Dev workflow (`docker compose up -d db` + uvicorn + `npm run dev`) unchanged.
  - Verified: db healthy before api starts; data intact after the db container was recreated;
    CORS 200 for :8080, 400 for an unknown origin; question + follow-up in the browser.
  - Lesson: a first frontend build failed with a missing rolldown Linux binding, then kept failing
    from the cached layer; `--no-cache` fixed it (npm silently skips optional platform binaries
    whose download fails). Suspect cached layers when a build failure makes no sense.
- `ubuntu-latest` moves to Ubuntu 26 from 2026-10-19 (GitHub notice on every run). Nothing here
  depends on the OS version; pin `ubuntu-24.04` if a run breaks around then.

**Open issues / decisions to remember:**
- *GitHub* (set up 2026-10-08): private repo **TeCom0/campus-assistant**
  (https://github.com/TeCom0/campus-assistant). TeCom0 is Youness's *personal* GitHub account
  (not a club account), and the commits' author identity TeCom0 <tecomclub@gmail.com> was kept
  deliberately. Default branch `main` (renamed from `master` before the first push). GitHub CLI
  installed via winget (`C:\Program Files\GitHub CLI\gh.exe`), logged in as TeCom0 with the
  `workflow` scope (needed to push a GitHub Actions file in Phase 6); `gh auth setup-git` makes
  plain `git push` use that login. Push after every commit. Windows PowerShell 5.1 mangles
  double quotes inside `git commit -m "..."`, so write multi-line messages to a file and use
  `git commit -F <file>`. `.env` was checked: ignored, never in history.
- *Postgres port*: Docker maps to host port **15432**, not 5432/5433/55432 -- 5432 and 5433 both
  collided with native Postgres installs on this machine; 55432 then broke after a reboot because
  it landed in a Windows/Hyper-V dynamic port exclusion range (chunks of the 49152-65535
  ephemeral range get reserved for WSL2 NAT, and which chunks are excluded can shift on any
  reboot). 15432 sits below that whole range, structurally avoiding the issue rather than dodging
  today's specific exclusions. See Environment section above for the full diagnostic steps if a
  DB connection ever fails again -- don't assume credentials are wrong before ruling out the
  network layer.
- *Embedding model switch*: started with paraphrase-multilingual-MiniLM-L12-v2, switched to
  **intfloat/multilingual-e5-small** (384-dim, 512 token limit) after discovering the first
  model's 128-token limit was silently truncating 99.8% of real chunks. embed_passages()/
  embed_query() apply e5's required "passage: "/"query: " prefixes internally.
- *Known cross-lingual retrieval gap*: 2 of 4 French eval questions aren't retrieved by any
  method (vector, keyword, or hybrid) -- keyword search can't help here since there's no
  French text to match against our English-only documents. Needs a different mitigation
  later (e.g. query translation before retrieval), not more retrieval-side tuning.
  Vector Hit@3 58.3%/MRR 0.558, keyword 16.7%/0.167, hybrid 75.0%/MRR 0.646 (hybrid: no
  regressions vs. vector).
- *LLM provider*: Groq (primary, model `openai/gpt-oss-20b`) / Gemini (fallback,
  `gemini-3.5-flash`) via `LLM_PROVIDER` config in `.env`. Both API keys are set and verified
  working.
- *No ingestion-trigger endpoint yet* (mentioned in the target Architecture list, not required
  by the Phase 3 checklist item) -- add if/when actually needed, e.g. for the Phase 7 pilot
  deployment.
- *Known residual risk, not fully resolved*: the LLM can occasionally answer in the wrong
  language despite the system prompt's "same language as the question" rule. Mitigated by
  strengthening the prompt wording; not guaranteed, since LLM instruction-following is
  inherently stochastic. Since 2026-10-08 the model is told the detected language (see the
  bugs list above), which removes the guessing but is still a prompt rule; when detection is
  unsure (short keyword questions) the model still judges it itself.
- *Pattern: prompt-only rules keep failing* ("at most two searches", the prerequisite caution
  note, the language rule, bracket style). Where something must hold, enforce it in code or
  shape the tool output so the model doesn't have to infer it; keep prompt rules as guidance.
- *The model can still add facts no tool gave it* (e.g. the MTH 1305 title). Clearer tool output
  reduces this but can't rule it out.
- *Wrong facts next to citations, seen 2026-10-08* -- more serious than the above, since a cited
  claim looks verified. "Quelles bourses sont disponibles pour les étudiants internationaux ?"
  (answered twice) listed external scholarships "(ex. McCall MacBain, Fulbright)" -- "Fulbright"
  is in 0 chunks, and McCall MacBain is an award AUI students *won*, not a scholarship offered to
  them -- and "réduction de 10 000 MAD sur le loyer" for alumni children, where 10,000 MAD is
  actually the non-refundable advance paid to accept a scholarship. Not fixed. Needs measuring
  before fixing: an answer-faithfulness check (each cited claim vs. its cited chunk) added to the
  evaluation set, which so far only measures retrieval.
- *The agent pads search queries, which hurts retrieval* (seen 2026-10-08): for "What is MTH
  1305?" it searched "MTH 1305 Al Akhawayn University course description" (and quoted variants),
  missing the only chunk with its title (p. 155, "Mathematics for Business"). The same search
  ranks that chunk 1st for "What is MTH 1305?" and 2nd for "MTH 1305". In one later run (after
  NO_DESCRIPTION_NOTE pointed it to search_documents) it searched plain "MTH 1305" and found the
  title -- a single run, not evidence it's fixed. Not fixed yet -- candidate
  fixes: tool-docstring guidance to search with the question's key terms, or have query_courses
  run the search itself for a code with no description (code over prompt, per the pattern above).
- *Section headings get separated from their content during chunking* (found 2026-10-11,
  **fix after the faithfulness baseline**). chunk.py cuts fixed ~1000-char, line-aligned
  windows, so a heading can land in a different chunk from its rules: the undergraduate
  "Repeat Policy" heading is in chunk 281 and its rules in chunk 282 (a probation table sits
  between them), so the rules chunk never says what it's about. Chunks carry only
  source/chunk_index/pages/language/text -- the "section" metadata in the target Architecture
  was never implemented. Fix: track the current section heading while chunking and add it to
  each chunk's text (so both embeddings and keyword search see it) and to its metadata.
  Re-run retrieval + faithfulness evals before/after.
- *Undergraduate vs. graduate rules get confused* (found 2026-10-11, **fix after the
  faithfulness baseline**). The catalog has parallel undergraduate and graduate policies with
  different thresholds (repeat policy: C- or lower, pp. 120-121, vs. B- or lower, p. 314, chunk
  786); a search for "repeat a course" can return the graduate chunk, which has heading and
  rules together. Same risk for the scholarships page, which covers graduate scholarships only.
  Fix: tag chunks by level (undergraduate / graduate / both) during ingestion, so the agent can
  filter by level, or ask the student their level when the question doesn't say.
- *Data pipeline recap*: data/sources.md lists 3 AUI documents (catalog PDF + 2 scholarship
  pages) -> load.py/clean.py/chunk.py (data/raw/, data/processed/, 1161 chunks in
  chunks.jsonl) -> app/ingestion/store.py embeds and upserts into Postgres table
  document_chunks (vector(384) + model_name + source/chunk_index/pages/language/text,
  idempotent via unique constraint + upsert).
