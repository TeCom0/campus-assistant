"""What the model is told, pinned byte for byte while A2.2 moves the text around.

The fixture was captured from the code deployed at c907a33. Same input to the model
means this refactor can't change its answers, so A2.2 needs no LLM calls. A deliberate
wording change (A2.7) replaces the fixture in the same commit, and re-measures.
"""

import json
from pathlib import Path

from langchain_core.utils.function_calling import convert_to_openai_tool

from app.agent.graph import MODEL_TOOLS, SYSTEM_PROMPT_TEMPLATE

FIXTURE = Path(__file__).parent / "fixtures" / "agent_text_c907a33.json"


def _pinned() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _tool_schemas() -> list[dict]:
    # search_documents is already a schema; query_courses is still a tool object.
    return [t if isinstance(t, dict) else convert_to_openai_tool(t) for t in MODEL_TOOLS]


def test_the_system_prompt_template_is_unchanged():
    assert SYSTEM_PROMPT_TEMPLATE == _pinned()["system_prompt_template"]


def test_the_tool_schemas_are_unchanged():
    assert _tool_schemas() == _pinned()["tools"]
