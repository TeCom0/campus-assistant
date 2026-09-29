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
