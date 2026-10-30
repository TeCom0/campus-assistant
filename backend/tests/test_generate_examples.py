"""Tests for saving example answers (app.generate_examples): nothing reaches the
app's folder unless approved, and the review shows each cited passage's text.
No LLM calls."""

import json

import pytest

from app import generate_examples


def _write(folder, example_id: str) -> None:
    (folder / f"{example_id}.json").write_text(json.dumps({"id": example_id}), encoding="utf-8")


def test_approve_copies_only_the_approved_examples(tmp_path, monkeypatch):
    review, saved = tmp_path / "review", tmp_path / "saved"
    review.mkdir()
    _write(review, "a")
    _write(review, "b")
    monkeypatch.setattr(generate_examples, "SAVED_DIR", saved)

    generate_examples.approve(["a"], review)
    assert sorted(p.name for p in saved.iterdir()) == ["a.json"]


def test_approve_refuses_an_example_that_was_never_generated(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_examples, "SAVED_DIR", tmp_path / "saved")
    with pytest.raises(SystemExit):
        generate_examples.approve(["missing"], tmp_path)


def test_review_puts_each_cited_passage_next_to_the_answer():
    saved = {
        "id": "x",
        "question": "Q?",
        "tool_calls": [{"tool": "search_documents", "label": 'Searching documents for "q"'}],
        "answer": "Yes [1].",
        "citations": [
            {"marker": 1, "title": "Academic Catalog 2024–2025", "section": "Repeat Policy"}
        ],
    }
    cited = [
        {"marker": 1, "source": "academic_catalog_2024_2025", "pages": [120], "text": "PASSAGE"}
    ]
    review = generate_examples.review_section(saved, cited)

    assert "Yes [1]." in review
    assert "[1] Academic Catalog 2024–2025, p. 120 -- Repeat Policy" in review
    assert "PASSAGE" in review


def _rate_limit(message: str):
    import groq
    import httpx

    response = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))
    return groq.RateLimitError(message, response=response, body=None)


def test_a_per_minute_limit_is_waited_out_and_the_daily_limit_is_raised(monkeypatch):
    calls = []

    def answer(graph, example):
        calls.append(1)
        if len(calls) == 1:
            raise _rate_limit("Rate limit reached ... tokens per minute (TPM)")
        return {"id": "x"}, []

    monkeypatch.setattr(generate_examples, "answer_example", answer)
    monkeypatch.setattr(generate_examples.time, "sleep", lambda seconds: None)
    assert generate_examples.answer_with_retries(None, {"id": "x"}) == ({"id": "x"}, [])
    assert len(calls) == 2

    def daily(graph, example):
        raise _rate_limit("Rate limit reached ... tokens per day (TPD)")

    monkeypatch.setattr(generate_examples, "answer_example", daily)
    with pytest.raises(Exception, match="per day"):
        generate_examples.answer_with_retries(None, {"id": "x"})


class _StreamingGraph:
    """Streams one search and an answer the way the compiled graph does, with
    the tool recording its step as search_documents does. No LLM call."""

    def stream(self, *args, **kwargs):
        from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

        from app.agent.trace import record_tool_step

        call = {"id": "call_1", "name": "search_documents", "args": {"query": "transfer"}}
        usage = {"input_tokens": 900, "output_tokens": 50, "total_tokens": 950}
        yield (
            "updates",
            {"agent": {"messages": [AIMessage("", tool_calls=[call], usage_metadata=usage)]}},
        )
        record_tool_step("search_documents", {"results": []}, call_id="call_1")
        citation = {
            "marker": 1,
            "source": "academic_catalog_2024_2025",
            "pages": [118],
            "text": "PASSAGE",
        }
        tool_message = ToolMessage("[1] PASSAGE", tool_call_id="call_1", artifact=[citation])
        yield "updates", {"tools": {"messages": [tool_message]}}
        yield "messages", (AIMessageChunk("Up to 68 credits [1]."), {"langgraph_node": "agent"})
        answer = AIMessage("Up to 68 credits [1].", usage_metadata=usage)
        yield "updates", {"agent": {"messages": [answer]}}


def test_a_saved_example_carries_the_trace_of_its_own_run():
    example = {"id": "x", "question": "How many credits can I transfer?", "language": "en"}
    saved, _cited = generate_examples.answer_example(_StreamingGraph(), example)

    assert saved["answer"] == "Up to 68 credits [1]."
    assert [c["marker"] for c in saved["citations"]] == [1]
    trace = saved["trace"]
    assert trace["status"] == "done"
    assert [s["call_id"] for s in trace["steps"]] == ["call_1"]
    assert [s["kind"] for s in trace["timeline"]] == ["llm", "tools", "llm"]
    assert trace["totals"]["llm_calls"] == 2
    assert trace["totals"]["input_tokens"] == 1800
    assert trace["totals"]["first_token_ms"] is not None
    assert "model" in trace
