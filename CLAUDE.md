# Campus AI Assistant (working name)

## What this project is
A multilingual (English/French) AI assistant for Al Akhawayn University students. It answers questions
about academic policies, the course catalog, and fellowships, always citing its sources, and uses an
agent to query structured data (e.g. "which fellowships close this month?"). The goal is to deploy it
to real students through TeCom (the student tech club) and measure real usage.

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
- Postgres (Docker) is mapped to host port 55432, not 5432. This machine has had native
  Postgres installs bind to both 5432 and 5433 at different times, which caused connections
  from the host to silently hit the wrong server (password authentication failures that had
  nothing to do with the actual password). 55432 avoids the collision. If a similar port
  conflict ever resurfaces, check `Get-NetTCPConnection -LocalPort <port> -State Listen` and
  confirm the owning process is Docker's (`com.docker.backend`/`wslrelay`) before assuming the
  app's credentials are wrong.

## Stack
- Backend: Python 3.12, FastAPI
- Orchestration: LangChain + LangGraph
- LLM: Groq free tier (primary), Google Gemini Flash free tier (fallback).
  Provider must be switchable through one config value. Free tiers have tight daily token limits:
  cache where sensible, keep prompts lean, never loop on LLM calls without a cap.
- Embeddings: open-source multilingual model via sentence-transformers, running locally (CPU)
- Database: PostgreSQL + pgvector (vectors), Postgres full-text search or BM25 (keywords), normal
  tables for structured data (e.g. fellowships with deadlines)
- Frontend: React + TypeScript (Vite), streaming chat UI with citations
- Quality: pytest (unit + integration), an evaluation set of questions with expected answers,
  ruff for linting
- Infra: Docker Compose (db + api + frontend), GitHub Actions CI (lint + tests)

## Architecture (target)
1. Ingestion: load public university documents (PDF/HTML) -> clean -> chunk -> embed -> store in pgvector
   with metadata (source, page, language, section).
2. Retrieval: hybrid search = vector similarity + keyword/BM25, merged (e.g. reciprocal rank fusion).
3. Generation: answer ONLY from retrieved chunks, cite sources, say "I don't know" when context is missing.
4. Agent (LangGraph): tools = search_documents, query_fellowships (SQL), and more later.
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
- [ ] Phase 4: LangGraph agent with tools (docs search + SQL)
- [ ] Phase 5: React + TypeScript chat UI with streaming
- [ ] Phase 6: tests, Docker Compose for full stack, GitHub Actions CI
- [ ] Phase 7: README, architecture diagram, demo video, deployment for student pilot

## Current status

**Finished this session:** Phases 0-3, end to end -- repo/Docker setup, the full ingestion
pipeline, all three retrieval methods with a measured evaluation baseline, and grounded/cited
RAG generation behind a streaming FastAPI endpoint. Session ended cleanly; working tree is
clean (nothing uncommitted).

**In progress:** nothing -- this is a clean phase boundary. Phase 4 has not been started.

**Exact next step:** Phase 4 -- LangGraph agent with tools (`search_documents` wrapping the
existing `search_hybrid()`, `query_fellowships` via structured SQL -- note fellowship
deadlines aren't ingested as structured data yet, so that tool needs its own small schema/
ingestion first). Start by explaining LangGraph's state/graph concepts before writing code,
per the working style above.

**Open issues / decisions to remember:**
- *Postgres port*: Docker maps to host port **55432**, not 5432/5433 -- this machine has had
  native Postgres installs collide with both, causing misleading "password authentication
  failed" errors that were actually a wrong-server problem, not a credentials problem. See
  Environment section above; verify with `Get-NetTCPConnection` before assuming credentials
  are wrong if this resurfaces.
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
  inherently stochastic -- revisit if it shows up again during Phase 4/5 testing.
- *Data pipeline recap*: data/sources.md lists 3 AUI documents (catalog PDF + 2 scholarship
  pages) -> load.py/clean.py/chunk.py (data/raw/, data/processed/, 1161 chunks in
  chunks.jsonl) -> app/ingestion/store.py embeds and upserts into Postgres table
  document_chunks (vector(384) + model_name + source/chunk_index/pages/language/text,
  idempotent via unique constraint + upsert).
