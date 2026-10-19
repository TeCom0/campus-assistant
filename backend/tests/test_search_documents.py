"""Tests for search_documents' multi-query search: which phrasings it fuses
(the agent's query, its English version, the student's question on a first
turn), the fallback when query_en is missing, and the schema the model sees.

The tool runs inside a one-node LangGraph graph, so InjectedState is filled
by ToolNode exactly as in the agent. Vector and keyword searches are stubs
that record each query, so no database or embedding model is needed.
"""

from dataclasses import dataclass

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent import graph
from app.agent.citations import reset_citation_counter
from app.agent.tools import search_documents, search_queries
from app.evaluation.generate_faithfulness_answers import searches
from app.retrieval import hybrid_search


@dataclass
class _Hit:
    source: str
    chunk_index: int
    pages: list[int]
    text: str
    section: str | None = None
    level: str = "general"
    sections: tuple = ()


@pytest.fixture
def searched(monkeypatch) -> list[str]:
    """Stub searches: "renewal" queries find chunk 7, anything else chunk 1.

    Returns the list of queries given to the vector search, one per query searched.
    """
    queries: list[str] = []

    def search_vector(query, top_k):
        queries.append(query)
        index = 7 if "renewal" in query else 1
        return [_Hit("catalog", index, [index], f"passage {index}")]

    monkeypatch.setattr(hybrid_search, "search_vector", search_vector)
    monkeypatch.setattr(hybrid_search, "search_keyword", lambda query, top_k: [])
    return queries


def _run_search(conversation: list, args: dict) -> str:
    """Run one search_documents call through ToolNode after `conversation`."""
    tool_node_graph = StateGraph(MessagesState)
    tool_node_graph.add_node("tools", ToolNode([search_documents]))
    tool_node_graph.add_edge(START, "tools")
    call = AIMessage("", tool_calls=[{"id": "1", "name": "search_documents", "args": args}])
    reset_citation_counter()
    result = tool_node_graph.compile().invoke({"messages": [*conversation, call]})
    return result["messages"][-1].content


FIRST_TURN_FR = [HumanMessage("Quelles sont les conditions pour garder ma bourse ?")]
FOLLOW_UP = [
    HumanMessage("How do I keep my scholarship?"),
    AIMessage("You need a 3.0 GPA."),
    HumanMessage("And for graduates?"),
]


def test_first_turn_fuses_query_english_version_and_the_question(searched):
    content = _run_search(
        FIRST_TURN_FR,
        {"query": "conditions bourse", "query_en": "scholarship renewal conditions"},
    )
    assert searched == [
        "conditions bourse",
        "scholarship renewal conditions",
        "Quelles sont les conditions pour garder ma bourse ?",
    ]
    assert "passage 7" in content  # found only by the English version


def test_follow_up_does_not_search_the_question(searched):
    _run_search(FOLLOW_UP, {"query": "graduate scholarship renewal", "query_en": "x"})
    assert searched == ["graduate scholarship renewal", "x"]


def test_english_query_equal_to_query_en_is_searched_once(searched):
    _run_search(FOLLOW_UP, {"query": "graduate GPA", "query_en": "Graduate  GPA"})
    assert searched == ["graduate GPA"]


def test_english_first_turn_with_all_three_equal_is_searched_once(searched):
    question = [HumanMessage("What is plagiarism?")]
    _run_search(question, {"query": "What is plagiarism?", "query_en": "What is plagiarism?"})
    assert searched == ["What is plagiarism?"]


@pytest.mark.parametrize("args", [{"query": "bourse"}, {"query": "bourse", "query_en": "  "}])
def test_missing_or_blank_query_en_falls_back_to_the_query(searched, args):
    content = _run_search(FOLLOW_UP, args)
    assert searched == ["bourse"]
    assert content.startswith("[1]")  # a normal result, not a tool error


def test_search_queries_counts_only_student_messages_as_turns():
    one_question_after_tool_calls = [
        HumanMessage("q"),
        AIMessage("", tool_calls=[{"id": "1", "name": "search_documents", "args": {}}]),
    ]
    assert search_queries("a", "b", one_question_after_tool_calls) == ["a", "b", "q"]
    assert search_queries("a", "b", FOLLOW_UP) == ["a", "b"]


def test_model_schema_requires_query_en_and_hides_the_state():
    search = next(t for t in graph.MODEL_TOOLS if isinstance(t, dict))
    parameters = search["function"]["parameters"]

    assert search["function"]["name"] == "search_documents"
    assert parameters["required"] == ["query", "query_en"]
    assert set(parameters["properties"]) == {"query", "query_en"}
    assert "default" not in parameters["properties"]["query_en"]


def test_eval_records_each_search_with_the_agents_translation():
    messages = [
        *FIRST_TURN_FR,
        AIMessage(
            "",
            tool_calls=[
                {"id": "1", "name": "search_documents",
                 "args": {"query": "bourse", "query_en": "scholarship"}},
                {"id": "2", "name": "search_documents", "args": {"query": "bourse"}},
                {"id": "3", "name": "query_courses", "args": {"code": "ACC 2302"}},
            ],
        ),
    ]  # fmt: skip
    question = FIRST_TURN_FR[0].content
    assert searches(messages) == [
        {"query": "bourse", "query_en": "scholarship", "searched": ["bourse", "scholarship", question]},
        {"query": "bourse", "query_en": None, "searched": ["bourse", question]},
    ]  # fmt: skip
