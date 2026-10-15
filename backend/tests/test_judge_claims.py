"""Tests for the faithfulness judge's deterministic parts
(app.evaluation.judge_claims): prompt building, the quote check, merging the
judge's verdicts into per-claim results, and batching. No LLM calls (the
batch test replaces call_judge with a fake, the Groq tests use a fake client).
"""

import re
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.evaluation import judge_claims
from app.evaluation.judge_claims import (
    AnswerAbstains,
    BatchVerdict,
    ClaimVerdict,
    build_prompt,
    judge_batch,
    merge_verdicts,
    quote_found,
)
from app.evaluation.throttle import Throttle

PASSAGE_TEXT = (
    "Instructors should be informed before the absence to agree with the student on a suitable "
    "time\nand manner for makeup, should it be necessary. A maximum of three of these absences "
    "per\nsemester may be authorized."
)
PASSAGES = [
    {"marker": 1, "source": "catalog", "pages": [101], "texts": [PASSAGE_TEXT]},
    {"marker": 2, "source": "catalog", "pages": [120], "texts": ["Repeated courses count once."]},
]


def _claim(n: int, markers: list[int], kind: str = "own", auto_label=None) -> dict:
    return {
        "claim_id": f"q#{n}",
        "text": f"claim {n}",
        "kind": kind,
        "markers": markers,
        "auto_label": auto_label,
    }


def _verdict(n: int, label: str, quote: str = "") -> ClaimVerdict:
    return ClaimVerdict(claim_id=f"q#{n}", label=label, evidence_quote=quote, reason="r")


def _item(answer_id: str, claims: list[dict], passages=PASSAGES) -> dict:
    return {"id": answer_id, "question": "Q?", "answer": "A [1].", "passages": passages,
            "claims": claims}  # fmt: skip


def test_prompt_lists_each_claims_scope_and_every_text_of_a_repeated_marker():
    passages = [{"marker": 1, "source": "catalog", "pages": [222], "texts": ["entry", "entry+"]}]
    prompt = build_prompt([_item("q", [_claim(1, [1]), _claim(2, [], "uncited")], passages)])
    assert "- id: q#1 | check against: [1] | claim: claim 1" in prompt
    assert "- id: q#2 | check against: all passages | claim: claim 2" in prompt
    assert "entry\n--- (same marker, returned again with more text) ---\nentry+" in prompt


def test_batch_prompt_keeps_each_answers_passages_in_its_own_block():
    prompt = build_prompt([_item("a", [_claim(1, [1])]), _item("b", [_claim(2, [1])])])
    block_a, block_b = prompt.split("========== ANSWER b ==========")
    assert "ANSWER a" in block_a and "PASSAGES (of answer a only):" in block_a
    assert "PASSAGES (of answer b only):" in block_b and "q#2" in block_b and "q#2" not in block_a


def test_quote_found_ignores_line_breaks_case_and_typographic_quotes():
    texts = [PASSAGE_TEXT]
    assert quote_found("a maximum of three of these absences per semester", texts)
    assert quote_found("A maximum of three ... may be authorized.", texts)
    assert quote_found(
        "Instructors should be informed before the absence",
        ["Instructors should be informed before the absence"],
    )
    assert quote_found("the student’s record", ["the student's record"])


def test_quote_found_rejects_invented_or_out_of_order_text():
    texts = [PASSAGE_TEXT]
    assert not quote_found("A maximum of five of these absences", texts)
    assert not quote_found("may be authorized ... Instructors should", texts)
    assert not quote_found("", texts)


def test_supported_with_a_verifiable_quote_stays_supported():
    claims = [_claim(1, [1])]
    verdict = [_verdict(1, "supported", "A maximum of three of these absences")]
    assert merge_verdicts(claims, PASSAGES, verdict)[0]["label"] == "supported"


def test_quote_from_a_passage_the_claim_did_not_cite_makes_it_unsupported():
    # Cites [2], but the judge's evidence is in [1].
    claims = [_claim(1, [2])]
    verdict = [_verdict(1, "supported", "A maximum of three of these absences")]
    result = merge_verdicts(claims, PASSAGES, verdict)[0]
    assert (result["judge_label"], result["label"], result["flag"]) == (
        "supported",
        "unsupported",
        "quote_not_found",
    )


def test_uncited_claims_are_checked_against_all_passages():
    claims = [_claim(1, [], "uncited")]
    verdict = [_verdict(1, "supported", "count once")]
    assert merge_verdicts(claims, PASSAGES, verdict)[0]["label"] == "supported"


def test_auto_labelled_missing_and_duplicate_verdicts():
    claims = [_claim(1, [9], auto_label="unsupported"), _claim(2, [1]), _claim(3, [1])]
    verdict = [_verdict(2, "no_claim"), _verdict(2, "supported", "x"), _verdict(7, "no_claim")]
    results = merge_verdicts(claims, PASSAGES, verdict)
    assert [(r["label"], r["flag"]) for r in results] == [
        ("unsupported", "invalid_citation"),
        ("no_claim", None),  # the first verdict for q#2 counts
        (None, "no_verdict"),  # the judge skipped q#3 (and q#7 isn't a claim)
    ]


def test_judge_batch_maps_verdicts_back_to_their_answers(monkeypatch):
    sent = []

    def fake_call_judge(client, prompt, answer_ids):
        sent.append(prompt)
        verdict = BatchVerdict(
            answers=[AnswerAbstains(answer_id="a", abstains=True)],  # "b" left out
            verdicts=[_verdict(1, "no_claim"), _verdict(2, "supported", "count once")],
        )
        return verdict, 123

    monkeypatch.setattr(judge_claims, "call_judge", fake_call_judge)
    monkeypatch.setattr(judge_claims, "CLAIMS_PER_CALL", None)  # Gemini: all in one call
    answers = [
        _item("a", [_claim(1, [1])]),
        _item("b", [_claim(2, [2])]),
        _item("auto_only", [_claim(3, [9], auto_label="unsupported")]),
    ]
    judged, tokens = judge_batch(None, answers)
    assert (len(sent), tokens) == (1, 123)  # one call for the whole batch
    # Nothing to judge in "auto_only", but it's still sent: its abstains is needed.
    assert "ANSWER auto_only" in sent[0] and "claim 3" not in sent[0]
    assert judged["a"][0] is True and judged["a"][1][0]["label"] == "no_claim"
    assert judged["b"][0] is None  # the judge gave no abstains for "b"
    assert judged["b"][1][0]["label"] == "supported"
    assert judged["auto_only"][1][0]["flag"] == "invalid_citation"


class _FakeGroq:
    """Stands in for groq.Groq: returns one canned reply, records the request."""

    def __init__(self, content: str):
        self.requests = []
        reply = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(total_tokens=321),
        )

        def create(**kwargs):
            self.requests.append(kwargs)
            return reply

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


def test_groq_reply_is_validated_against_the_verdict_schema():
    reply = (
        '{"verdicts": [{"claim_id": "q#1", "label": "supported", "evidence_quote": "three", '
        '"reason": "ok"}], "abstains": true}'
    )
    client = _FakeGroq(reply)
    verdict, tokens = judge_claims._call_groq(client, "the prompt", "a")
    assert (verdict.verdicts[0].label, tokens) == ("supported", 321)
    # Returned in the same shape as Gemini's batched verdict, under the answer's id.
    assert verdict.answers == [AnswerAbstains(answer_id="a", abstains=True)]
    sent = client.requests[0]
    json_schema = sent["response_format"]["json_schema"]
    assert json_schema["strict"] is True
    assert json_schema["schema"]["additionalProperties"] is False
    assert sent["max_completion_tokens"] == judge_claims.GROQ_MAX_OUTPUT_TOKENS
    assert sent["messages"][1]["content"] == "the prompt"


def test_groq_reply_outside_the_schema_raises_instead_of_being_misread():
    reply = '{"verdicts": [{"claim_id": "q#1", "label": "mostly supported"}], "abstains": false}'
    with pytest.raises(ValidationError):
        judge_claims._call_groq(_FakeGroq(reply), "the prompt", "a")


def test_long_answers_are_judged_in_claim_groups_and_merged(monkeypatch):
    sent = []

    def fake_call_judge(client, prompt, answer_ids):
        ids = re.findall(r"id: (q#\d+)", prompt)
        sent.append(ids)
        verdicts = [_verdict(int(i.split("#")[1]), "no_claim") for i in ids]
        # Each group sees the whole answer; only the first group's abstains counts.
        abstains = [AnswerAbstains(answer_id="a", abstains=len(sent) == 1)]
        return BatchVerdict(answers=abstains, verdicts=verdicts), 10

    monkeypatch.setattr(judge_claims, "call_judge", fake_call_judge)
    monkeypatch.setattr(judge_claims, "CLAIMS_PER_CALL", 6)
    claims = [_claim(n, [1]) for n in range(1, 15)]  # 14 claims -> groups of 6, 6, 2
    judged, tokens = judge_batch(None, [_item("a", claims)])
    assert [len(ids) for ids in sent] == [6, 6, 2]
    assert tokens == 30
    abstains, results = judged["a"]
    assert abstains is True
    assert [r["label"] for r in results] == ["no_claim"] * 14  # every claim got its verdict


def test_strict_schema_forbids_extra_fields_on_every_object():
    schema = judge_claims.strict_json_schema(BatchVerdict.model_json_schema())
    objects = [schema] + list(schema["$defs"].values())
    assert {o["title"]: o["additionalProperties"] for o in objects} == {
        "BatchVerdict": False,
        "AnswerAbstains": False,
        "ClaimVerdict": False,
    }


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self.body = body

    def json(self) -> dict:
        return self.body

    @property
    def text(self) -> str:
        return "error body"


def _mistral_body(content: str, finish_reason: str = "stop") -> dict:
    return {
        "model": "mistral-large-2512",
        "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200},
    }


def _mistral_client(responses: list) -> tuple:
    """A MistralClient whose HTTP session returns the given responses in order;
    no real waiting (the throttle and the retries sleep on a fake clock)."""
    sleeps = []
    clock = [0.0]  # throttle waits move this fake clock forward

    def advance(seconds: float) -> None:
        clock[0] += seconds

    throttle = Throttle(1, 250_000, clock=lambda: clock[0], sleep=advance)
    client = judge_claims.MistralClient("key", throttle, sleep=sleeps.append)
    requests_sent = []

    def post(url, json, timeout):
        requests_sent.append(json)
        return responses.pop(0)

    client.session = SimpleNamespace(post=post)
    return client, requests_sent, sleeps


VALID_REPLY = (
    '{"verdicts": [{"claim_id": "q#1", "label": "supported", "evidence_quote": "three", '
    '"reason": "ok"}], "abstains": false}'
)


def test_mistral_reply_is_validated_and_tokens_are_counted():
    client, sent, _ = _mistral_client([_FakeResponse(200, _mistral_body(VALID_REPLY))])
    verdict, tokens = judge_claims._call_mistral(client, "the prompt", "a")
    assert (verdict.verdicts[0].label, tokens) == ("supported", 1200)
    assert verdict.answers == [AnswerAbstains(answer_id="a", abstains=False)]
    request = sent[0]
    assert request["model"] == judge_claims.MISTRAL_MODEL
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["max_tokens"] == judge_claims.MISTRAL_MAX_OUTPUT_TOKENS
    assert (client.input_tokens, client.output_tokens) == (1000, 200)
    # 1000 in at $0.50/M + 200 out at $1.50/M = $0.0008
    assert "$0.0008" in client.cost_summary()


def test_mistral_retries_a_429_then_succeeds():
    responses = [_FakeResponse(429), _FakeResponse(200, _mistral_body(VALID_REPLY))]
    client, sent, sleeps = _mistral_client(responses)
    judge_claims._call_mistral(client, "the prompt", "a")
    assert (len(sent), sleeps) == (2, [15])


def test_mistral_stops_after_the_retries():
    client, sent, sleeps = _mistral_client([_FakeResponse(503) for _ in range(4)])
    with pytest.raises(judge_claims.MistralUnavailable):
        judge_claims._call_mistral(client, "the prompt", "a")
    assert (len(sent), sleeps) == (4, [15, 30, 60])  # bounded: 1 try + 3 retries


def test_mistral_reply_cut_off_by_max_tokens_raises():
    body = _mistral_body('{"verdicts": [', finish_reason="length")
    client, _, _ = _mistral_client([_FakeResponse(200, body)])
    with pytest.raises(ValueError, match="max_tokens"):
        judge_claims._call_mistral(client, "the prompt", "a")


def test_mistral_client_errors_are_not_retried_and_show_the_message():
    client, sent, sleeps = _mistral_client([_FakeResponse(400)])
    with pytest.raises(RuntimeError, match="HTTP 400: error body"):
        judge_claims._call_mistral(client, "the prompt", "a")
    assert (len(sent), sleeps) == (1, [])


def test_excluded_claims_are_not_judged_but_their_answer_still_gets_a_decline_verdict(
    monkeypatch,
):
    sent = []

    def fake_call_judge(client, prompt, answer_ids):
        sent.append(prompt)
        return BatchVerdict(answers=[AnswerAbstains(answer_id="r", abstains=True)], verdicts=[]), 9

    monkeypatch.setattr(judge_claims, "call_judge", fake_call_judge)
    monkeypatch.setattr(judge_claims, "CLAIMS_PER_CALL", 6)  # Groq-style groups
    refusal = {**_claim(1, []), "exclude": "refusal"}
    judged, _ = judge_batch(None, [_item("r", [refusal])])
    assert len(sent) == 1  # one decline-only call, despite having no claim to judge
    assert "claim 1" not in sent[0] and "none to check" in sent[0]
    abstains, results = judged["r"]
    assert abstains is True
    assert (results[0]["label"], results[0]["flag"]) == (None, "excluded")
