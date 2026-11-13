"""A2.6b step 2: the retry on its own, with the previous note and the new one.

    python -m app.evaluation.run_retry_note_check --dry-run
    python -m app.evaluation.run_retry_note_check --out 2026-11-13_retry_note --cap 59000

The rule, recorded in CLAUDE.md ("A2.6b rule", "Next steps") before this ran: re-run the saved
search queries of the 3 diagnosis runs of transfer_credits_en (local retrieval, 0 tokens) and call
only the retry, 10 times with the previous note (retry_input_previous, below) and 10 with the new
one (graph._retry_input), round-robin over the 3 search sets. The new note is kept only if at least
9/10 of its retries pass the gate and at least as many as the previous note's. Each passing retry
is then read by hand: a marker on a passage that doesn't hold the figure it's cited for counts as
a failure. This script counts gate passes; the hand reading, and the decision, aren't in it.

Each pair of calls uses the same search set, and which note goes first alternates, so neither
note gets the earlier or later minutes of the run. --dry-run builds every input and prints its
size, with no Groq call.

Calls the Groq API, and shares its daily quota with the live demo. Stops at --cap (checked before
each call, so it can go over by one retry) and at Groq's daily limit; waits out the per-minute one.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from groq import RateLimitError
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent import graph
from app.agent.citations import cited_markers, normalize_brackets, reset_citation_counter
from app.agent.gate import gate_answer
from app.agent.model import get_agent_model
from app.evaluation.generate_faithfulness_answers import (
    PER_MINUTE_RETRIES,
    PER_MINUTE_WAIT_SECONDS,
    is_per_minute_limit,
)
from app.evaluation.run_gate_diagnosis import RESULTS_DIR

DIAGNOSIS = RESULTS_DIR / "2026-11-12_diagnosis.jsonl"
QUESTION_ID = "transfer_credits_en"
LANGUAGE = "en"
PAIRS = 10
DEFAULT_CAP = 59_000

# The retry's note before A2.6b step 1. It lost on 2026-11-13 (7/10 against 9/10), so the graph
# no longer has it; it lives here so the comparison can be run again as it was.
PREVIOUS_CITATION_RETRY_NOTE = """Cite every fact in your answer with the bracket number of the \
result it comes from, e.g. [6]. Use only the bracket numbers that appear in the results above, \
never any other number."""


def retry_input_previous(messages, language: str | None) -> list:
    """The retry's input before step 1: the note at the end of the system prompt, no last note."""
    system, *conversation, _note = graph._retry_input(messages, language)
    content = system["content"] + "\n\n" + PREVIOUS_CITATION_RETRY_NOTE
    return [{"role": "system", "content": content}, *conversation]


NOTES = {
    "current": retry_input_previous,  # the note at the end of the system prompt
    "new": graph._retry_input,  # the note as the last message (step 1)
}


def diagnosis_runs(path: Path = DIAGNOSIS) -> list[dict]:
    """The diagnosis runs of QUESTION_ID, in order: their question, queries and markers."""
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return [r for r in records if r["id"] == QUESTION_ID]


def rebuild_conversation(question: str, queries: list[dict]) -> list:
    """The question and its searches, as the graph had them before the first answer.

    One search per round, in the saved order, through the real ToolNode and search_documents,
    so the passages, their markers and the fused phrasings (the question is one of them on a
    first turn) are what the agent got. The first answer isn't needed: the retry never sees it.
    """
    tool_graph = StateGraph(MessagesState)
    tool_graph.add_node("tools", ToolNode(graph.TOOLS))
    tool_graph.add_edge(START, "tools")
    tools = tool_graph.compile()

    reset_citation_counter()
    messages: list = [HumanMessage(question)]
    for i, args in enumerate(queries, start=1):
        call = AIMessage("", tool_calls=[{"id": f"c{i}", "name": "search_documents", "args": args}])
        result = tools.invoke({"messages": [*messages, call]})
        messages = [*messages, call, result["messages"][-1]]
    return messages


def known_markers(messages) -> set[int]:
    return {c["marker"] for m in messages if m.type == "tool" for c in m.artifact or []}


def schedule(pairs: int = PAIRS, sets: int = 3) -> list[tuple[int, int, str]]:
    """(pair, search set, note) for every call: round-robin sets, alternating which note leads."""
    calls = []
    for pair in range(pairs):
        order = ["current", "new"] if pair % 2 == 0 else ["new", "current"]
        calls += [(pair + 1, pair % sets, note) for note in order]
    return calls


def _invoke(model, messages) -> tuple[str, int, str | None]:
    """(text, tokens, error) for one retry. A refused tool call is an empty retry, as in the
    graph. Raises RateLimitError for the caller to wait or stop."""
    try:
        response = model.invoke(messages)
    except Exception as e:
        if not graph._is_refused_tool_call(e):
            raise
        return "", 0, "tool_call"
    usage = response.usage_metadata or {}
    tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    return str(response.content), tokens, None


def main_cli() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="Output file name, without .jsonl")
    parser.add_argument("--cap", type=int, default=DEFAULT_CAP)
    parser.add_argument("--dry-run", action="store_true", help="Build the inputs, call nothing")
    args = parser.parse_args()
    if not args.dry_run and not args.out:
        parser.error("--out is required unless --dry-run")

    runs = diagnosis_runs()
    conversations = []
    for n, run in enumerate(runs, start=1):
        messages = rebuild_conversation(run["question"], run["queries"])
        markers = known_markers(messages)
        if sorted(markers) != run["known_markers"]:
            print(f"Set {n}: markers {sorted(markers)}, diagnosis had {run['known_markers']}.")
            print("The searches don't match the diagnosis; stopping.")
            return 1
        conversations.append(messages)
        sizes = {
            note: len(json.dumps(build(messages, LANGUAGE), default=str, ensure_ascii=False))
            for note, build in NOTES.items()
        }
        print(f"Set {n}: {len(run['queries'])} searches, markers {sorted(markers)}, input {sizes}")

    calls = schedule(sets=len(conversations))
    if args.dry_run:
        print(f"\nDry run: {len(calls)} calls planned, none made.")
        return 0

    out_path = RESULTS_DIR / f"{args.out}.jsonl"
    model = get_agent_model()
    used = 0
    for pair, set_index, note in calls:
        if used >= args.cap:
            print(f"\nStopped at the cap: {used:,} tokens.")
            break
        messages = conversations[set_index]
        for attempt in range(1, PER_MINUTE_RETRIES + 2):
            try:
                text, tokens, error = _invoke(model, NOTES[note](messages, LANGUAGE))
                break
            except RateLimitError as e:
                if is_per_minute_limit(e) and attempt <= PER_MINUTE_RETRIES:
                    print(
                        f"pair {pair} {note}: per-minute limit, waiting {PER_MINUTE_WAIT_SECONDS}s"
                    )
                    time.sleep(PER_MINUTE_WAIT_SECONDS)
                    continue
                print(f"\nGroq's limit reached at pair {pair} {note}; stopping.")
                return 1
        known = known_markers(messages)
        verdict = gate_answer(text, tool_ran=True, known_markers=known, language=LANGUAGE).reason
        cited = cited_markers(normalize_brackets(text))
        record = {
            "pair": pair,
            "set": set_index + 1,
            "note": note,
            "answer": text,
            "verdict": verdict,
            "error": error,
            "cited": sorted(cited),
            "invented": sorted(cited - known),
            "tokens": tokens,
        }
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        used += tokens
        print(
            f"pair {pair:>2} set {set_index + 1} {note:<7} {verdict or 'passed':<15} {tokens:>6} tokens"
        )

    records = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    print(f"\n{used:,} tokens. Gate passes (to be read by hand before any decision):")
    for note in NOTES:
        done = [r for r in records if r["note"] == note]
        passed = sum(r["verdict"] is None for r in done)
        print(f"  {note:<7} {passed}/{len(done)}")
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
