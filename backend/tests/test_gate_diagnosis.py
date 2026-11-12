"""The gate diagnosis's own logic. No LLM calls: it must read the attempts right before it
spends tokens on them."""

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.gate import NOT_FOUND_TEMPLATE
from app.evaluation import run_gate_diagnosis as diagnosis

USAGE = {"input_tokens": 90, "output_tokens": 10, "total_tokens": 100}


def _searched() -> list:
    call = {"id": "c1", "name": "search_documents", "args": {"query": "credits"}}
    return [
        HumanMessage("How many credits can I transfer?"),
        AIMessage("", tool_calls=[call], usage_metadata=USAGE),
        ToolMessage("[1] a [2] b", tool_call_id="c1", artifact=[{"marker": 1}, {"marker": 2}]),
    ]


def _template(reason: str) -> AIMessage:
    return AIMessage(NOT_FOUND_TEMPLATE["en"], response_metadata={"gate": reason})


def test_an_answer_that_passed_has_one_attempt():
    messages = [*_searched(), AIMessage("68 credits [1].", usage_metadata=USAGE)]
    a = diagnosis.attempts(messages)
    assert a["queries"] == [{"query": "credits"}]
    assert a["known_markers"] == [1, 2]
    assert (a["first_answer"], a["first_verdict"], a["first_cited"]) == (
        "68 credits [1].",
        None,
        [1],
    )
    assert not a["retried"] and a["retry_answer"] is None and a["retry_cited"] is None
    assert a["final_answer"] == "68 credits [1]."
    assert a["tokens"] == 200


def test_a_retry_that_passed_keeps_the_rejected_first_answer():
    messages = [
        *_searched(),
        AIMessage("68 credits.", usage_metadata=USAGE),
        _template("no_citation"),
        AIMessage("68 credits [2].", usage_metadata=USAGE, response_metadata={"retry": True}),
    ]
    a = diagnosis.attempts(messages)
    assert (a["first_answer"], a["first_verdict"], a["first_cited"]) == (
        "68 credits.",
        "no_citation",
        [],
    )
    assert a["retried"]
    assert (a["retry_answer"], a["retry_verdict"], a["retry_cited"]) == (
        "68 credits [2].",
        None,
        [2],
    )
    assert a["final_answer"] == "68 credits [2]."
    assert a["tokens"] == 300


def test_an_invented_number_is_named():
    messages = [
        *_searched(),
        AIMessage("68 credits.", usage_metadata=USAGE),
        _template("no_citation"),
        AIMessage("68 [1] or 70 [9].", usage_metadata=USAGE, response_metadata={"retry": True}),
        _template("invented_marker"),
    ]
    a = diagnosis.attempts(messages)
    assert a["retry_verdict"] == "invented_marker"
    assert (a["retry_cited"], a["retry_invented"]) == ([1, 9], [9])
    assert a["final_answer"] == NOT_FOUND_TEMPLATE["en"]


def test_a_first_answer_with_an_invented_number_isnt_retried():
    messages = [
        *_searched(),
        AIMessage("70 [5].", usage_metadata=USAGE),
        _template("invented_marker"),
    ]
    a = diagnosis.attempts(messages)
    assert (a["first_verdict"], a["first_invented"], a["retried"]) == (
        "invented_marker",
        [5],
        False,
    )


class _FakeGraph:
    def __init__(self) -> None:
        self.runs = 0

    def invoke(self, state, config):
        self.runs += 1
        return {"messages": [*_searched(), AIMessage("68 [1].", usage_metadata=USAGE)]}


def test_the_run_stops_at_the_cap_and_saves_each_record(tmp_path, capsys):
    out = tmp_path / "out.jsonl"
    graph = _FakeGraph()
    question = {"id": "q", "question": "How many credits can I transfer?"}
    records = diagnosis.run(graph, [question], repeat=5, out_path=out, cap=350)

    assert graph.runs == 2  # 400 tokens after the second, checked before each run
    assert [r["n"] for r in records] == [1, 2]
    assert [json.loads(line)["n"] for line in out.read_text(encoding="utf-8").splitlines()] == [
        1,
        2,
    ]
    assert "Stopped at the cap" in capsys.readouterr().out
