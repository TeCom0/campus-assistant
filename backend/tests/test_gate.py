"""The answer-level gate, as a pure function, and on saved answers (0 LLM tokens)."""

import json
from pathlib import Path

import pytest

from app.agent.gate import (
    INVENTED_MARKER,
    NO_CITATION,
    NO_TOOL,
    NOT_FOUND_TEMPLATE,
    SCOPE_TEMPLATE,
    gate_answer,
)

RESULTS = Path(__file__).resolve().parents[2] / "eval" / "results" / "faithfulness"


def _gate(answer, *, tool_ran=True, known=frozenset({1, 2}), language="en", fallback=False):
    return gate_answer(
        answer, tool_ran=tool_ran, known_markers=set(known), language=language, fallback=fallback
    )


def test_an_answer_with_valid_citations_goes_out_unchanged():
    result = _gate("You can transfer 68 credits [1], or 12 for a master's [2].")
    assert result.answer == "You can transfer 68 credits [1], or 12 for a master's [2]."
    assert result.reason is None


def test_no_tool_gets_the_scope_template_whatever_the_model_wrote():
    # The reported case: the model answered this from its own knowledge.
    result = _gate("1 + 1 = 2.", tool_ran=False, known=())
    assert result.answer == SCOPE_TEMPLATE["en"]
    assert result.reason == NO_TOOL


def test_no_tool_is_rejected_even_if_the_answer_has_markers():
    # With no tool, no marker can be real. A jailbreak could ask for "[1]".
    assert _gate("It's 2 [1].", tool_ran=False, known=()).reason == NO_TOOL


def test_a_tool_ran_but_no_citation_gets_the_not_found_template():
    result = _gate("The catalog says 68 credits.")
    assert result.answer == NOT_FOUND_TEMPLATE["en"]
    assert result.reason == NO_CITATION


def test_a_number_no_tool_returned_gets_the_not_found_template():
    result = _gate("68 credits [7].")
    assert result.answer == NOT_FOUND_TEMPLATE["en"]
    assert result.reason == INVENTED_MARKER


def test_one_invented_number_among_real_ones_is_rejected():
    assert _gate("68 credits [1], and 12 more [7].").reason == INVENTED_MARKER


def test_a_grouped_citation_counts_each_number():
    assert _gate("68 credits [1, 2].").reason is None
    assert _gate("68 credits [1, 7].").reason == INVENTED_MARKER


def test_full_width_brackets_count_as_markers():
    # /chat normalizes them per token, and the check doesn't rely on that.
    assert _gate("68 credits 【1】.").reason is None


def test_a_bracketed_year_reads_as_an_invented_number():
    # A known cost of the marker pattern: it can't tell "[2024]" from a citation.
    assert _gate("In the catalog [2024], 68 credits [1].").reason == INVENTED_MARKER


def test_the_code_built_fallback_goes_out_as_it_is():
    text = "I couldn't finish this answer. Please try asking again."
    result = _gate(text, known=(), fallback=True)
    assert result.answer == text
    assert result.reason is None


@pytest.mark.parametrize(
    ("language", "expected"), [("fr", "fr"), ("en", "en"), (None, "en")], ids=str
)
def test_templates_follow_the_detected_language(language, expected):
    no_tool = _gate("x", tool_ran=False, known=(), language=language)
    assert no_tool.answer == SCOPE_TEMPLATE[expected]
    no_citation = _gate("x", language=language)
    assert no_citation.answer == NOT_FOUND_TEMPLATE[expected]


def test_the_scope_template_names_what_is_covered():
    assert "academic catalog and scholarship pages" in SCOPE_TEMPLATE["en"]
    assert "le catalogue académique et les pages de bourses" in SCOPE_TEMPLATE["fr"]


# --- On saved answers: rule item 1 in CLAUDE.md ---------------------------------------


def _replaced(filename: str) -> dict[str, str]:
    """Which saved answers the gate would replace, as {id: reason}."""
    replaced = {}
    for line in (RESULTS / filename).read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        result = gate_answer(
            record["answer"],
            tool_ran=bool(record["tool_calls"]),
            known_markers={passage["marker"] for passage in record["passages"]},
            language=record["language"],
            fallback=bool(record.get("fallback")),
        )
        if result.reason:
            replaced[record["id"]] = result.reason
    return replaced


def test_on_run_3_it_replaces_exactly_the_three_refusals():
    # Each of these declines an unanswerable question, so the template is as good or better.
    assert _replaced("answers_run3.jsonl") == {
        "fulbright_en": NO_CITATION,
        "instructor_en": NO_CITATION,
        "instructor_fr": NO_CITATION,
    }


def test_on_the_uncited_answers_sample_it_replaces_only_add_drop():
    replaced = _replaced("answers_citation_check_2026-11-06.jsonl")
    assert replaced == {"add_drop_en": NO_CITATION}
