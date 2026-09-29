"""LLM completion, provider-switchable via app.config.LLM_PROVIDER.

Free-tier providers have tight daily token limits (see CLAUDE.md), so
callers should keep prompts lean and never loop on this without a cap.
"""

from google import genai
from google.genai import types as genai_types
from groq import Groq

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_PROVIDER,
)


def _complete_groq(prompt: str, system: str | None) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set (check .env)")
    client = Groq(api_key=GROQ_API_KEY)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(model=GROQ_MODEL, messages=messages)
    return response.choices[0].message.content


def _complete_gemini(prompt: str, system: str | None) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set (check .env)")
    client = genai.Client(api_key=GEMINI_API_KEY)
    config = genai_types.GenerateContentConfig(system_instruction=system) if system else None
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=config)
    return response.text


_PROVIDERS = {"groq": _complete_groq, "gemini": _complete_gemini}


def complete(prompt: str, system: str | None = None) -> str:
    """Send a prompt (and optional system instructions) to the configured LLM provider."""
    if LLM_PROVIDER not in _PROVIDERS:
        raise ValueError(
            f"Unknown LLM_PROVIDER {LLM_PROVIDER!r}; expected one of {list(_PROVIDERS)}"
        )
    return _PROVIDERS[LLM_PROVIDER](prompt, system)


if __name__ == "__main__":
    print(complete("Say hello in exactly one word."))
