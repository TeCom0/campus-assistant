"""Generate the saved example answers shown on the UI's empty state.

Each example question (frontend/src/exampleQuestions.json) is answered once by
the real agent, exactly as /chat answers it (same graph, history, language
detection, step limit, citation filtering and display info). The results go
to a REVIEW folder outside the repo, never straight into the app:

- <id>.json      the file the app would replay (no passage text, which the
                 browser never receives either)
- review.md      each answer next to the full text of the passages it cites,
                 for the author to check before anything is saved

Only after the author approves an example does --approve copy it into
frontend/src/examples/, where the app replays it without any API call (no LLM
tokens, not counted by the demo limits). Saved files carry
"cached_example": true and live outside eval/results/, so the evaluation
never counts them.

Usage (from backend/):
    python -m app.generate_examples --out <review folder>            # all 4
    python -m app.generate_examples --out <review folder> --ids add_drop_fr
    python -m app.generate_examples --out <review folder> --approve add_drop_fr,transfer_credits_en
"""

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from groq import RateLimitError

from app.agent.citations import keep_cited, normalize_brackets, reset_citation_counter
from app.agent.graph import build_graph
from app.agent.history import build_input_messages
from app.agent.language import detect_language
from app.agent.tool_labels import build_tool_call_label
from app.config import GEMINI_MODEL, GROQ_MODEL, LLM_PROVIDER, MAX_AGENT_STEPS
from app.sources import with_display_info

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"
QUESTIONS_PATH = FRONTEND / "exampleQuestions.json"
SAVED_DIR = FRONTEND / "examples"


def answer_example(graph, example: dict) -> tuple[dict, list[dict]]:
    """(the file to replay, the cited passages with their text, for review)."""
    language = detect_language(example["question"])
    reset_citation_counter()
    result = graph.invoke(
        {"messages": build_input_messages(example["question"], None)},
        config={"recursion_limit": MAX_AGENT_STEPS, "configurable": {"language": language}},
    )
    messages = result["messages"]
    answer = normalize_brackets(
        "".join(m.content for m in messages if m.type == "ai" and isinstance(m.content, str))
    )
    tool_calls = [
        {"tool": tc["name"], "label": build_tool_call_label(tc["name"], tc["args"], language)}
        for m in messages
        if m.type == "ai"
        for tc in m.tool_calls
    ]
    citations = [c for m in messages if m.type == "tool" for c in (m.artifact or [])]
    cited = keep_cited(citations, answer)  # with the passage text, for review
    saved = {
        "id": example["id"],
        "question": example["question"],
        "language": example["language"],
        "cached_example": True,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": GROQ_MODEL if LLM_PROVIDER == "groq" else GEMINI_MODEL,
        "tool_calls": tool_calls,
        "answer": answer,
        "citations": [
            {k: v for k, v in c.items() if k != "text"} for c in with_display_info(cited)
        ],
    }
    return saved, cited


def review_section(saved: dict, cited: list[dict]) -> str:
    lines = [f"## {saved['id']}", "", f"**Question:** {saved['question']}", ""]
    lines += [f"**Tool calls:** {', '.join(c['label'] for c in saved['tool_calls']) or 'none'}", ""]
    lines += ["**Answer:**", "", saved["answer"], "", "**Cited passages:**"]
    shown = {c["marker"]: c for c in saved["citations"]}
    for c in cited:
        card = shown.get(c["marker"], {})
        pages = ", ".join(map(str, c.get("pages") or [])) or "-"
        lines += [
            "",
            f"[{c['marker']}] {card.get('title', c['source'])}, p. {pages} -- {card.get('section') or ''}",
        ]
        lines += ["", "```text", c["text"], "```"]
    if not cited:
        lines += ["", "(none: the answer cites nothing)"]
    return "\n".join(lines) + "\n"


def generate(ids: list[str] | None, out: Path) -> int:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    selected = [q for q in questions if not ids or q["id"] in ids]
    out.mkdir(parents=True, exist_ok=True)
    graph = build_graph()
    sections = []
    for example in selected:
        try:
            saved, cited = answer_example(graph, example)
        except RateLimitError as e:
            print(f"{example['id']}: Groq rate limit, stopping. Re-run with --ids later.\n{e}")
            break
        (out / f"{example['id']}.json").write_text(
            json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        sections.append(review_section(saved, cited))
        print(
            f"{example['id']}: {len(saved['tool_calls'])} tool calls, {len(cited)} cited passages"
        )
    review = out / "review.md"
    with review.open("a", encoding="utf-8") as f:
        f.writelines(sections)
    print(f"-> {review}")
    return len(sections)


def approve(ids: list[str], out: Path) -> None:
    SAVED_DIR.mkdir(exist_ok=True)
    for example_id in ids:
        source = out / f"{example_id}.json"
        if not source.exists():
            raise SystemExit(f"{source} doesn't exist: generate it first")
        shutil.copyfile(source, SAVED_DIR / source.name)
        print(f"saved {SAVED_DIR / source.name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="Review folder, outside the repo")
    parser.add_argument("--ids", help="Comma-separated example ids (default: all)")
    parser.add_argument("--approve", help="Comma-separated ids the author approved: copy them")
    args = parser.parse_args()
    if args.approve:
        approve(args.approve.split(","), args.out)
    else:
        generate(args.ids.split(",") if args.ids else None, args.out)
