"""FastAPI application entrypoint."""

import json
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.citations import keep_cited, reset_citation_counter
from app.agent.graph import build_graph
from app.agent.history import build_input_messages
from app.agent.language import detect_language
from app.agent.tool_labels import build_tool_call_label
from app.config import CORS_ORIGINS, MAX_AGENT_STEPS

app = FastAPI(title="Campus AI Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
_compiled_graph = build_graph()

# LLM output occasionally uses full-width Unicode brackets (e.g. "【4】")
# instead of the ASCII "[4]" the system prompt asks for -- confirmed directly in
# the raw token stream, not just the final text, so this is corrected
# deterministically here rather than relying on prompt-following alone.
_BRACKET_FIXES = {"【": "[", "】": "]"}


def _normalize_token(text: str) -> str:
    for bad, good in _BRACKET_FIXES.items():
        text = text.replace(bad, good)
    return text


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


@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    async def event_stream():
        reset_citation_counter()
        language = detect_language(request.question)
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
                        text = _normalize_token(msg_chunk.content)
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

            cited = keep_cited(citations, "".join(answer_parts))
            yield _sse("citations", {"citations": cited})
            yield _sse("done", {})

        except Exception as e:  # noqa: BLE001 -- deliberately broad: any failure
            # mid-stream must still close the SSE stream with an error event,
            # not a silently dropped connection. Full detail logged server-side
            # only; the client gets a generic message, not internal exception text.
            print(f"[chat] error while streaming answer: {e!r}")
            yield _sse("error", {"message": "Something went wrong while generating the answer."})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
