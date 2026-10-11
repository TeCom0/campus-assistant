"""Tests for claim splitting and citation scope (app.evaluation.split_claims).

The first three answers are real agent answers from the first faithfulness
run (2026-10-11); the rest are synthetic cases for each rule.
"""

from app.evaluation.split_claims import extract_claims, parse_blocks, split_sentences

TRANSFER_EN = (
    "The maximum number of credits that can be transferred to Al Akhawayn University for an "
    "undergraduate program is **68 semester credits** [1]."
)

PLAGIARISM_FR = (
    "Le plagiat, tel qu’il est défini dans le règlement de l’Université Al Akhawayn, consiste en "
    "« toute tentative de présenter les mots, le contenu ou les idées d’une autre personne comme "
    "étant les siens ». Cette pratique est considérée comme une infraction grave par le corps "
    "professoral et l’administration ; les contrevenants peuvent faire l’objet de sanctions "
    "sévères, allant de l’échec d’un cours à l’expulsion .[2]"
)

# "  \n" is a Markdown line break, as the model wrote it. Spelled out rather
# than left as trailing spaces, which editors and formatters strip.
ACC2302_EN = (
    "To enroll in **ACC 2302 – Accounting Principles II**, you must first complete "
    "**ACC 2301 – Accounting Principles I**.  \n"
    "ACC 2301 itself has a prerequisite that is an *alternative* among three math courses:\n"
    "\n"
    "| Course | Prerequisite (as listed) |\n"
    "|--------|--------------------------|\n"
    "| **ACC 2301** | *Requires:* MTH 1305, **or** MTH 1303, **or** MTH 1304 |\n"
    "| **MTH 1303** | Calculus I: Differential and Integral Calculus – *no prerequisites listed* |\n"
    "\n"
    "So, before taking ACC 2302 you must have completed **ACC 2301** and one of the math "
    "courses listed above.  \n"
    "Because the math courses are alternatives, you only need to take one of them. However, "
    "you may want to confirm with an academic advisor.  \n"
    "\n"
    "*Source: AUI catalog – ACC 2302 and ACC 2301 prerequisite chain* [1]"
)


def _kinds(answer: str, passages: set[int] = frozenset(range(1, 10))) -> list[tuple[str, list]]:
    return [(c["kind"], c["markers"]) for c in extract_claims(answer, set(passages))]


# --- the three real answers -------------------------------------------------


def test_single_cited_sentence():
    assert _kinds(TRANSFER_EN) == [("own", [1])]


def test_marker_after_the_period_covers_its_paragraph():
    claims = extract_claims(PLAGIARISM_FR, {1, 2, 3, 4, 5})
    assert [(c["kind"], c["markers"]) for c in claims] == [("block", [2]), ("own", [2])]
    assert claims[0]["text"].startswith("Le plagiat")


def test_source_line_covers_the_whole_answer_and_is_not_a_claim():
    claims = extract_claims(ACC2302_EN, {1})
    assert {c["kind"] for c in claims} == {"source_line"}
    assert all(c["markers"] == [1] for c in claims)
    assert not any("Source:" in c["text"] for c in claims)
    # 2 sentences before the table (a Markdown line break doesn't split the
    # paragraph, the sentence end does), 2 table rows, 3 sentences after.
    assert [c["block_type"] for c in claims] == ["paragraph"] * 2 + ["table_row"] * 2 + [
        "paragraph"
    ] * 3


def test_table_row_is_one_claim_rendered_with_its_headers():
    rows = [c for c in extract_claims(ACC2302_EN, {1}) if c["block_type"] == "table_row"]
    assert rows[0]["text"] == (
        "Course: **ACC 2301**; Prerequisite (as listed): *Requires:* MTH 1305, **or** MTH 1303, "
        "**or** MTH 1304"
    )


# --- sentence splitting -----------------------------------------------------


def test_split_keeps_decimals_and_abbreviations_together():
    text = "A GPA of 3.50 is needed, e.g. for honors. The cap is 20 SCH [1]."
    assert split_sentences(text) == [
        "A GPA of 3.50 is needed, e.g. for honors.",
        "The cap is 20 SCH [1].",
    ]


def test_split_handles_french_spacing_and_quotes():
    text = "Est-ce possible ? Oui, selon le catalogue [3]. « C'est la règle. » Fin [4]."
    assert split_sentences(text) == [
        "Est-ce possible ?",
        "Oui, selon le catalogue [3].",
        "« C'est la règle. »",
        "Fin [4].",
    ]


def test_marker_after_punctuation_moves_into_its_sentence():
    assert split_sentences("First fact. [2] Second fact.[3, 4] Third.") == [
        "First fact [2].",
        "Second fact [3, 4].",
        "Third.",
    ]


# --- citation scope rules ---------------------------------------------------


def test_list_items_without_markers_take_the_lead_in_markers():
    answer = "You need one of these courses [3]:\n- MTH 1303\n- MTH 1304 [4]\n- MTH 1305"
    assert _kinds(answer) == [("own", [3]), ("lead_in", [3]), ("own", [4]), ("lead_in", [4])]


def test_heading_starts_a_new_section_for_lead_in():
    answer = "Intro fact [1].\n\n## Other topic\n\n- item without a marker"
    assert _kinds(answer) == [("own", [1]), ("uncited", [])]


def test_bold_line_counts_as_a_heading():
    answer = "Intro fact [1].\n\n**Eligibility:**\n- item without a marker"
    assert _kinds(answer) == [("own", [1]), ("uncited", [])]


def test_prose_paragraph_does_not_inherit():
    assert _kinds("Fact [1].\n\nA new paragraph with no marker.") == [
        ("own", [1]),
        ("uncited", []),
    ]


def test_list_item_continuation_line_stays_in_the_item():
    blocks = parse_blocks("- First line\n  continues here [2].\n- Second")
    assert [(b.type, b.text) for b in blocks] == [
        ("list_item", "First line continues here [2]."),
        ("list_item", "Second"),
    ]


def test_marker_only_pieces_and_headings_are_not_claims():
    assert _kinds("# Prerequisites\n\nFact [1]. [2]") == [("own", [1, 2])]


def test_invalid_markers_are_flagged_and_all_invalid_is_auto_unsupported():
    claims = extract_claims("Real [1]. Mixed [1, 9]. Invented [9].", {1})
    assert [(c["invalid_markers"], c["auto_label"]) for c in claims] == [
        ([], None),
        ([9], None),
        ([9], "unsupported"),
    ]


def test_uncited_claims_have_no_markers_and_no_auto_label():
    claims = extract_claims("I don't know based on the available information.", {1, 2})
    assert [(c["kind"], c["markers"], c["auto_label"]) for c in claims] == [("uncited", [], None)]


# --- citation keys and sources sections (seen in add_drop_en, run 1) --------


def test_citation_key_list_is_not_claims_and_covers_the_uncited_table():
    answer = (
        "| Step | What to do |\n"
        "|------|------------|\n"
        "| 1 | Clear your holds. |\n"
        "| 2 | Use the online portal. |\n"
        "\n"
        "**Key citations**\n"
        "\n"
        "- Holds and form requirement: [4]  \n"
        "- Add/drop period dates: [7]\n"
        "\n"
        "If you're unsure, contact the registrar's office."
    )
    claims = extract_claims(answer, {4, 7})
    assert [(c["text"], c["kind"], c["markers"]) for c in claims] == [
        ("Step: 1; What to do: Clear your holds.", "source_line", [4, 7]),
        ("Step: 2; What to do: Use the online portal.", "source_line", [4, 7]),
        # The paragraph after the key list is a claim again, not part of it.
        ("If you're unsure, contact the registrar's office.", "source_line", [4, 7]),
    ]


def test_items_under_a_sources_heading_are_not_claims():
    answer = (
        "Fact without a marker.\n\n### Sources\n- [1] AUI catalog, p. 31\n- [2] Scholarships page"
    )
    assert [(c["kind"], c["markers"]) for c in extract_claims(answer, {1, 2})] == [
        ("source_line", [1, 2])
    ]


def test_lead_in_with_marker_before_the_colon_is_not_a_citation_key():
    blocks = parse_blocks("You need one of these courses [3]:\n- MTH 1303")
    assert [b.type for b in blocks] == ["paragraph", "list_item"]
    assert [b.type for b in parse_blocks("- Holds and form requirement: [4]")] == ["source_line"]


def test_line_breaks_inside_a_table_cell_become_spaces():
    answer = "| Action | Steps |\n|---|---|\n| Add | 1. Preregister. <br>2. Use the portal. [4] |"
    assert extract_claims(answer, {4})[0]["text"] == (
        "Action: Add; Steps: 1. Preregister.  2. Use the portal. [4]"
    )


# --- more ways run-1 answers placed their citation (2026-10-11) -------------


def test_marker_alone_on_the_last_line_covers_the_answer():
    # csc3326_prereqs_en
    answer = (
        "The prerequisites for **CSC 3326 – Database Systems** are:\n\n"
        "- **CSC 2306 (or CSC 1402 or BAI 3301)**  \n- **Junior classification**  \n\n[1]"
    )
    assert _kinds(answer, {1}) == [("source_line", [1])] * 3


def test_closing_attribution_sentence_covers_the_answer():
    # academic_probation_en (shortened)
    answer = (
        "If your semester GPA falls between **1.5 and 1.99**, you are on probation.\n\n"
        "* You may register for no more than **four courses**.\n\n"
        "This information is taken from the AUI academic catalog. [5]"
    )
    assert _kinds(answer, {5}) == [("source_line", [5])] * 2
    french = "Fait.\n\nCes informations proviennent du catalogue académique [2]."
    assert _kinds(french, {2}) == [("source_line", [2])]


def test_reference_entry_starting_with_its_marker_is_not_a_claim():
    # repeat_course_en
    answer = (
        "Yes, you can retake it.\n\n**Citation**\n\n"
        "[1] (repeat policy: “A student may repeat any course in which a C- or lower...”)"
    )
    assert _kinds(answer, {1}) == [("source_line", [1])]


def test_a_cited_fact_is_not_mistaken_for_an_attribution():
    assert _kinds("Les règles du catalogue fixent la limite à 68 crédits [1].", {1}) == [
        ("own", [1])
    ]
