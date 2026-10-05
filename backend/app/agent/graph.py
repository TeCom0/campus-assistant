"""The LangGraph agent: an LLM with tool-calling access to search_documents
(unstructured document search) and query_courses (structured course lookups)
-- deliberately two different tools, since "what do I need before taking
ACC 2302?" is a structured prerequisite-chain query that semantic search
over narrative text can't reliably answer.
"""

from datetime import UTC, datetime

from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.citations import reset_citation_counter
from app.agent.model import get_agent_model
from app.agent.tools import query_courses, search_documents

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
names or implies a specific course code, or asks about prerequisite chains.

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

LANGUAGE (strict): detect the language of the student's question and write your ENTIRE answer in \
that same language -- if the question is in English, answer only in English; if in French, \
answer only in French. Never switch languages, even if tool results are in a different language \
than the question."""

TOOLS = [search_documents, query_courses]


def _build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(today=datetime.now(UTC).date().isoformat())


def _agent_node(state: MessagesState) -> dict:
    model = get_agent_model().bind_tools(TOOLS)
    messages = [{"role": "system", "content": _build_system_prompt()}, *state["messages"]]
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
