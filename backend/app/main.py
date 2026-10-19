"""FastAPI application entrypoint."""

import json
from contextlib import asynccontextmanager
from typing import Literal

import groq
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel

from app.agent.citations import (
    keep_cited,
    normalize_brackets,
    reset_citation_counter,
    without_passage_text,
)
from app.agent.graph import build_graph
from app.agent.history import build_input_messages
from app.agent.language import detect_language
from app.agent.tool_labels import build_tool_call_label
from app.config import CORS_ORIGINS, MAX_AGENT_STEPS
from app.db.connection import get_connection, init_schema
from app.limits import Decision, check_and_record, client_ip, hash_ip, message
from app.sources import link_target, with_display_info


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Idempotent (IF NOT EXISTS throughout): makes sure question_log exists on
    # a server whose database was loaded before the table was added.
    conn = get_connection(register_vector_type=False)
    try:
        init_schema(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="Campus AI Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
_compiled_graph = build_graph()


@app.get("/sources/{source_id}", response_model=None)
def open_source(source_id: str, page: int | None = None) -> RedirectResponse | JSONResponse:
    """A source card's link: the document at the cited page, or its fallback
    page if the document's URL doesn't answer (app/sources.py). Not a question,
    so not counted against the demo limits."""
    target = link_target(source_id, page)
    if target is None:
        return JSONResponse(status_code=404, content={"message": "Unknown source"})
    return RedirectResponse(target, status_code=302)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    # Prior turns, oldest first. Optional, so single-turn callers keep working.
    messages: list[HistoryMessage] | None = None


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def admit_question(http_request: Request) -> Decision:
    """Record the question against the demo limits, or refuse it (app/limits.py)."""
    conn = get_connection()
    try:
        return check_and_record(conn, hash_ip(client_ip(http_request)))
    finally:
        conn.close()


# response_model=None: it returns Response objects itself (a stream, or a 429),
# so there's no model for FastAPI to derive from the return annotation.
@app.post("/chat", response_model=None)
async def chat(request: ChatRequest, http_request: Request) -> StreamingResponse | JSONResponse:
    language = detect_language(request.question)
    # Checked before any LLM call, so a refused question costs no tokens.
    decision = admit_question(http_request)
    if not decision.allowed:
        return JSONResponse(
            status_code=429,
            content={"kind": decision.kind, "message": message(decision.kind, language)},
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    async def event_stream():
        reset_citation_counter()
        citations: list[dict] = []
        # Everything streamed as answer text, so the citations event can list
        # only the markers the answer actually uses. A marker can arrive split
        # across tokens ("[" then "3]"), hence the whole text, not per token.
        answer_parts: list[str] = []

        try:
            history = [m.model_dump() for m in request.messages or []]
            async for stream_mode, chunk in _compiled_graph.astream(
                {"messages": build_input_messages(request.question, history)},
                config={
                    "recursion_limit": MAX_AGENT_STEPS,
                    "configurable": {"language": language},
                },
                stream_mode=["messages", "updates"],
            ):
                if stream_mode == "messages":
                    msg_chunk, metadata = chunk
                    if metadata.get("langgraph_node") == "agent" and msg_chunk.content:
                        text = normalize_brackets(msg_chunk.content)
                        answer_parts.append(text)
                        yield _sse("token", {"text": text})

                elif stream_mode == "updates":
                    for node_name, node_output in chunk.items():
                        if node_name == "agent":
                            for msg in node_output.get("messages", []):
                                for tc in getattr(msg, "tool_calls", None) or []:
                                    label = build_tool_call_label(tc["name"], tc["args"], language)
                                    yield _sse(
                                        "tool_call",
                                        {"tool": tc["name"], "args": tc["args"], "label": label},
                                    )
                        elif node_name == "tools":
                            for msg in node_output.get("messages", []):
                                artifact = getattr(msg, "artifact", None)
                                if artifact:
                                    citations.extend(artifact)

            cited = with_display_info(
                without_passage_text(keep_cited(citations, "".join(answer_parts)))
            )
            yield _sse("citations", {"citations": cited})
            yield _sse("done", {})

        except groq.RateLimitError as e:
            # Groq's own limit, hit mid-answer: say so kindly instead of the
            # generic error. "per minute" (tokens/min) clears within a minute;
            # anything else (tokens/day) only tomorrow.
            print(f"[chat] Groq rate limit: {e!r}")
            kind = "busy" if "per minute" in str(e) else "daily_cap"
            yield _sse("error", {"message": message(kind, language), "kind": "limit"})

        except Exception as e:  # noqa: BLE001 -- deliberately broad: any failure
            # mid-stream must still close the SSE stream with an error event,
            # not a silently dropped connection. Full detail logged server-side
            # only; the client gets a generic message, not internal exception text.
            print(f"[chat] error while streaming answer: {e!r}")
            yield _sse("error", {"message": "Something went wrong while generating the answer."})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
