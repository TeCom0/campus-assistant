"""The gate measurement's own logic. No LLM calls: it must be right before it spends tokens."""

import json

import pytest

from app.agent.gate import NOT_FOUND_TEMPLATE, SCOPE_TEMPLATE
from app.evaluation import run_gate_check as check

QUESTION = {
    "id": "q",
    "set": "offtopic",
    "category": "off_topic",
    "expected": "template",
    "question": "What is 1 + 1?",
    "language": "en",
}


def _record(answer="", markers=(), cards=(), tools=(), gate=None, error=None, set_name="offtopic"):
    return {
        "id": "q",
        "set": set_name,
        "answer": answer,
        "cited_markers": list(markers),
        "cards": list(cards),
        "tool_calls": list(tools),
        "gate": gate,
        "error": error,
        "tokens": 10,
        "seconds": 0.1,
    }


def test_parse_events_reads_a_chat_response():
    body = 'event: token\ndata: {"text": "hi"}\n\nevent: done\ndata: {}\n\n'
    assert check.parse_events(body) == [("token", {"text": "hi"}), ("done", {})]


def test_a_record_holds_what_the_browser_received():
    events = [
        ("tool_call", {"tool": "search_documents", "label": "Searching the documents..."}),
        ("token", {"text": "68 credits [1]."}),
        ("citations", {"citations": [{"marker": 1}]}),
        ("trace", {"status": "done", "totals": {"input_tokens": 90, "output_tokens": 10}}),
        ("done", {}),
    ]
    record = check.record_from_events(QUESTION, events, 1.26)
    assert record["answer"] == "68 credits [1]."
    assert record["cited_markers"] == [1]
    assert record["cards"] == [1]
    assert record["tool_calls"] == ["search_documents"]
    assert record["progress_lines"] == ["Searching the documents..."]
    assert (record["gate"], record["status"], record["tokens"]) == (None, "done", 100)
    assert (record["seconds"], record["error"]) == (1.3, None)


def test_a_record_with_no_trace_still_builds():
    # The trace is display data: a run can end without one.
    record = check.record_from_events(QUESTION, [("error", {"message": "x"})], 0.1)
    assert record["error"] == {"message": "x"}
    assert record["tokens"] == 0


@pytest.mark.parametrize(
    "record",
    [
        _record(SCOPE_TEMPLATE["en"], gate="no_tool"),
        _record(NOT_FOUND_TEMPLATE["fr"], tools=["search_documents"], gate="no_citation"),
        _record("68 credits [1].", markers=[1], cards=[1], tools=["search_documents"]),
        _record("", error={"message": "x"}),
        _record(""),
    ],
    ids=["scope template", "not-found template", "cited", "error", "nothing sent"],
)
def test_these_dont_count_as_reaching_the_student_uncited(record):
    assert not check.reaches_student_uncited(record)


@pytest.mark.parametrize(
    "record",
    [
        _record("1 + 1 = 2."),
        _record("It's 2 [1].", markers=[1], cards=[1]),
        _record("68 credits.", tools=["search_documents"]),
        _record("68 [7].", markers=[7], cards=[], tools=["search_documents"]),
        _record("68 [1], 12 [7].", markers=[1, 7], cards=[1], tools=["search_documents"]),
    ],
    ids=["no tool", "no tool, fake marker", "no citation", "invented", "one invented"],
)
def test_these_count_even_if_the_gate_said_it_passed(record):
    # Reads what the browser received, not the gate's verdict.
    assert check.reaches_student_uncited(record)


def _all_records(replaced=0, leak=False) -> list[dict]:
    records = []
    for question in check.load_questions():
        answer = SCOPE_TEMPLATE["en"] if question["set"] == "offtopic" else "68 credits [1]."
        record = _record(answer, markers=[1], cards=[1], tools=["search_documents"])
        record.update(id=question["id"], set=question["set"])
        records.append(record)
    sample = [r for r in records if r["set"] == "sample"]
    for record in sample[:replaced]:
        record.update(
            answer=NOT_FOUND_TEMPLATE["en"], gate="no_citation", cited_markers=[], cards=[]
        )
    if leak:
        records[0].update(answer="1 + 1 = 2.", tool_calls=[], cited_markers=[], cards=[])
    return records


def test_the_rule_passes_at_one_replaced_of_twelve(capsys):
    assert check.print_summary(_all_records(replaced=1))
    assert "RULE PASSED" in capsys.readouterr().out


def test_the_rule_fails_at_two_replaced(capsys):
    assert not check.print_summary(_all_records(replaced=2))
    assert "RULE NOT PASSED" in capsys.readouterr().out


def test_the_rule_fails_on_any_leak():
    assert not check.print_summary(_all_records(leak=True))


def test_the_rule_fails_if_a_question_didnt_run():
    assert not check.print_summary(_all_records()[:-1])


def test_the_sample_is_the_one_in_the_recorded_rule():
    assert len(check.SAMPLE_IDS) == 12
    sample = [q for q in check.load_questions() if q["set"] == "sample"]
    assert [q["id"] for q in sample] == check.SAMPLE_IDS


def test_the_offtopic_set_holds_every_question_the_plan_names():
    questions = json.loads(check.OFFTOPIC_SET_PATH.read_text(encoding="utf-8"))
    asked = {q["question"] for q in questions}
    assert {
        "What is 1 + 1?",
        "What is the capital of France?",
        "What programs does AUI offer?",
        "What is AUI's add/drop policy?",
    } <= asked
    assert {q["category"] for q in questions} == {"off_topic", "aui", "injection"}
    assert len({q["id"] for q in questions}) == len(questions)


def test_a_stopped_run_resumes_and_skips_whats_done(tmp_path, monkeypatch):
    out = tmp_path / "out.jsonl"
    questions = check.load_questions()
    out.write_text(json.dumps({**_record(), "id": questions[0]["id"]}) + "\n", encoding="utf-8")
    asked = []

    def fake_ask(client, question):
        asked.append(question["id"])
        return {**_record(), "id": question["id"], "set": question["set"], "tokens": 1}

    monkeypatch.setattr(check, "ask", fake_ask)
    monkeypatch.setattr(check.main, "admit_question", check.main.admit_question)
    records = check.run(out)

    assert questions[0]["id"] not in asked
    assert len(records) == len(questions)


def test_the_run_stops_at_the_token_cap(tmp_path, monkeypatch, capsys):
    asked = []

    def fake_ask(client, question):
        asked.append(question["id"])
        return {**_record(), "id": question["id"], "set": question["set"], "tokens": 60_000}

    monkeypatch.setattr(check, "ask", fake_ask)
    monkeypatch.setattr(check.main, "admit_question", check.main.admit_question)
    check.run(tmp_path / "out.jsonl")

    assert len(asked) == 2  # 120k after the second, so no third
    assert "Stopped at the cap" in capsys.readouterr().out


def test_the_run_stops_at_groqs_daily_limit(tmp_path, monkeypatch, capsys):
    def fake_ask(client, question):
        raise check.DailyLimitReached

    monkeypatch.setattr(check, "ask", fake_ask)
    monkeypatch.setattr(check.main, "admit_question", check.main.admit_question)
    assert check.run(tmp_path / "out.jsonl") == []
    assert "daily limit" in capsys.readouterr().out


# --- Follow-ups -----------------------------------------------------------------------


def _saved_history(tmp_path):
    path = tmp_path / "saved.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for first_id in ("transfer_credits_en", "add_drop_en", "transfer_credits_fr"):
            record = {
                "id": first_id,
                "question": f"{first_id}?",
                "answer": f"answer [1] {first_id}",
            }
            f.write(json.dumps(record) + "\n")
    return path


def test_a_followup_carries_its_saved_question_and_answer(tmp_path):
    followups = {q["id"]: q for q in check.load_followups(_saved_history(tmp_path))}
    assert followups["followup_summer"]["history"] == [
        {"role": "user", "content": "add_drop_en?"},
        {"role": "assistant", "content": "answer [1] add_drop_en"},
    ]
    kinds = [q["kind"] for q in followups.values()]
    assert (kinds.count("substantive"), kinds.count("conversational")) == (3, 3)


def test_the_history_goes_to_chat():
    sent = {}

    class Response:
        text = "event: done\ndata: {}\n\n"

    class Client:
        def post(self, path, json):
            sent.update(json)
            return Response()

    question = {**QUESTION, "history": [{"role": "user", "content": "first"}]}
    check.ask(Client(), question)
    assert sent == {
        "question": "What is 1 + 1?",
        "messages": [{"role": "user", "content": "first"}],
    }


def _followup_records(questions, replaced=()):
    records = []
    for q in questions:
        record = _record("68 credits [1].", markers=[1], cards=[1], tools=["search_documents"])
        if q["id"] in replaced:
            record.update(answer=SCOPE_TEMPLATE["en"], gate="no_tool", cited_markers=[], cards=[])
        record["id"] = q["id"]
        records.append(record)
    return records


def test_a_template_on_a_conversational_followup_doesnt_fail_the_rule(tmp_path, capsys):
    questions = check.load_followups(_saved_history(tmp_path))
    records = _followup_records(questions, replaced={"followup_thanks", "followup_simpler"})
    assert check.print_followup_summary(records, questions)
    assert "known cost): 2/3" in capsys.readouterr().out


def test_a_template_on_a_substantive_followup_fails_the_rule(tmp_path, capsys):
    questions = check.load_followups(_saved_history(tmp_path))
    records = _followup_records(questions, replaced={"followup_summer"})
    assert not check.print_followup_summary(records, questions)
    assert "NOT PASSED" in capsys.readouterr().out


def test_a_followup_that_didnt_run_fails_the_rule(tmp_path):
    questions = check.load_followups(_saved_history(tmp_path))
    assert not check.print_followup_summary(_followup_records(questions)[:-1], questions)
