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
- [built] Phase 5: React + TypeScript chat UI with streaming (sign-off after open item 1 below)
- [ ] Phase 6: tests, Docker Compose for full stack, GitHub Actions CI
- [ ] Phase 7: README, architecture diagram, demo video, deployment for student pilot

## Current status

**Phases 0-4 done, Phase 5 built.** Phases 0-3: repo/Docker setup, the full ingestion pipeline,
all three retrieval methods with a measured evaluation baseline, grounded/cited RAG generation.
Phase 4: the LangGraph agent, wired into `/chat`. Phase 5: the React + TS chat UI and multi-turn
history. Verifying Phase 5 in the browser (2026-10-06) found bugs; three are fixed, the rest are
the numbered next steps below.

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

**Bugs found while verifying Phase 5 (2026-10-06), fixed:**
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
- *"Not in the catalog" for a real course* (2026-10-08): the agent once called MTH 1305
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
- *Answer in the wrong language* (2026-10-08): an English scholarship question was answered in
  French. The prompt asked the model to detect the language itself. Measured first: langdetect
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
- *Uncited and duplicate sources* (2026-10-08): an answer listed every passage any tool returned
  -- 15 for "What is MTH 1305?", though its 3 searches returned only 10 distinct chunks (chunk
  1030 three times, each copy numbered as a new source). Now `citation_number_for(key)` in
  citations.py gives a passage one number per request (key: `(source, chunk_index)`, or
  `("course", code)`), via a dict on the same mutable ContextVar object as the counter; a repeated
  search passage is sent to the model as a one-line "same passage as returned by an earlier
  search" note instead of its full text (5 of those 15 results). main.py joins the streamed
  answer and sends only the citations it cites (`keep_cited`; reads `[3]` and `[2, 4]`), so an
  answer citing nothing lists no sources. App.tsx: `<li value={marker}>`, since footnotes are no
  longer 1..N. Not done: the frontend still links only single `[N]` markers, not `[2, 4]`.
  Verified in the UI: MTH 1305 answer listed 2 sources (it cited [2], [3]), down from 15.
- Test suite: 49 tests, all passing.

**Next steps, in order:**
1. Phase 5 code walkthrough (interview depth): how chatStream.ts/App.tsx parse the SSE stream,
   how citations get linked, how history.py decides what history to send.
2. `ruff format` connection.py, llm.py and keyword_search.py (they already fail
   `ruff format --check`; would break a CI format check).
3. Phase 6: GitHub Actions CI (ruff + pytest) with a Postgres service container, so the DB tests
   run instead of skipping -- needs the schema and seeded courses, and the POSTGRES_* env vars
   app/config.py requires at import.

**Open issues / decisions to remember:**
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
- *Data pipeline recap*: data/sources.md lists 3 AUI documents (catalog PDF + 2 scholarship
  pages) -> load.py/clean.py/chunk.py (data/raw/, data/processed/, 1161 chunks in
  chunks.jsonl) -> app/ingestion/store.py embeds and upserts into Postgres table
  document_chunks (vector(384) + model_name + source/chunk_index/pages/language/text,
  idempotent via unique constraint + upsert).
