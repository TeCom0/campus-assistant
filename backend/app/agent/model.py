"""LangChain chat model construction for the LangGraph agent.

Mirrors app.llm's provider switch (same LLM_PROVIDER/model/API-key config
values), but returns a LangChain BaseChatModel -- LangGraph's tool-calling
needs that interface, which app.llm's plain complete()/stream() don't
provide.
"""

from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_PROVIDER,
)


@lru_cache(maxsize=1)
def get_agent_model():
    if LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set (check .env)")
        return ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY)
    if LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set (check .env)")
        return ChatGoogleGenerativeAI(model=GEMINI_MODEL, api_key=GEMINI_API_KEY)
    raise ValueError(f"Unknown LLM_PROVIDER {LLM_PROVIDER!r}")
