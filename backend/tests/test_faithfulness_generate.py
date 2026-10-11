"""Tests for the helpers that turn an agent run into a faithfulness record
(app.evaluation.generate_faithfulness_answers). Built from hand-made LangChain
messages: no LLM or database calls.
"""

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.evaluation.generate_faithfulness_answers import (
    answer_text,
    collect_passages,
    load_done_ids,
    token_usage,
    tool_calls,
)


def _usage(total: int) -> dict:
    return {"input_tokens": total - 10, "output_tokens": 10, "total_tokens": total}


def _tool_result(*citations: dict) -> ToolMessage:
    return ToolMessage(content="...", tool_call_id="call", artifact=list(citations))


def _citation(marker: int, text: str) -> dict:
    return {"marker": marker, "source": "catalog", "pages": [1], "text": text}


def _run() -> list:
    return [
        HumanMessage("What do I need before ACC 2302?"),
        AIMessage(
            "",
            tool_calls=[{"name": "query_courses", "args": {"code": "ACC 2302"}, "id": "call"}],
            usage_metadata=_usage(1000),
        ),
        _tool_result(_citation(1, "ACC 2302 entry")),
        AIMessage(
            "",
            tool_calls=[
                {
                    "name": "query_courses",
                    "args": {"code": "ACC 2302", "follow_prerequisites": True},
                    "id": "call",
                }
            ],
            usage_metadata=_usage(1500),
        ),
        _tool_result(_citation(1, "ACC 2302 entry + chain")),
        AIMessage("You need ACC 2301 【1】.", usage_metadata=_usage(2000)),
    ]


def test_answer_is_the_agent_text_with_brackets_normalized():
    assert answer_text(_run()) == "You need ACC 2301 [1]."


def test_repeated_marker_keeps_every_distinct_text_in_order():
    messages = [*_run(), _tool_result(_citation(1, "ACC 2302 entry"))]  # exact repeat
    passages = collect_passages(messages)
    assert len(passages) == 1
    assert passages[0]["marker"] == 1
    assert passages[0]["texts"] == ["ACC 2302 entry", "ACC 2302 entry + chain"]


def test_passages_are_sorted_by_marker():
    messages = [_tool_result(_citation(3, "c"), _citation(1, "a")), _tool_result(_citation(2, "b"))]
    assert [p["marker"] for p in collect_passages(messages)] == [1, 2, 3]


def test_tool_calls_and_token_usage_cover_every_llm_call():
    messages = _run()
    assert [tc["args"] for tc in tool_calls(messages)] == [
        {"code": "ACC 2302"},
        {"code": "ACC 2302", "follow_prerequisites": True},
    ]
    assert token_usage(messages) == {
        "llm_calls": 3,
        "input_tokens": 4470,
        "output_tokens": 30,
        "total_tokens": 4500,
    }


def test_failed_run_has_empty_answer_and_no_passages():
    assert answer_text([]) == ""
    assert collect_passages([]) == []
    assert token_usage([])["llm_calls"] == 0


def test_done_ids_are_read_from_existing_jsonl(tmp_path):
    path = tmp_path / "answers_run1.jsonl"
    assert load_done_ids(path) == set()
    path.write_text(
        json.dumps({"id": "a"}) + "\n" + json.dumps({"id": "b"}) + "\n\n", encoding="utf-8"
    )
    assert load_done_ids(path) == {"a", "b"}
