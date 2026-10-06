"""Centralized configuration values shared across ingestion and (later) retrieval."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load the repo-root .env (POSTGRES_* credentials, etc.) into the environment.
# No-op if the variables are already set some other way (e.g. in CI).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Multilingual (100 languages), retrieval-tuned embedding model. Requires
# "query: " / "passage: " prefixes on its inputs -- see app/embeddings.py.
# 512 token limit, chosen over paraphrase-multilingual-MiniLM-L12-v2 (128
# token limit) after discovering that limit was silently truncating ~99.8%
# of our real document chunks.
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIM = 384

POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_PORT = os.environ["POSTGRES_PORT"]
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# LLM provider, switchable through this one value ("groq" or "gemini") --
# see app/llm.py. Keys use .get() with an empty-string default, not
# os.environ[...], so importing this module doesn't fail before a key has
# been added; app/llm.py raises a clear error only when a provider is
# actually used without its key set.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# openai/gpt-oss-20b: Groq's recommended replacement for the now-deprecated
# (2026-08-16) llama-3.1-8b-instant.
GROQ_MODEL = "openai/gpt-oss-20b"
# gemini-3.5-flash: stable GA release (2026-05-19). Not gemini-2.5-flash,
# which is being retired 2026-10-20.
GEMINI_MODEL = "gemini-3.5-flash"

# Prior chat turns sent to the agent per request. Capped because free-tier
# token limits are tight and history grows every turn.
MAX_HISTORY_MESSAGES = 10

# Tool rounds (agent turns that call tools) allowed per question. Once used up,
# the agent must answer with what it has -- enforced in code (app/agent/graph.py),
# since the prompt's "at most two searches" rule alone was ignored in testing.
MAX_TOOL_ROUNDS = 3

# Hard cap on agent steps per request (each agent or tool-node run counts as one).
# A backstop only: MAX_TOOL_ROUNDS keeps a normal run at most 3 * 2 + 1 = 7 steps.
# Hitting this raises GraphRecursionError, which ends the answer with an error.
MAX_AGENT_STEPS = 10

# Browser origins allowed to call the API (the Vite dev server). Browsers block
# cross-origin requests unless the server opts in with CORS headers.
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
