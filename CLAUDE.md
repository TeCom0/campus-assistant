# Campus AI Assistant -- notes for Claude Code

Instructions for AI coding assistants working in this repo. The README is the user-facing
description; this file is how the project is worked on.

## What this project is

A bilingual (English/French) AI assistant for Al Akhawayn University (AUI) students. It answers
questions about academic policies, the course catalog and scholarships, always citing its
sources, and uses an agent to query structured course data (e.g. "what are the prerequisites for
ACC 2302?"). It is an unofficial student project, not an official AUI service (the UI says so).
AUI has confirmed they are fine with the project, so the catalog text can stay in the repo.

Live demo: https://campus-assistant.denmarkeast.cloudapp.azure.com

It is also a portfolio project for AI Software Engineer internship applications, so it must
demonstrate: RAG, AI agents, hybrid search, REST APIs, a TypeScript frontend, tests, Docker,
CI/CD, and evaluation.

## Working style (IMPORTANT, follow strictly)

- This is a learning project. Youness (the author) must be able to understand and defend every
  line in an interview.
- Work in small steps. One step per turn. Never scaffold large parts of the project at once.
- Before writing code: explain what the step does, why, and which concepts are involved.
- After writing code: explain the key lines, then say exactly what to run to verify it.
- Wait for Youness to confirm the step works before moving to the next one.
- When introducing a new concept (embeddings, BM25, LangGraph state, etc.), explain it in depth
  first.
- Prefer clear, explicit code over clever abstractions.
- Commit after every working step with a clear conventional commit message (feat:, fix:, test:,
  docs:, chore:), and push.
- Measure before and after a change that can affect quality (retrieval eval, faithfulness eval).
  When a decision rule is agreed, record it before seeing the numbers.
- Rules that must hold are enforced in code, not only in the prompt: prompt-only rules ("at most
  two searches", answer language, bracket style) kept failing in testing.

## Environment

- Windows, PowerShell 5.1. Python 3.12, Node 24, Docker Desktop (WSL2 backend), 16 GB RAM.
- Give PowerShell commands, not bash, unless running inside a Docker container.
- PowerShell 5.1 mangles double quotes in arguments to native programs: write multi-line commit
  messages to a file and use `git commit -F <file>`.
- No NVIDIA GPU: keep ML workloads (embeddings) on CPU. Don't switch to GPU (ROCm) unprompted.
- The project lives outside OneDrive (long-path issues).
- If the Docker daemon isn't reachable: `docker desktop start`, wait for `docker desktop status`.
- Postgres (Docker) is on host port **15432**. 5432/5433 collide with native Postgres installs on
  this machine (a misleading "password authentication failed"), and ports in 49152-65535 can
  fall into Windows/Hyper-V dynamic exclusion ranges after a reboot. If a DB connection fails,
  rule out the network layer first: `Get-NetTCPConnection -LocalPort 15432 -State Listen`,
  `netsh interface ipv4 show excludedportrange protocol=tcp`, then `docker compose down` +
  `docker compose up -d db` (not just `restart`).
- npm 11.4.2 crashes adding some packages ("Cannot read properties of null (reading
  'edgesOut')"); `npx npm@11.20.0 install ...` works, and `npm ci` accepts the lockfile.

## Stack

- Backend: Python 3.12, FastAPI, Server-Sent Events.
- Agent: LangGraph (explicit `StateGraph`), LangChain tools.
- LLM: Groq `openai/gpt-oss-20b` (primary), Gemini (fallback), switched by `LLM_PROVIDER`.
  Free tiers have tight daily token limits: keep prompts lean, never loop on LLM calls without a
  cap. The evaluation and the live demo share the same Groq quota.
- Embeddings: `intfloat/multilingual-e5-small` (384 dims, 512 tokens), local CPU.
- Database: PostgreSQL 16 + pgvector (vectors), Postgres full-text search (keywords), normal
  tables for courses and prerequisites.
- Frontend: React + TypeScript (Vite), react-markdown (raw HTML disabled), vitest.
- Quality: pytest, ruff (pinned 0.16.9, same in CI), oxlint, a retrieval eval set and an answer
  faithfulness eval set.
- Infra: Docker Compose (db + api + frontend; Caddy in production), GitHub Actions CI.

## Architecture

1. Ingestion (`backend/app/ingestion/`): load public AUI documents (catalog PDF + scholarship
   pages, listed in `data/sources.md`) -> clean -> chunk (each chunk starts with a "Section:"
   line: level + nearest heading) -> embed -> store in `document_chunks` with metadata.
   Courses and prerequisites are extracted into their own tables.
2. Retrieval (`backend/app/retrieval/`): vector + keyword search fused by reciprocal rank
   fusion (k=60). Each search fuses several phrasings: the agent's query, its English version
   (`query_en`), and on the first turn the student's question; the university's name is
   stripped from each.
3. Agent (`backend/app/agent/`): tools `search_documents` and `query_courses` (recursive
   prerequisite chains); at most 3 tool rounds, then a forced answer (with retry and fallback).
4. Generation: answer only from retrieved passages, cite them as `[N]`, say "I don't know" when
   the passages don't cover it. Citation numbers are per passage, once per request.
5. API (`backend/app/main.py`): `/chat` (SSE: token, tool_call, citations, done, error),
   `/health`, `/sources/{source}`. Demo limits (daily cap, per-IP limit) in Postgres
   (`app/limits.py`).
6. Frontend (`frontend/`): streaming chat with citation chips and source cards, example questions
   replayed from saved answers (no API call), dark mode.
7. Evaluation (`backend/app/evaluation/`, `eval/`): retrieval eval (anchors, Hit@k, MRR) and the
   faithfulness pipeline (claim splitting, LLM judge with a verbatim quote check, hand labels,
   agreement). The judge rules are frozen for comparability between runs.

## Data rules

- Only public university documents. No personal student data.
- Secrets live in `.env` (gitignored); `.env.example` lists the variables.
- On the server, IP addresses are stored only as an HMAC (`IP_HASH_SECRET`), deleted after 2 days.

## How to run

Full setup from a fresh clone is in the README ("Running it"). Day to day:

```powershell
docker compose up -d db                        # repo root
cd backend; .\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000      # API
cd frontend; npm run dev                       # UI on http://localhost:5173

cd backend; pytest -q; ruff check .; ruff format --check .
cd frontend; npm run lint; npm test; npm run build
python -m app.evaluation.run_retrieval_eval    # in backend\, database seeded
```

Deployment (Azure VM, Docker Compose + Caddy): `deploy/DEPLOY.md`. Updates are a `git archive`
copy of HEAD to the VM, then `up -d --build`; SSH by the DNS name (that's the host key in
known_hosts).

## Current status (2026-10-23)

- All phases done and deployed. Repo is public, CI badge in the README. Faithfulness: run 3
  (after fixes A-C) 6/26 main answers with an unsupported cited claim vs. 17/47 at baseline
  (confidence intervals overlap); details in the README.
- Left: demo video; switch to the Namecheap domain (A record + `DOMAIN` in the server `.env`,
  then `up -d`).
- Open problems (README "Known limitations" / "Future work"): everyday wording missing passages
  written in the catalog's vocabulary (candidate: a multilingual reranker), citation placement
  (Fix D), the undergraduate/graduate level filter, a re-ingest of the newer catalog editions.

A full development and decision log exists locally as `SESSION_LOG.md` (gitignored, not in the
public repo). Read the relevant part when history matters (why a decision was made, past
measurements, evaluation details).
