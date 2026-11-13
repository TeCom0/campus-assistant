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


def test_a_record_counts_the_retry_and_its_tokens():
    timeline = [
        {"kind": "llm", "input_tokens": 90, "output_tokens": 10},
        {"kind": "tools"},
        {"kind": "llm", "input_tokens": 300, "output_tokens": 50},
        {"kind": "llm", "input_tokens": 280, "output_tokens": 40, "retry": True},
    ]
    trace = {
        "status": "done",
        "retry": "no_citation",
        "timeline": timeline,
        "totals": {"input_tokens": 670, "output_tokens": 100},
    }
    record = check.record_from_events(QUESTION, [("trace", trace)], 1.0)
    assert record["retried"] is True
    assert record["gate"] is None  # the retry passed
    assert (record["tokens"], record["retry_tokens"]) == (770, 320)


def test_a_record_without_a_retry_says_so():
    trace = {"status": "done", "timeline": [{"kind": "llm", "input_tokens": 9, "output_tokens": 1}]}
    record = check.record_from_events(QUESTION, [("trace", trace)], 1.0)
    assert (record["retried"], record["retry_tokens"]) == (False, 0)


def test_the_summary_lists_each_retry_and_how_it_ended(capsys):
    records = [
        {**_record(), "id": "a", "retried": True, "retry_tokens": 300},
        {**_record(gate="no_citation"), "id": "b", "retried": True, "retry_tokens": 200},
        {**_record(), "id": "c", "retried": False, "retry_tokens": 0},
    ]
    check.print_retries(records)
    out = capsys.readouterr().out
    assert "retried: 2/3 ['a: passed', 'b: no_citation']" in out
    assert "retry tokens: 500" in out


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


def test_a_lower_cap_stops_the_run_sooner(tmp_path, monkeypatch, capsys):
    asked = []

    def fake_ask(client, question):
        asked.append(question["id"])
        return {**_record(), "id": question["id"], "set": question["set"], "tokens": 4_000}

    monkeypatch.setattr(check, "ask", fake_ask)
    monkeypatch.setattr(check.main, "admit_question", check.main.admit_question)
    check.run(tmp_path / "out.jsonl", check.sample_questions(), cap=10_000)

    assert len(asked) == 3  # 12k after the third: the cap is checked before each question
    assert "Stopped at the cap" in capsys.readouterr().out


def test_sample_only_is_the_twelve_questions_of_the_recorded_rule():
    assert [q["id"] for q in check.sample_questions()] == check.SAMPLE_IDS


def test_substantive_only_keeps_the_three_that_need_a_search(tmp_path):
    history = tmp_path / "history.jsonl"
    saved = [
        {"id": q["first_id"], "question": "q", "answer": "a"}
        for q in json.loads(check.FOLLOWUP_SET_PATH.read_text(encoding="utf-8"))
    ]
    history.write_text("\n".join(json.dumps(r) for r in saved), encoding="utf-8")
    kept = check.substantive_followups(check.load_followups(history))
    assert [q["id"] for q in kept] == ["followup_graduate", "followup_summer", "followup_fr"]


def test_a_sample_only_summary_doesnt_count_the_offtopic_set_as_missing(capsys):
    questions = check.sample_questions()
    records = [{**_record(set_name="sample"), "id": q["id"]} for q in questions]
    assert check.print_summary(records, questions)
    assert "missing: []" in capsys.readouterr().out


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


# --- Rounds (step 3 of the retry rule: each question twice) ----------------------------


def test_rounds_ask_the_whole_first_round_before_the_second():
    questions = check.with_rounds(check.sample_questions(), 2)
    assert len(questions) == 24
    assert [q["round"] for q in questions] == [1] * 12 + [2] * 12
    assert [q["id"] for q in questions[12:]] == check.SAMPLE_IDS


def test_a_record_says_which_round_it_belongs_to():
    record = check.record_from_events({**QUESTION, "round": 2}, [], 0.1)
    assert record["round"] == 2
    assert check.record_from_events(QUESTION, [], 0.1)["round"] == 1


def test_a_record_saved_before_rounds_is_round_one():
    assert check.key({"id": "q"}) == ("q", 1)


def test_a_resumed_two_round_run_asks_only_whats_missing(tmp_path, monkeypatch):
    out = tmp_path / "out.jsonl"
    questions = check.with_rounds(check.sample_questions(), 2)
    done = [{**_record(set_name="sample"), "id": q["id"], "round": 1} for q in questions[:12]]
    out.write_text("\n".join(json.dumps(r) for r in done) + "\n", encoding="utf-8")
    asked = []

    def fake_ask(client, question):
        asked.append((question["id"], question["round"]))
        return {**_record(set_name="sample"), "id": question["id"], "round": question["round"]}

    monkeypatch.setattr(check, "ask", fake_ask)
    monkeypatch.setattr(check.main, "admit_question", check.main.admit_question)
    records = check.run(out, questions)

    assert asked == [(i, 2) for i in check.SAMPLE_IDS]  # the same ids, not skipped
    assert len(records) == 24


def _sample_records(rounds, replaced):
    questions = check.with_rounds(check.sample_questions(), rounds)
    records = []
    for q in questions:
        record = _record("68 [1].", markers=[1], cards=[1], tools=["search_documents"])
        record.update(id=q["id"], round=q["round"], set="sample")
        records.append(record)
    for record in records[:replaced]:
        record.update(answer=NOT_FOUND_TEMPLATE["en"], gate="no_citation", cited_markers=[])
    return questions, records


def test_two_rounds_pass_at_two_replaced_of_twenty_four(capsys):
    assert check.print_summary(*reversed(_sample_records(2, replaced=2)))
    out = capsys.readouterr().out
    assert "2/24" in out and "(limit 2)" in out


def test_two_rounds_fail_at_three_replaced(capsys):
    assert not check.print_summary(*reversed(_sample_records(2, replaced=3)))
    assert "(limit 2)" in capsys.readouterr().out


def test_two_rounds_fail_if_the_second_round_didnt_run():
    questions, records = _sample_records(2, replaced=0)
    assert not check.print_summary(records[:12], questions)


def test_a_substantive_template_in_the_second_round_fails_the_followups(tmp_path):
    questions = check.with_rounds(
        check.substantive_followups(check.load_followups(_saved_history(tmp_path))), 2
    )
    records = _followup_records(questions)
    for record, q in zip(records, questions):
        record["round"] = q["round"]
    assert check.print_followup_summary(records, questions)
    records[-1].update(answer=SCOPE_TEMPLATE["en"], gate="no_tool", cited_markers=[], cards=[])
    assert not check.print_followup_summary(records, questions)
