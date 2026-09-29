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
- [ ] Phase 2: retrieval (vector, keyword, hybrid) + evaluation set to measure retrieval quality
- [ ] Phase 3: RAG answers with citations via FastAPI
- [ ] Phase 4: LangGraph agent with tools (docs search + SQL)
- [ ] Phase 5: React + TypeScript chat UI with streaming
- [ ] Phase 6: tests, Docker Compose for full stack, GitHub Actions CI
- [ ] Phase 7: README, architecture diagram, demo video, deployment for student pilot

## Current status
Phase 0 and Phase 1 (ingestion) done.
- Sources identified in data/sources.md (AUI Academic Catalog 2024-2025 PDF + 2 scholarship pages).
- load.py downloads raw files to data/raw/; clean.py extracts plain text to data/processed/
  (PDF keeps per-page markers for citations; HTML strips script/style/nav/header/footer/noscript).
- chunk.py splits into ~1000-char overlapping chunks (data/processed/chunks.jsonl, 1161 chunks),
  tracking source/pages/language per chunk, and reports token lengths against the embedding
  model's max_seq_length after every run.
- embeddings.py: multilingual embedding model, via app/config.py (EMBEDDING_MODEL_NAME =
  intfloat/multilingual-e5-small, 384-dim, 512 token limit). embed_passages()/embed_query()
  apply e5's required "passage: "/"query: " prefixes internally.
- app/db/ (schema.sql + connection.py) + app/ingestion/store.py: embeds all chunks and
  upserts them into Postgres table document_chunks (vector(384) + model_name + source/
  chunk_index/pages/language/text, unique on source+chunk_index+model_name for idempotent
  re-runs). Verified end-to-end: 1161 rows stored, a real query against the live table
  correctly retrieves the right catalog passage with correct page metadata.
- Postgres (Docker) runs on host port 55432, not 5432/5433 -- this machine has had native
  Postgres installs collide with both. See Environment section above before assuming a
  DB connection failure is a credentials bug.

Next: Phase 2 -- retrieval (vector, keyword/BM25, hybrid merge) and an evaluation set to
measure retrieval quality.
