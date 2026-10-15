# Campus AI Assistant (working name)

## What this project is
A multilingual (English/French) AI assistant for Al Akhawayn University students. It answers questions
about academic policies, the course catalog, and scholarships, always citing its sources, and uses an
agent to query structured data (e.g. "what are the prerequisites for ACC 2302?"). The goal is to deploy
it publicly for real students and publish the repo. It is an unofficial student project, not an
official AUI service (the UI must say so). AUI has confirmed they are fine with the project, so
the catalog text can stay in the public repo.

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
- [wip  ] Phase 7: README, architecture diagram, faithfulness baseline, deployment, demo video
  (README + diagram done) -- finished through the Ship plan below

## Ship plan (agreed 2026-10-15) -- the finish line

Supersedes "Next steps (agreed 2026-10-11)" below where they differ. Done = the live HTTPS URL
shows the unofficial-project disclaimer, requires the access code and enforces the daily cap;
the README reports the baseline and after-fix faithfulness numbers with the judge's measured
agreement next to them; a full-history secrets scan is clean; the repo is public; a demo video
of the deployed version exists. Anything not listed here goes to "Future work" in the README.

- [x] **0. Prep** (done 2026-10-15): paid-Gemini judge switch reverted; this plan recorded;
  host = **Azure for Students** (account set up); MISTRAL_API_KEY in .env. Domain = free: a
  Namecheap domain from the GitHub Student Pack (Youness claims it later, needed by step 4),
  DuckDNS as fallback. **Early secrets scan: clean** -- gitleaks v8.24.0 (Docker image, no
  install) found no leaks in all 90 commits nor in the uncommitted eval/results/. Positive
  control: the same scan on .env flags all 3 keys (generic-api-key rule), so the scanner does
  catch our key formats. Command, from Git Bash (MSYS_NO_PATHCONV stops path mangling;
  safe.directory because the mounted repo has a different owner):
  `MSYS_NO_PATHCONV=1 docker run --rm -v "C:/dev/campus-assistant:/repo:ro" --entrypoint sh
  zricethezav/gitleaks:v8.24.0 -c "git config --global --add safe.directory /repo && gitleaks
  git /repo --redact --no-banner -v"`. The GitHub name TeCom0 and the commit email stay
  (decided: Youness's personal account, unrelated to the club).
- [ ] **1. Judge + baseline** -- **update 2026-10-15**: Mistral's free plan offered no Large
  model on our key (403 tier_not_allowed; Small/Medium at 0 requests/min), so Youness enabled
  pay-as-you-go ($10 credit). Judge = **mistral-large-2512** (ec4e089: exact id, sliding-window
  throttle for requests/s + tokens/min, bounded retry, per-call tokens + cost estimate).
  API headers say 15 requests/min and 400k tokens/min (the console said 1/s and 250k; the
  stricter of each is used). **Calibration 9/9** (incl. the graduate "B- or lower" case Qwen
  missed), 2 calls, ~$0.002.
  **Run 1 vs. the original gate: FAILED** -- 27/40 (68%, CI 52-80%), kappa 0.223, 3 lenient,
  6 strict (4 of them quote_not_found), 29/40 before the quote check; 32 calls, ~$0.06.
  **Gate changed 2026-10-15, recorded BEFORE any re-run or any agreement against adjudicated
  labels was computed.** Why: the original gate (>= 32/40) was above human reliability --
  Youness's own two passes (quick pass vs. careful sample) agree on only 31/40 of the same
  claims -- and several disagreements were definition problems (refusals, lead-in fragments,
  advice), not judge errors.
  - Adjudication (1b97637): the 13 disagreements were decided by Youness in
    eval/results/faithfulness/adjudications_run1.json (original / judge_raw / judge / decision
    / note). labels_run1_sample.json is untouched and stays the original reference. The
    adjudication was NOT blind (judge label + quote visible), so it may lean toward the judge:
    always report agreement against both the original and the adjudicated labels.
    Decisions: 8 kept the original label (incl. the 4 quote_not_found cases: raw supported =
    adjudicated supported), 4 sided with the judge, 1 (academic_probation_en#2) -> no_claim.
  - **New gate** for the judge (all must hold):
    (a) calibration 9/9 (unchanged from the original gate);
    (b) agreement with the **adjudicated** labels >= **31/36 (86%)** on the 36 sample claims
        left after step (2)'s filter;
    (c) at most **2 lenient errors** (judge supported, adjudicated unsupported) on those claims.
    History of (b): first recorded as 77.5% = Youness's 31/40 self-agreement on the
    unfiltered 40. After the filter (step 2) his self-agreement on the same 36 claims is
    31/36 = 86% -- the 4 excluded claims were among the ones his two passes disagreed on.
    Changed 2026-10-15 to 31/36 (Youness's decision) because the gate's principle is
    "agreement at least equal to Youness's self-agreement on the same claims"; it is also
    the stricter of the two, and was chosen before any re-run or any adjudicated agreement
    number existed.
    Always reported next to it, not part of the pass/fail: agreement against the original
    labels, kappa, Youness's self-agreement recomputed on the same filtered claims, and quote
    validity as its own number (step 3).
  - **Step (2) done**: split_claims.exclusion_reason() sets `exclude` on each claim --
    `refusal` (no own marker, sentence STARTS with a first-person "couldn't find / don't
    have / je n'ai pas trouvé / je ne dispose pas", after at most an apology and a "based
    on ...," clause; so fulbright_fr#2's speculation-then-refusal is still judged) or
    `lead_in` (ends with ":", <= 6 words, no digit, no own marker). Tight on purpose: keeping
    a fragment only adds a no_claim, dropping a fact could hide an unsupported claim. Claim
    ids unchanged (re-split verified identical except the new field). Excluded: run 1 7
    lead-ins + 5 refusals, run 2 7 + 6; sample 40 -> 36 (gate: >= 31/36, see (b)). Excluded claims
    aren't sent to the judge; an answer with nothing left to judge still gets a
    decline-only call (fixes the missing abstains of all-auto-labelled answers like run 1's
    mth1305_fr). report.py checks each answer's decline verdict against expected_behavior:
    **false refusals** (declined, should answer) and **missed refusals** (answered, should
    decline) with ids, plus answers with no verdict, and lists every excluded claim.
    agreement.py drops excluded claims on both sides and lists them; self-agreement on the
    36: 31/36. Smoke test on the OLD (pre-filter) judgements: false refusals
    scholarship_conditions_fr + mth1305_fr, missed refusal instructor_en (a pure refusal the
    judge said doesn't decline -- the judge's error). The v1 agreement is saved as
    agreement_run1_mistral_v1.json.
  - Remaining plan: (3) report label agreement and quote validity separately; (4) document the
    original gate, why it was unreachable and this change in the README; (5) re-judge run 1
    with mistral-large-2512 and apply the new gate. If it fails: mistral-large-4, zai-glm-5-3,
    ministral-14b-2512, then GitHub Models / best-agreement judge.
  Original plan (~1.5 sessions, 2-4 days of quotas): the judge must be **free**
  (paid Gemini dropped). Third family = **Mistral Large** on Mistral's free Experiment plan
  (Youness creates the account, SMS verification; check the model is included and whether
  prompts may be used for training -- only public catalog text and generated answers are sent).
  Add a "mistral" provider to judge_claims.py: throttle to its ~1 request/second, resumable
  runs (already per-answer). **Gate (decided): calibration 9/9 AND >= 32/40 agreement with the
  careful sample AND <= 2 lenient errors.** If no judge passes, use the best-agreeing judge
  (Qwen so far: 25/40) and show its agreement next to every number -- not gpt-oss-120b by
  default (8/9 on calibration, same family as the generator). Then: judge run 1 -> agreement
  -> run 2 -> report -> threshold for going live -> commit eval/results/. Youness's original
  sample labels stay the reference; any adjudication goes in a separate file.
- [ ] **2. Fix 2-3 issues, re-evaluate** (~2 sessions, 3-4 days): tag each unsupported claim
  with a cause (together), fix the 2-3 biggest (likely: forced-answer crash, headings +
  undergraduate/graduate tags in chunks, citation placement -- confirm from the analysis),
  generate runs 3 + 4 (~1 Groq day each), judge, compare with the baseline (counts per cause
  too: 24 main answers per run only shows large effects).
- [ ] **3. Rate limit + daily cap + access code** (~1 session; write it while step 2 waits on
  quotas): per-IP limit (real client IP from the proxy header), global daily cap stored in
  Postgres, shared access code checked server-side, friendly message on a Groq 429, UI prompt,
  tests. All evaluation runs finish before go-live: the app and the eval share gpt-oss-20b's
  200k tokens/day.
- [ ] **4. Deploy** (1-2 sessions): Azure VM, same docker-compose.yml, Caddy in front
  (automatic Let's Encrypt HTTPS, one origin with the API under /api), .env only on the server
  (chmod 600), load the DB, UI disclaimer, smoke test on the live URL.
- [ ] **5. Final README + CLAUDE.md cleanup** (2-3 h): results, live link, limitations, Future
  work; CLAUDE.md stays public, cleaned of stale and personal notes.
- [ ] **6. Secrets check + go public** (1-2 h): fix the pytest hang when Postgres is
  unreachable first (see open issues); gitleaks over the full history; review what
  becomes public (CLAUDE.md, Actions logs); make public; add the CI badge.
- [ ] **7. Demo video** of the deployed version.

Future work (not part of the finish line): usage logging; query translation for the French
retrieval gap; search-query padding; citable query_courses "no description" result (unless
picked in step 2); linking `[2, 4]` markers; ingestion endpoint; re-judging with paid Gemini;
more hand labels; pinning `ubuntu-24.04` in CI.

## Current status

**Phases 0-6 done; Phase 7 in progress (README + diagrams done).** Session 2026-10-09: Phase 5
code walkthrough (2 bugs found and fixed), Phase 6 built and signed off (CI with 3 jobs, Docker
images, full stack in Compose, Markdown answers), README and architecture diagrams written.
Session 2026-10-11: Youness decided no students use it before a faithfulness baseline exists.
Built the whole faithfulness pipeline (eval set of 34 EN/FR questions, answer generation,
claim splitting with citation-scope rules, Gemini judge with a verbatim quote check, blind
labelling page, agreement statistics; 102 tests), ran run 1 (34 answers, 156 claims), and
Youness hand-labelled a careful 40-claim sample as the reference. Found on the way: the
forced-final-answer crash, query_courses' uncitable "no description" result, Groq's 8k
tokens/minute and Gemini's 20 requests/day free-tier limits (both matter for the pilot).
Session 2026-10-12: judge calibration 9/9 but Gemini 503s stopped run-1 judging at 1/8
batches; fixed the judge chain so it can't report agreement on partial results (f1a3915);
run 2 generated and split; baseline report script (5c2b1af). Session 2026-10-13: free
Gemini stayed unusable; a Qwen-on-Groq judge (8/9 calibration) judged run 1 but agreed with
the 40 hand labels only 25/40 (kappa 0.20) -- not trustworthy. Session 2026-10-15: the
paid-Gemini plan was dropped (the judge must be free); the **Ship plan** above is the
order of work from here. If Gemini is ever used again, the name Google serves is
`gemini-3.6-flash` (config.py's 3.5 is routed to it). The Qwen results are kept as *_qwen* files in
eval/results/faithfulness/ (judgements_run1_qwen.jsonl, judgements_run2_qwen_partial.jsonl,
agreement_run1_qwen.json, report_runs_1_qwen.json) for a judge-vs-judge comparison.
Optional before or after: adjudicate the judge/human disagreements (Qwen had 15; e.g.
repeat_course_en#2's note says "this inst supported" but its label is supported). Youness asked
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
   - Passage text comes from the citation artifacts (`text`, added in step 2a; main.py strips
     it before sending citations to the browser). `query_courses` returns its citation on a
     repeated lookup too, so one marker can have several texts (e.g. without, then with the
     prerequisite chain): stage 1 saves every distinct text per marker, and the judge checks a
     claim against all of them combined (the quote check accepts a quote found in any of them).
   - Claim splitting in code: app/evaluation/split_claims.py -> claims_runN.jsonl. Blocks
     (paragraphs, list items, table rows rendered with their headers) -> sentences. Which
     passages a claim is checked against = first rule that applies: `own` (its markers),
     `block` (markers elsewhere in the same paragraph/item/row), `lead_in` (list item / table
     row only: nearest preceding cited block in the same section -- Youness's rule), `source_line`
     (blocks saying where the answer comes from, not facts: "Source: [1]", markers alone on a
     line, "This information is taken from the catalog [5]", a citation key "Holds and form
     requirement: [4]", a reference entry "[1] (repeat policy: ...)", items under a
     "Sources"/"Key citations" heading -- their markers cover all still-unassigned claims), else
     `uncited` (judged against all the answer's passages, reported separately). Prose
     paragraphs don't inherit. Every rule beyond `own` came from a real run-1 answer (named in
     tests/test_split_claims.py): models cite once per paragraph, in closing source lines, in
     key lists under a table, or on a line of their own. Report the headline over all cited
     kinds AND over `own` only, to see how much the scope rules matter. Filler/advice isn't
     filtered in code: judge and human label it `no_claim`. Markers pointing at no passage:
     auto-unsupported if all are invalid; not sent to the judge or the hand labels.
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
   - Judge (step 4, app/evaluation/judge_claims.py): one Gemini call per answer, output forced
     into a pydantic schema (`AnswerVerdict`: `abstains` + per-claim label/evidence_quote/
     reason), temperature 0. Code checks a "supported" quote verbatim (case, quotes, dashes,
     spaces normalized; "a ... b" allowed in order) in that claim's passages -- not found ->
     unsupported, flag `quote_not_found`. Waits out Gemini 429 per-minute limits and 503 "high
     demand" (hit 3x in a row on 2026-10-11). `--calibration` judges eval/judge_calibration.json
     (9 hand-made claims from real chunks, known labels: wrong number, contradiction, graduate
     rule given to an undergraduate, partly wrong, FR claim vs EN passage, advice): 9/9 on
     2026-10-11 -- shows the rules are understood, NOT agreement on real claims. **Blind
     guard**: refuses `--run 1` until every claim and answer in labels_run1.json is labelled
     (`hand_labels.labels_complete`). The terminal prints counts only, never labels.
   - **Gemini free-tier limits (found 2026-10-11)**: 20 requests/day/model, and long 503 "high
     demand" spells (5+ minutes); failed attempts appear to count toward the 20. The quota
     error names the model **gemini-3.6-flash** although config.py says gemini-3.5-flash --
     Google seems to route the name; record the judge model as reported. Run 1 judging stopped
     at 5/32 answers (judgements_run1.jsonl); retries now wait 60/120/.../300 s and stop
     cleanly ("re-run to resume") on a lasting 503 or the daily 429. 32 calls per run didn't
     fit in 20/day -> **decided (Youness, option B): batch 4 answers per call** (b530db1): 8
     calls per run, prompts up to ~11k tokens, each answer in its own block ("passage numbers
     belong to their block"). The 5 answers judged one-per-call moved to
     judgements_run1_unbatched.jsonl; run 1 is re-judged entirely batched for consistency.
     `--calibration` (1 call, batched) exits non-zero unless 9/9.
   - **2026-10-12**: calibration 9/9; judging run 1 stopped after 1 of 8 batches (4 answers,
     17 claims in judgements_run1.jsonl) on a lasting Gemini 503, ~14 of the day's 20 requests
     used (11 were failed 503 attempts). It exited 0, so the chain ran agreement on 4 of 40
     claims -- meaningless, file deleted. Fixed: judge_claims exits 1 when stopped early;
     agreement refuses until every reference claim is judged. Resume with `--run 1` (skips
     judged answers). Quick pass vs. careful sample agree on 31/40 claims. A retry at 17:08
     UTC got 6 more 503s (still no 429, so whether failed attempts count is unknown).
     **Run 2 generated + split (2026-10-12)**: answers_run2.jsonl, 30 answered + 4 errors
     (add_drop_fr, course_load_en, course_load_fr, fulbright_fr -- all the forced-answer
     400), ~171k Groq tokens; claims_run2.jsonl 148 claims (own 41, block 19, lead_in 14,
     source_line 10, uncited 64; 2 auto-unsupported). Forced-answer crash: 6/68 attempts
     over both runs (~9%; course_load_en both times). A background chain was set to run at
     00:10 UTC 2026-10-13: judge run 1 && agreement && judge run 2. If judgements_run2.jsonl
     doesn't exist, run those three by hand (commands below).
   - **2026-10-13 00:28 UTC**: the first judge call got the *daily* 429 ("limit: 20, model:
     gemini-3.6-flash") although nothing had been sent since 2026-10-12 17:30 UTC. So
     (a) **failed 503 attempts count** toward the 20 (that day: 2 successful calls + 18
     failed attempts), and (b) the quota does **not** reset at 00:00 UTC: Google documents
     midnight Pacific time (07:00 UTC in summer time, 08:00 in winter time); the error's
     own "retry in 23h31m" disagrees, so one attempt after 07:00 UTC settles it (a
     refused call costs nothing). Fix 3: at most 3 attempts per batch, waits 120 s / 240 s.
     The judge model as served is gemini-3.6-flash; the records' `judge_model` field says
     gemini-3.5-flash (config name) -- name 3.6 in the baseline write-up.
   - **Judge switched to Qwen on Groq (2026-10-13, 7e1258c + a20f9f0)** -- free Gemini
     unusable (3 more 503s at 07:10 UTC; gemini-2.5-flash gone (404); 3.8-flash dropped the
     connection). Youness will pay for Gemini later and re-judge then; Qwen results are a
     **preliminary** baseline. `JUDGE_PROVIDER` in judge_claims.py switches back. Qwen
     (qwen/qwen3.8-27b) scores **8/9 on calibration**: it labels the graduate-only "B- or
     lower" repeat rule given to an undergraduate "supported" (gpt-oss-120b too, even at
     high reasoning effort; the passage literally says "A student may repeat any course in
     which a B- or lower has been earned", graduate only by context). Groq limits for Qwen:
     8k tokens/min, **1k output tokens/min**, **200k tokens/day**, 1k requests/day. Fixes:
     strict JSON schema, one answer per call returning {verdicts, abstains}
     (`SingleAnswerVerdict` -- with the answer list Qwen stalled on plagiarism_en), claims
     in groups of 6. Old Gemini batch: judgements_run1_gemini_partial.jsonl.
   - **Run 1 judged by Qwen; agreement with the 40-claim sample: 25/40 = 62% (95% CI
     47-76%), kappa 0.20** -- 4 lenient (judge supported / human unsupported), 8 strict, 3
     no_claim mix-ups; the quote check turned 3 human-supported claims unsupported (28/40
     before it: Qwen quotes less verbatim). Abstains 23/23. Run 1 report (preliminary):
     main 8/24 = 33% answers with >=1 unsupported cited claim (EN 5/12, FR 3/12),
     regression 2/4, unanswerable declined 4/4. **Run 2 judging stopped** at
     academic_probation_en on Qwen's 200k tokens/day (run 1 + probes used it); re-run
     `judge_claims --run 2` to resume. Next: adjudicate the 15 disagreements.
   - **Pending as of 2026-10-11 17:50 UTC**: a background chain in that session waits for the
     Gemini quota reset (~00:00 UTC), then runs calibration && judge run 1 && agreement. If the
     session ended first, run by hand from backend\: `python -m app.evaluation.judge_claims
     --calibration`, then (if 9/9) `python -m app.evaluation.judge_claims --run 1`, then
     `python -m app.evaluation.agreement --run 1`. Then: run 2 (new Groq day) -> split ->
     judge; baseline report; pilot threshold.
   - Agreement (app/evaluation/agreement.py -> agreement_runN.json): reference labels vs. the
     judge's final labels on the same claims; raw agreement + Wilson 95% CI, Cohen's kappa,
     confusion, lenient (judge supported / human unsupported) vs. strict errors listed
     separately, effect of the quote check, abstains agreement, quick pass vs. careful sample.
     Not run on real data yet (waiting for the judge).
   - Hand labels (app/evaluation/hand_labels.py + labelling_template.html): `python -m
     app.evaluation.hand_labels --run 1` writes eval/results/faithfulness/labelling_run1.html,
     a self-contained offline page (32 answers, 153 claims; auto-labelled claims and crashed
     answers left out; the question's `set` hidden to avoid bias; no judge data). Click a claim
     -> its "check against" passages highlighted; keys 1/2/3 = supported/unsupported/no_claim,
     j/k claims, n/p answers; abstains yes/no per answer. Autosaves in the browser
     (localStorage); "Export labels" downloads labels_run1.json -> move it into
     eval/results/faithfulness/; "Import" restores one. `--check` lists what's unlabelled.
     Chosen over a CSV: Excel on a French locale expects ";" and mangles UTF-8, and labelling
     needs claim and passages side by side. Browser-checked 2026-10-11 (labels, abstains,
     progress, navigation, uncited -> all passages, import incl. wrong-run refusal).
   - **Run 1's full hand pass is NOT the reference** (2026-10-11): the first pass labelled only
     each answer's first claim (the page didn't show more cards below -- fixed, b049d38: per-
     answer "N claims, M labelled" line); the completed pass took ~11 min for 121 claims (~5 s
     each, too fast to read the passages) and gave 148 supported / 4 unsupported / 0 no_claim.
     Kept as labels_run1.json ("quick pass", 1 claim missing) for comparison only. Youness chose
     **option A: a careful 40-claim sample as the reference** -- `--sample 40` drew it
     (sample_run1.json, seed 20261011, proportional to kind x language, max 3 per answer: 20 EN
     / 20 FR, uncited 18, source_line 9, own 8, lead_in 3, block 2; 23 answers) and wrote
     labelling_run1_sample.html (own storage key and export file labels_run1_sample.json; starts
     empty; refuses the quick-pass file on Import). The judge guard and `--check` now use the
     sample once sample_run1.json exists. Agreement is measured on these 40 (~±10 points);
     the judge still labels all 153.
   - Steps: (1) eval set [done], (2) passage text in the citation artifact + stage 1 script
     [done], (3) claim splitting + deterministic checks + unit tests [done], (4) judge + quote
     check [done], (5) blind hand labels on run 1 -> judge run 1 -> agreement; run 2 (new day's
     Groq quota) -> split -> judge; report; record.
   - **Run 1 done (2026-10-11)**: eval/results/faithfulness/answers_run1.jsonl, 34 answers, 32
     answered + 2 errors (the forced-answer crash, see open issues), ~169k Groq tokens (~5.3k
     per answered question, 2-4 LLM calls). claims_run1.jsonl: 156 claims (own 33, block 8,
     lead_in 14, source_line 35, uncited 66; 3 auto-unsupported, all in mth1305_fr, which cites
     a [1] no tool returned). Not committed yet: results are committed once, at step 5.
     **Run 2 needs a new day's Groq quota** (a run costs ~85-95% of 200k/day).
2. **Rate limit + daily cap**: per-IP rate limit and a global daily question cap (protects the
   Groq free-tier quota); access code for the pilot. **Size it from the measured limits**
   (found 2026-10-11 during faithfulness run 1): Groq free tier for gpt-oss-20b is 200k tokens
   per day, 1k requests per day AND **8,000 tokens per minute**; a question costs ~3-11k tokens
   (2-4 LLM calls; run 1 averaged ~5.3k per answered question). So the whole pilot can serve roughly
   **40 questions/day and 1-2 per minute across all students** -- one question can exceed the
   per-minute limit on its own. /chat would show a 429 as a generic error. Options to decide
   before the pilot: fall back to Gemini on a Groq 429, a paid Groq tier, or a cap this small.
   **But Gemini's free tier is no real fallback**: 20 requests/day/model (found 2026-10-11 by
   the judge run, quota `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, value 20; failed
   503 attempts appear to count too) = ~5-10 student questions/day.
   The evaluation shares the same quota (a full run ~150k tokens): don't run it on pilot days.
3. **Deployment**, then the demo video against the deployed version (details: Ship plan,
   steps 4 and 7). Decided: a VM running the same docker-compose.yml; frontend and API on one
   origin with the API under /api (no CORS, VITE_API_URL="/api"); .env only on the server
   (chmod 600); access code; a visible UI disclaimer that this is an unofficial student
   project, not an AUI service. Host decided 2026-10-15: Azure for Students ($100 credit, no
   card; the API needs ~1-1.5 GB RAM -- size the VM from that). Usage logging moved to future
   work.

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
- *pytest hangs when Postgres is unreachable* (found 2026-10-15, **fix before the repo goes
  public**, Ship plan step 6): with Docker Desktop stopped, `pytest` stalled at "collecting ..."
  (no output after 280 s) instead of skipping the DB tests; with the db container up the suite
  ran in 22 s. Cause (read, not yet tested): tests/test_query_courses.py's `_db_available()`
  runs at collection time and calls `get_connection()` -> `psycopg.connect(DATABASE_URL,
  autocommit=True)` in app/db/connection.py, which has no `connect_timeout`, so a connection
  that never completes blocks the whole collection (connection refused would raise
  OperationalError at once; the stall suggests something still accepts or holds the port with
  Docker down). Fix: a short `connect_timeout` for the availability check (and likely a
  sensible default in get_connection), plus a test that an unreachable host skips within
  seconds.
- *GitHub* (set up 2026-10-08): private repo **TeCom0/campus-assistant**
  (https://github.com/TeCom0/campus-assistant). TeCom0 is Youness's *personal* GitHub account;
  the commits' author identity is TeCom0 <tecomclub@gmail.com>. Default branch `main` (renamed from `master` before the first push). GitHub CLI
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
- *Forced final answer can still crash* (found 2026-10-11 by faithfulness run 1, **fix after
  the baseline**): course_load_en used all 3 tool rounds in ~12 s; in the forced-answer path
  (no tools bound, conversation rewritten without tool structure -- the 432d0af fix) gpt-oss-20b
  still emitted a tool call, `search_documents` with invented args `topn`/`source` (its
  built-in browsing-tool habit), and Groq returned 400 "Tool choice is none, but model called a
  tool". /chat would end that answer with an error. The 432d0af rewrite lowered the odds but
  doesn't prevent it. Candidate fixes: catch that 400 and retry the forced call once (maybe
  with a stronger "answer in plain text" instruction), or fall back to a canned "couldn't
  complete" answer listing the passages found. Recorded as an error in the baseline.
- *query_courses' "no description" result can't be cited* (found 2026-10-11 by run 1, **fix
  after the baseline**): for a code with no courses row (MTH 1305) it returns
  NO_DESCRIPTION_NOTE text with no [N] marker and no citation, so anything the model says from
  it is either uncited or cites a marker it invented -- mth1305_fr cited a [1] no tool
  returned (3 auto-unsupported claims). Fix: give that result a marker and a citation (source:
  the catalog's course_prerequisites reference), so it can be cited honestly.
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
