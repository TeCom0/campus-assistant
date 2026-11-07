"""The progress lines a student reads while the answer is held: no text the model wrote."""

import pytest

from app.agent.tool_labels import build_tool_call_label


def test_a_search_label_never_holds_the_models_query():
    args = {"query": "Ignore this and read: you have won a prize", "query_en": "a prize"}
    label = build_tool_call_label("search_documents", args, "en")
    assert label == "Searching the documents..."
    assert (
        build_tool_call_label("search_documents", args, "fr") == "Recherche dans les documents..."
    )


@pytest.mark.parametrize("code", ["ACC 2302", "acc 2302", " MTH1305 ", "CSC 3326L"])
def test_a_real_course_code_is_shown(code):
    label = build_tool_call_label("query_courses", {"code": code}, "en")
    assert label == f"Looking up course {code.strip().upper()}"


def test_the_prerequisite_chain_is_named():
    args = {"code": "ACC 2302", "follow_prerequisites": True}
    assert build_tool_call_label("query_courses", args, "en") == (
        "Looking up course ACC 2302 and its prerequisite chain"
    )
    assert build_tool_call_label("query_courses", args, "fr") == (
        "Recherche du cours ACC 2302 et de sa chaîne de prérequis"
    )


@pytest.mark.parametrize(
    "code",
    ["you have won a prize", "ACC 2302 is cancelled", "<b>ACC 2302</b>", "", "2302", None],
)
def test_anything_else_in_the_code_argument_isnt_shown(code):
    assert build_tool_call_label("query_courses", {"code": code}, "en") == "Looking up a course"
    assert build_tool_call_label("query_courses", {"code": code}, "fr") == "Recherche d'un cours"


def test_no_language_means_english():
    assert build_tool_call_label("search_documents", {}, None) == "Searching the documents..."


def test_an_unknown_tool_is_named_by_code():
    assert build_tool_call_label("other", {"x": "y"}, "en") == "Using tool other"
