"""The LangGraph agent: an LLM with tool-calling access to search_documents.

(query_courses -- a structured lookup over real catalog course data, code/
title/credits/prerequisites -- will be added next; see CLAUDE.md's Current
status.)
"""

from datetime import UTC, datetime

from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.model import get_agent_model
from app.agent.tools import search_documents

SYSTEM_PROMPT_TEMPLATE = """You are the Al Akhawayn University (AUI) assistant. Today's date is \
{today}.

You have access to a search_documents tool over AUI's official documents. Use it whenever a \
question might be answered by those documents -- do not answer AUI-specific facts from your own \
general knowledge. If the tool's results don't contain the answer, say plainly that you don't \
know based on the available documents.

When you cite a claim, use the passage's bracket number exactly as given by the tool, e.g. [1], \
using plain ASCII square brackets only.

LANGUAGE (strict): detect the language of the student's question and write your ENTIRE answer \
in that same language -- if the question is in English, answer only in English; if in French, \
answer only in French. Never switch languages, even if the tool's results are in a different \
language than the question."""

TOOLS = [search_documents]


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


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    compiled_graph = build_graph()
    for question in [
        "How many credits can I transfer to AUI?",
        "Hello, how are you?",
    ]:
        print(f"=== {question} ===")
        result = compiled_graph.invoke({"messages": [{"role": "user", "content": question}]})
        for msg in result["messages"]:
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                print(f"[{msg.type}] called tool(s): {[tc['name'] for tc in tool_calls]}")
            else:
                print(f"[{msg.type}] {str(msg.content)[:300]}")
        print()
