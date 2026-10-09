# Campus AI Assistant

A bilingual (English/French) assistant for Al Akhawayn University (AUI) students. It answers
questions about academic policies, the course catalog and scholarships, **cites the page each
answer comes from**, and uses an agent with tools to look up structured course data, e.g. *"What
are the prerequisites for ACC 2302?"* — including the full prerequisite chain.

Built to be piloted with real students through TeCom, AUI's student tech club.

**Status:** the chat app, agent, CI and Docker setup are done (Phases 0–6). Next: architecture
diagram, demo video and the student pilot deployment.

---

## What it does

- **Answers only from university documents**, with numbered citations (`[1]`) linked to footnotes
  showing the source and page. When the documents don't cover a question, it says so instead of
  guessing.
- **Agent with two tools**, chosen per question by the LLM:
  - `search_documents` — hybrid search (vector + keyword) over the catalog and scholarship pages.
  - `query_courses` — SQL over 660 courses and 526 prerequisite links extracted from the catalog,
    following prerequisite chains recursively.
- **Streams the answer** token by token, showing which tool is running ("Looking up course
  ACC 2302").
- **English and French**: answers in the question's language; follow-up questions keep the
  conversation's context.

## Architecture

```
React + TS UI  --POST /chat (SSE stream)-->  FastAPI
                                               |
                                     LangGraph agent (LLM: Groq / Gemini)
                                        |                        |
                              search_documents             query_courses
                                        |                        |
                     hybrid search: pgvector + Postgres     courses tables
                     full-text, merged with RRF             (recursive CTE)
                                        \                        /
                                         PostgreSQL + pgvector

Ingestion (offline): AUI PDF/HTML -> clean -> chunk -> embed (multilingual-e5-small, CPU)
                     -> document_chunks;  catalog text -> course extraction -> courses tables
```

## Tech stack

| Area | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Server-Sent Events |
| Agent | LangGraph (explicit `StateGraph`), LangChain tools |
| LLM | Groq `openai/gpt-oss-20b` (primary), Gemini `gemini-3.5-flash` (fallback), one config switch |
| Embeddings | `intfloat/multilingual-e5-small` via sentence-transformers, local CPU |
| Database | PostgreSQL 16 + pgvector; Postgres full-text search for keywords |
| Frontend | React 19 + TypeScript, Vite, react-markdown |
| Quality | pytest (50 tests), ruff, oxlint, retrieval evaluation set |
| Infra | Docker Compose (db + api + frontend), GitHub Actions CI |

## Design decisions worth knowing

- **Hybrid search with Reciprocal Rank Fusion.** Vector similarity and keyword `ts_rank` scores
  are on incompatible scales, so they're merged by *rank* (`1 / (60 + rank)`), not by score.
  Hybrid beat vector-only on the evaluation set with no regressions (numbers below).
- **Rules that must hold are enforced in code, not only in the prompt.** The model ignored "at
  most two searches" in testing, so the tool budget is enforced in the graph: after 3 tool rounds
  the model is called with no tools bound. Same for the answer language (detected in code and
  passed to the model) and citation brackets (normalized on the stream).
- **Citations are numbered per passage, once per request.** A passage returned by two searches
  keeps its first number, and only the sources the answer actually cites are sent to the UI.
- **Prerequisites are shown in the catalog's own wording, not parsed into AND/OR logic.** The
  catalog's wording is genuinely ambiguous (a comma means AND on some lines and OR on others), and
  a parser would turn that into confident wrong answers.
- **The server is stateless.** The browser sends the recent conversation with each question
  (last 10 messages, old citation markers stripped), so there is no session store.
- **The embedding model was chosen by measurement.** The first model's 128-token limit was
  silently truncating 99.8% of chunks; e5-small handles 512 tokens.

## Evaluation

Retrieval is measured on 12 hand-labelled questions (8 English, 4 French), each with the chunk
that answers it (`eval/retrieval_eval_set.json`):

| Method | Hit@3 | MRR |
|---|---|---|
| Keyword (Postgres full-text) | 16.7% | 0.167 |
| Vector (pgvector, cosine) | 58.3% | 0.558 |
| **Hybrid (RRF)** | **75.0%** | **0.646** |

Run it with `python -m app.evaluation.run_retrieval_eval` (in `backend/`, database seeded).

Not measured yet: whether each cited claim is actually supported by its cited passage. That's the
next evaluation to add (see Known limitations).

## Running it

### Prerequisites

Docker Desktop, Python 3.12, Node 24, and a free API key from
[Groq](https://console.groq.com) (and optionally [Google AI Studio](https://ai.google.dev) for the
Gemini fallback).

```powershell
copy .env.example .env    # then put your API key(s) in .env
```

### 1. Database and data (first time only)

The database starts empty. These steps download the public AUI documents, process them and fill
the database. The first run also downloads the embedding model (~470 MB).

```powershell
docker compose up -d db

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

python -m app.ingestion.load      # download the documents (list mirrors data/sources.md)
python -m app.ingestion.clean     # PDF/HTML -> text
python -m app.ingestion.chunk     # text -> chunks
python -m app.ingestion.store     # embed chunks -> document_chunks
python -m app.ingestion.courses   # catalog -> courses + prerequisites
```

### 2a. Run everything in Docker

```powershell
docker compose up -d --build
```

Open http://localhost:8080. The API is on http://localhost:8000 (`/health`, `/chat`).

### 2b. Or run for development (hot reload)

```powershell
# terminal 1, in backend\ with the venv active
uvicorn app.main:app --reload --port 8000

# terminal 2, in frontend\
npm install
npm run dev
```

Open http://localhost:5173. (Stop the `api` container first if it's running: both use port 8000.)

## Tests and CI

```powershell
cd backend
pytest -q          # 50 tests; the Postgres ones skip if the database isn't running
ruff check . ; ruff format --check .
```

Every push and pull request runs three GitHub Actions jobs (`.github/workflows/ci.yml`): ruff,
pytest against a real pgvector service container (seeded with the course data first, so the
database tests run instead of skipping), and the frontend lint + type-check + build. The agent
tests use a fake model, so CI makes no LLM calls.

## Project structure

```
backend/
  app/
    agent/        LangGraph graph, tools, citations, history, language detection
    retrieval/    vector, keyword and hybrid search
    ingestion/    load -> clean -> chunk -> store; course extraction
    evaluation/   retrieval evaluation runner
    db/           connection helper, schema.sql
    main.py       FastAPI app: /health, /chat (SSE)
  tests/
frontend/src/     App.tsx (chat UI), chatStream.ts (SSE client), types.ts
eval/             retrieval evaluation set
data/             sources.md (document URLs); raw/ and processed/ are generated
```

## Known limitations

- **Cited answers can still contain wrong details.** The model occasionally adds facts that its
  cited passage doesn't support. Measuring this (an answer-faithfulness evaluation) comes before
  fixing it.
- **French questions over English documents.** All sources are English; 2 of the 4 French
  evaluation questions aren't retrieved by any method. Translating the query before retrieval is
  the likely fix.
- **The agent sometimes pads its search queries** ("MTH 1305 Al Akhawayn University course
  description"), which can push the right passage down the ranking.
- **Free-tier LLM limits.** Groq's daily token limit caps usage; history is capped at 10 messages
  to keep requests small.
- **No authentication or rate limiting yet**, needed before a public pilot.

## Data

Only public AUI documents are used (listed with URLs in `data/sources.md`); no personal student
data is stored. The server doesn't save questions, but each question and the retrieved passages
are sent to the LLM provider (Groq, or Google for Gemini) to generate the answer.
