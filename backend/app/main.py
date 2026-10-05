"""FastAPI application entrypoint."""

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.citations import reset_citation_counter
from app.agent.graph import build_graph
from app.agent.tool_labels import build_tool_call_label, detect_language
from app.config import CORS_ORIGINS

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


class ChatRequest(BaseModel):
    question: str
    # No conversation history field yet (requests are single-turn/stateless) --
    # deliberately a plain BaseModel so an optional `messages` field can be added
    # later (e.g. `messages: list[dict] | None = None`) without breaking existing
    # callers; Pydantic models support new optional fields as a non-breaking change.


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    async def event_stream():
        reset_citation_counter()
        language = detect_language(request.question)
        citations: list[dict] = []

        try:
            async for stream_mode, chunk in _compiled_graph.astream(
                {"messages": [{"role": "user", "content": request.question}]},
                stream_mode=["messages", "updates"],
            ):
                if stream_mode == "messages":
                    msg_chunk, metadata = chunk
                    if metadata.get("langgraph_node") == "agent" and msg_chunk.content:
                        yield _sse("token", {"text": _normalize_token(msg_chunk.content)})

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

            yield _sse("citations", {"citations": citations})
            yield _sse("done", {})

        except Exception as e:  # noqa: BLE001 -- deliberately broad: any failure
            # mid-stream must still close the SSE stream with an error event,
            # not a silently dropped connection. Full detail logged server-side
            # only; the client gets a generic message, not internal exception text.
            print(f"[chat] error while streaming answer: {e!r}")
            yield _sse("error", {"message": "Something went wrong while generating the answer."})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
