"""FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="Campus AI Assistant")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
