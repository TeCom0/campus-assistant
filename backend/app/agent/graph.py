"""The LangGraph agent: an LLM with tool-calling access to search_documents
(unstructured document search) and query_courses (structured course lookups)
-- deliberately two different tools, since "what do I need before taking
ACC 2302?" is a structured prerequisite-chain query that semantic search
over narrative text can't reliably answer.
"""

from datetime import UTC, datetime

import groq
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.citations import reset_citation_counter
from app.agent.model import get_agent_model
from app.agent.tools import query_courses, search_documents
from app.config import MAX_TOOL_ROUNDS

SYSTEM_PROMPT_TEMPLATE = """You are the Al Akhawayn University (AUI) assistant. Today's date is \
{today}.

You have access to two tools:
- search_documents: search AUI's official documents (academic policies, course catalog \
descriptions, scholarship information). Use this for general questions answerable from those \
documents.
- query_courses: look up a specific course by its code (e.g. "ACC 2302") in the structured \
course catalog -- returns its title, credits, and prerequisites. Pass follow_prerequisites=True \
to get the FULL prerequisite chain (not just the immediate prerequisite) for questions like \
"what do I need before taking X?". Use this tool, not search_documents, whenever the question \
names or implies a specific course code, or asks about prerequisite chains. Keep the catalog's \
"and"/"or" logic exactly; if the wording is ambiguous or depends on the student's school, quote \
it and suggest confirming with an academic advisor rather than choosing an interpretation.

The student's latest message may be a follow-up that depends on earlier turns. Before calling a \
tool, write its query so it stands alone: carry the topic over from earlier in the conversation \
(e.g. "credit transfer limit for graduate programs", not just "graduate programs"). Make at most \
two search_documents calls per question; if the results already answer it, stop searching and \
answer.

Do not answer AUI-specific facts from your own general knowledge -- always use a tool. If neither \
tool's results contain the answer, say plainly that you don't know based on the available \
information.

CITATIONS: every passage or course fact returned by EITHER tool starts with its own bracket \
number, e.g. [6] -- these numbers are globally unique across the whole conversation (a second \
or third tool call continues the sequence, it does not restart at [1]). When you state a fact \
that came from a tool, cite it with that exact number right after the claim, e.g. [6]. Use the \
ordinary keyboard characters "[" and "]" only -- never full-width or other Unicode bracket \
variants (e.g. not 【6】) -- since this exact format is parsed by code. Never invent a citation \
number yourself; only ever use a number a tool actually gave you.

{language_rule}"""

# The language is detected in code (app.agent.language) and passed in through
# the run's config, so the model is told it rather than left to judge it --
# an English question was once answered in French. When detection is unsure
# (e.g. "GPA?"), the model judges it as before.
LANGUAGE_NAMES = {"en": "English", "fr": "French"}

LANGUAGE_RULE_KNOWN = """LANGUAGE (strict): the student's latest message is in {language_name}. \
Write your ENTIRE answer in {language_name}, even if tool results or earlier turns of the \
conversation are in a different language."""

LANGUAGE_RULE_UNKNOWN = """LANGUAGE (strict): detect the language of the student's question and \
write your ENTIRE answer in that same language -- if the question is in English, answer only in \
English; if in French, answer only in French. Never switch languages, even if tool results are \
in a different language than the question."""

TOOLS = [search_documents, query_courses]

BUDGET_EXHAUSTED_NOTE = """Tools are no longer available for this question. Answer now using \
only the tool results provided in the conversation, with citations as usual. If they don't \
contain the answer, say plainly that you don't know based on the available information."""

# Added for the one retry after the model called a tool anyway (see _forced_answer).
FORCED_RETRY_NOTE = """Do not call any tool, and do not write a tool call or a search query: \
no tool can be used any more. Write your answer as plain text now."""

# The answer built in code when both forced attempts fail: no LLM text, just
# the passages the searches found, cited by their markers so /chat lists them
# as sources. Flagged in response_metadata so the evaluation counts it as a
# failed answer, not a real one.
FALLBACK_WITH_SOURCES = {
    "en": "I couldn't finish this answer. These passages found while searching may help:",
    "fr": "Je n'ai pas pu terminer cette réponse. Ces passages trouvés pendant la recherche "
    "peuvent vous aider :",
}
FALLBACK_NO_SOURCES = {
    "en": "I couldn't finish this answer. Please try asking again, in other words if possible.",
    "fr": "Je n'ai pas pu terminer cette réponse. Veuillez reposer la question, si possible "
    "autrement.",
}


def is_fallback_answer(text: str) -> bool:
    """True for an answer _fallback_answer built (the client sends it back as history)."""
    texts = [*FALLBACK_WITH_SOURCES.values(), *FALLBACK_NO_SOURCES.values()]
    return any(text.startswith(t) for t in texts)


def _build_system_prompt(language: str | None) -> str:
    if language in LANGUAGE_NAMES:
        language_rule = LANGUAGE_RULE_KNOWN.format(language_name=LANGUAGE_NAMES[language])
    else:
        language_rule = LANGUAGE_RULE_UNKNOWN
    return SYSTEM_PROMPT_TEMPLATE.format(
        today=datetime.now(UTC).date().isoformat(), language_rule=language_rule
    )


def _tool_rounds_since_last_question(messages) -> int:
    """Count agent turns that called tools since the student's latest message.

    Walks backwards and stops at the latest human message, so tool rounds from
    earlier questions in the conversation don't count against this one. Several
    tool calls made in one turn count as one round.
    """
    rounds = 0
    for msg in reversed(messages):
        if msg.type == "human":
            break
        if msg.type == "ai" and msg.tool_calls:
            rounds += 1
    return rounds


def _latest_question_index(messages) -> int:
    return max(i for i, m in enumerate(messages) if m.type == "human")


def _without_tool_calls(messages) -> list:
    """Rewrite the conversation with no tool-call structure, for the forced final answer.

    Keeps the student's messages and earlier plain-text answers, drops the
    agent's tool-call turns, and passes the latest question's tool results
    as one plain-text message. With no tool definitions and no tool calls to
    imitate, the model has nothing tool-shaped to produce -- tool_choice="none"
    wasn't enough: Groq rejects a tool call the model still generates, it
    doesn't prevent it.
    """
    last_question = _latest_question_index(messages)
    conversation = [
        m
        for m in messages[: last_question + 1]
        if m.type == "human" or (m.type == "ai" and not m.tool_calls)
    ]
    results = [str(m.content) for m in messages[last_question + 1 :] if m.type == "tool"]
    return [
        *conversation,
        HumanMessage("Results of the searches made for this question:\n\n" + "\n\n".join(results)),
    ]


def _is_refused_tool_call(error: Exception) -> bool:
    """True for Groq's "Tool choice is none, but model called a tool" error.

    It comes in two shapes: a 400 response (BadRequestError, details under
    body["error"]), or, when the answer is streamed as in /chat, an error event
    inside the stream (APIError, details directly in body). Both carry the code
    "tool_use_failed".
    """
    if not isinstance(error, groq.APIError) or not isinstance(error.body, dict):
        return False
    details = error.body.get("error", error.body)
    return isinstance(details, dict) and details.get("code") == "tool_use_failed"


def _fallback_answer(messages, language: str | None) -> AIMessage:
    """The answer when the model can't produce one: the passages found, by marker."""
    markers = sorted(
        {
            citation["marker"]
            for m in messages[_latest_question_index(messages) + 1 :]
            if m.type == "tool"
            for citation in getattr(m, "artifact", None) or []
        }
    )
    text_language = "fr" if language == "fr" else "en"
    if markers:
        text = FALLBACK_WITH_SOURCES[text_language] + " " + " ".join(f"[{n}]" for n in markers)
    else:
        text = FALLBACK_NO_SOURCES[text_language]
    return AIMessage(text, response_metadata={"fallback": True})


def _forced_answer(messages, system_prompt: str, language: str | None) -> AIMessage:
    """The final answer once the tool budget is used.

    No tools are bound and the conversation has no tool-call structure, yet
    gpt-oss-20b still emits a tool call ~9% of the time (6/68 answers over
    faithfulness runs 1-2), and Groq rejects it. So: one retry with a stronger
    "plain text" note, then the code-built fallback. Any other error is raised
    as before -- only this known failure is handled.
    """
    model = get_agent_model()
    conversation = _without_tool_calls(messages)
    system_prompt += "\n\n" + BUDGET_EXHAUSTED_NOTE
    prompts = [system_prompt, system_prompt + "\n\n" + FORCED_RETRY_NOTE]
    for attempt, prompt in enumerate(prompts, start=1):
        try:
            return model.invoke([{"role": "system", "content": prompt}, *conversation])
        except Exception as e:
            if not _is_refused_tool_call(e):
                raise
            print(f"[agent] forced answer, attempt {attempt}: the model called a tool")
    print("[agent] forced answer failed twice; sending the fallback answer")
    return _fallback_answer(messages, language)


def _agent_node(state: MessagesState, config: RunnableConfig | None = None) -> dict:
    # LangGraph passes the run's config to a node that declares a `config`
    # parameter. The language lives there, not in the state: it's fixed for
    # the whole run and no node changes it.
    language = (config or {}).get("configurable", {}).get("language")
    system_prompt = _build_system_prompt(language)
    if _tool_rounds_since_last_question(state["messages"]) >= MAX_TOOL_ROUNDS:
        # Budget used: no tools bound and no tool calls in the conversation,
        # so the model can only answer.
        response = _forced_answer(state["messages"], system_prompt, language)
    else:
        model = get_agent_model().bind_tools(TOOLS)
        messages = [{"role": "system", "content": system_prompt}, *state["messages"]]
        response = model.invoke(messages)
    return {"messages": [response]}


def build_graph():
    graph = StateGraph(MessagesState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def _print_messages(messages, truncate: int | None = None) -> None:
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            print(f"[{msg.type}] called tool(s): {[tc['name'] for tc in tool_calls]}")
        else:
            content = str(msg.content)
            if truncate:
                content = content[:truncate]
            print(f"[{msg.type}] {content}")


def _run_test_questions(compiled_graph) -> None:
    for question in [
        "How many credits can I transfer to AUI?",
        "Hello, how are you?",
        "What are the prerequisites for ACC 2302?",
        "What do I need before taking ACC 2302, including indirect prerequisites?",
        "Tell me about course XYZ 9999.",
    ]:
        print(f"=== {question} ===")
        reset_citation_counter()
        result = compiled_graph.invoke({"messages": [{"role": "user", "content": question}]})
        _print_messages(result["messages"], truncate=400)
        print()


def _run_interactive_chat(compiled_graph) -> None:
    print("Interactive agent chat. Type 'exit' to quit.\n")
    messages: list = []
    while True:
        try:
            question = input("> ").strip()
        except EOFError:
            break
        if question.lower() == "exit":
            break
        if not question:
            continue

        messages.append({"role": "user", "content": question})
        reset_citation_counter()
        result = compiled_graph.invoke({"messages": messages})
        _print_messages(result["messages"][len(messages) :])
        messages = result["messages"]
        print()


if __name__ == "__main__":
    import argparse
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--chat", action="store_true", help="Interactive chat mode (type 'exit' to quit)"
    )
    args = parser.parse_args()

    graph = build_graph()
    if args.chat:
        _run_interactive_chat(graph)
    else:
        _run_test_questions(graph)
        print()
