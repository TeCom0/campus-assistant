"""FastAPI application entrypoint."""

import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.generation import stream_answer

app = FastAPI(title="Campus AI Assistant")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    question: str


@app.post("/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    def event_stream():
        for event in stream_answer(request.question):
            data = json.dumps(event, ensure_ascii=False)
            yield f"event: {event['type']}\ndata: {data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
