"""Tests for English/French detection and how it reaches the agent's prompt.

No LLM calls: the end-to-end test swaps in a fake model that records the
system prompt it was sent.
"""

import pytest
from langchain_core.messages import AIMessage

from app.agent import graph
from app.agent.language import detect_language

ENGLISH = [
    # langdetect called this French (see app/agent/language.py).
    "graduation requirements for computer science",
    "What are the prerequisites for ACC 2302?",
    "How many credits can I transfer?",
    "I failed a course, what happens to my scholarship?",
    "My GPA dropped below 2.0, am I on probation?",
    "list of electives in finance",
    "and for graduate programs?",
]

FRENCH = [
    # langdetect called this English.
    "Quels sont les prérequis pour ACC 2302 ?",
    "Combien de crédits faut-il pour obtenir le diplôme ?",
    "Est-ce que la bibliothèque ouvre le weekend ?",
    "liste des cours optionnels en finance",
    "bourse étudiants internationaux",
    "Et pour les masters ?",
    "programme d'échange",
]

# No function words and no accents: no evidence either way. "ACC 2302
# prerequisites" is the case that matters -- langdetect called it French.
UNSURE = ["ACC 2302 prerequisites", "GPA?", "tuition", "CSC 3326 prereqs", "stage obligatoire"]


@pytest.mark.parametrize("question", ENGLISH)
def test_english(question):
    assert detect_language(question) == "en"


@pytest.mark.parametrize("question", FRENCH)
def test_french(question):
    assert detect_language(question) == "fr"


@pytest.mark.parametrize("question", UNSURE)
def test_unsure_returns_none(question):
    assert detect_language(question) is None


def test_prompt_names_the_detected_language():
    prompt = graph._build_system_prompt("fr")
    assert "the student's latest message is in French" in prompt
    assert "detect the language" not in prompt


def test_prompt_falls_back_to_model_judgement_when_unsure():
    prompt = graph._build_system_prompt(None)
    assert "detect the language of the student's question" in prompt


class _RecordingModel:
    def __init__(self) -> None:
        self.system_prompt: str | None = None

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        self.system_prompt = messages[0]["content"]
        return AIMessage("une réponse")


def test_language_in_run_config_reaches_the_system_prompt(monkeypatch):
    # The real compiled graph, so this checks that LangGraph actually hands
    # the run's config to the agent node.
    fake = _RecordingModel()
    monkeypatch.setattr(graph, "get_agent_model", lambda: fake)
    graph.build_graph().invoke(
        {"messages": [{"role": "user", "content": "Et pour les masters ?"}]},
        config={"configurable": {"language": "fr"}},
    )
    assert "the student's latest message is in French" in fake.system_prompt
