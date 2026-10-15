# Campus AI Assistant

A bilingual (English/French) assistant for Al Akhawayn University (AUI) students. It answers
questions about academic policies, the course catalog and scholarships, **cites the page each
answer comes from**, and uses an agent with tools to look up structured course data, e.g. *"What
are the prerequisites for ACC 2302?"* — including the full prerequisite chain.

An unofficial student project, not an official AUI service.

**Status:** the chat app, agent, CI and Docker setup are done (Phases 0–6), and a faithfulness
baseline is measured (see Evaluation). Next: fixes for the main faithfulness problems, a public
deployment for students, and a demo video.

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

**Answering a question.** The agent node decides which tools to call; after 3 tool rounds it
must answer with what it has (enforced in code). Events stream back to the browser as they
happen.

```mermaid
flowchart TD
    UI["React + TypeScript chat UI<br/>(browser)"]
    API["FastAPI<br/>POST /chat"]
    UI -- "question + recent history" --> API
    API -. "SSE stream: tool_call, token,<br/>citations, done / error" .-> UI

    subgraph AGENT["LangGraph agent"]
        AG["agent node<br/>LLM: Groq or Gemini"]
        TN["tools node"]
        AG -- "tool calls<br/>(max 3 rounds)" --> TN
        TN -- "results with<br/>citation numbers" --> AG
    end
    API --> AG

    TN --> SD["search_documents<br/>hybrid search"]
    TN --> QC["query_courses<br/>course lookup"]

    SD --> VS["vector search<br/>query embedded with e5-small"]
    SD --> KS["keyword search<br/>Postgres full-text"]
    VS --> RRF["merged by rank (RRF)"]
    KS --> RRF

    subgraph DB["PostgreSQL + pgvector"]
        DC[("document_chunks")]
        CT[("courses<br/>course_prerequisites")]
    end
    VS --> DC
    KS --> DC
    QC -- "recursive CTE<br/>for prerequisite chains" --> CT
```

**Getting the data in** (run once, offline):

```mermaid
flowchart LR
    SRC["AUI public documents<br/>catalog PDF + 2 scholarship pages"]
    SRC --> LOAD["load<br/>download"]
    LOAD --> CLEAN["clean<br/>PDF / HTML to text"]
    CLEAN --> CHUNK["chunk"]
    CHUNK --> EMBED["embed<br/>multilingual-e5-small, CPU"]
    EMBED --> DC[("document_chunks<br/>1161 chunks")]
    CLEAN --> EXTRACT["extract courses<br/>from catalog text"]
    EXTRACT --> CT[("courses + prerequisites<br/>660 courses, 526 links")]
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
| Quality | pytest (163 tests), ruff, oxlint, retrieval and answer-faithfulness evaluation sets |
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

### Answer faithfulness: are cited claims supported by their passages?

**Method.** 34 questions (17 topics, each asked in English and French: 26 `main`, 4 known past
failures, 4 unanswerable) are answered by the real agent. Each answer is split into claims in
code (`split_claims.py`), and each claim is checked against the passages its citation points to.
Refusals ("I couldn't find…") and short list lead-ins ("The main options are:") are excluded from
scoring, because they state nothing about the university. Whether an answer *should* have declined
is checked separately, per answer, as false refusals and missed refusals. An LLM judge from a
different model family than the generator labels each claim supported, unsupported or no_claim.
For "supported", the judge must quote its evidence, and code checks that the quote really is in
one of the claim's passages; if not, the claim counts as unsupported.

**Can the judge be trusted?** Its labels are compared with my own hand labels on a 40-claim
stratified sample of run 1, labelled blind before the judge ran.

- *Original gate:* calibration 9/9 on hand-made cases, at least 32/40 agreement, and at most 2
  "lenient" errors (judge says supported, human says unsupported: the dangerous direction).
  - Gemini Flash (free tier): unusable (503 errors, 20 requests/day).
  - Qwen 3.8 27B: 25/40.
  - Mistral Large 2512: 27/40 (68%, kappa 0.22), 3 lenient errors.
- *Why that gate was unreachable:* my own two labelling passes on the same claims agree on only
  31/40. A judge can't be required to agree with me more than I agree with myself. Several
  disagreements were definition problems (refusals, lead-in fragments, advice), not judge
  errors.
- *What changed.* All of it was recorded in the project notes before the judge was re-run.
  - Refusals and lead-ins are excluded, which leaves 36 sample claims. My self-agreement on
    those is 31/36.
  - I adjudicated the 13 disagreements. That adjudication saw the judge's labels, so it may lean
    toward the judge. Agreement with my **original** labels is always reported next to the
    adjudicated one, and any new disagreements get a **blind** adjudication: two unnamed labels,
    in random order.
  - The judge prompt now requires a verbatim quote, and an unquotable claim must be labelled
    unsupported. The quote check normalizes quote characters, whitespace and case, and accepts
    "a … b" quotes only if every part is in the same passage.
- *New gate,* on the judge's final labels (after the quote check):
  - calibration 9/9;
  - at least **31/36** agreement with the adjudicated labels, i.e. my own self-agreement;
  - at most **2 lenient errors**.

  Label agreement and quote validity are reported separately. The judge is re-run once under
  these rules, and the result is reported whatever it is.

**Result of the re-run: the judge did not pass.** Mistral Large 2512 under the rules above, on
the 36 scored sample claims:

| | vs. my original labels | vs. adjudicated labels |
|---|---|---|
| Label agreement (judge's own label) | 27/36 = 75% (95% CI 59–86%), κ −0.12 | 31/36 = 86% (71–94%), κ 0.48 |
| **Final agreement** (after the quote check: **gated**) | 21/36 = 58% (42–73%), κ −0.09 | **27/36 = 75% (59–86%)**, κ 0.39 |
| Lenient errors (final) | 4 | **2** |
| Strict errors (final) | 10 | 7 |

- **Gate:** calibration 9/9 ✓; at most 2 lenient errors ✓ (2); at least 31/36 final agreement ✗
  (27/36).
- **Quote validity:** 92/115 = 80% of the judge's "supported" quotes were found verbatim in the
  claim's passages, across all of run 1 (75% in the sample). Under the earlier, looser prompt it
  was 68%.
- **Where the gap comes from:** most remaining disagreements are strict errors, the judge saying
  "unsupported" where I say "supported". Five of the seven are quotes that fail the check:
  - quotes joining two passages;
  - the judge's own words inside a quote;
  - a 3-word quote under the 4-word minimum.

  So the faithfulness numbers below likely **overstate** the problem. The judge also misses some
  real problems: 2 lenient errors.
- **Blind adjudication:** the judge's 5 new disagreements were decided without knowing which
  label was whose: 3 kept my original label, 2 went to the judge.
- κ is near or below zero against the original labels even at 75% agreement. Almost every label
  is "supported", so kappa punishes any disagreement heavily. Raw agreement with its interval is
  the more useful number here.

As decided in advance, judge work ends here, so run 2 was not judged. The baseline below uses
this judge and must be read together with its 75% agreement.

**Faithfulness baseline (run 1, 34 answers, judged by Mistral Large 2512):**

| Group | Answers with ≥ 1 unsupported cited claim | Crashed |
|---|---|---|
| `main` (all) | 10/24 = 41.7% (95% CI 24.5–61.2%) | 2 |
| `main` English | 4/12 = 33.3% | 1 |
| `main` French | 6/12 = 50.0% | 1 |
| Known past failures | 3/4 | 0 |
| Unanswerable | 0/4 (none cite anything) | 0 |

- **False refusals:** 2/28. The assistant declined two answerable questions (scholarship
  conditions in French, and MTH 1305 in French).
- **Missed refusals:** the report counts 1/4 (`instructor_en`), but that's a judge error. The
  answer does decline ("I couldn't find any information…"), and my hand label says so. So the
  assistant declined all 4 unanswerable questions.
- **Excluded from scoring:** 12 of 156 claims (7 lead-ins, 5 refusals), all listed in the report.
- **Crashes:** 2 answers hit the known forced-answer error and have no claims.
- **Cost:** the judge runs on Mistral's pay-as-you-go API; judging all of run 1 cost about $0.06.

These numbers set the starting point for the fixes (headings in chunks, undergraduate/graduate
tagging, the forced-answer crash). The same pipeline will measure the result.

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

- **Cited answers can still contain wrong details.** In the baseline, 10 of 24 main answers
  (42%) had at least one cited claim the judge found unsupported. The judge itself agrees with
  hand labels on 75% of claims and tends to be too strict (see Evaluation).
- **French questions over English documents.** All sources are English; 2 of the 4 French
  evaluation questions aren't retrieved by any method. Translating the query before retrieval is
  the likely fix.
- **The agent sometimes pads its search queries** ("MTH 1305 Al Akhawayn University course
  description"), which can push the right passage down the ranking.
- **Free-tier LLM limits.** Groq's daily token limit caps usage; history is capped at 10 messages
  to keep requests small.
- **No authentication or rate limiting yet**, needed before a public deployment.

## Data

Only public AUI documents are used (listed with URLs in `data/sources.md`); no personal student
data is stored. The server doesn't save questions, but each question and the retrieved passages
are sent to the LLM provider (Groq, or Google for Gemini) to generate the answer.
