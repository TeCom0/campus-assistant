"""Embed chunks (data/processed/chunks.jsonl) and store them in Postgres."""

import json
from pathlib import Path

from pgvector import Vector

from app.config import EMBEDDING_MODEL_NAME
from app.db.connection import get_connection, init_schema
from app.embeddings import embed_passages

CHUNKS_PATH = Path(__file__).resolve().parents[3] / "data" / "processed" / "chunks.jsonl"

BATCH_SIZE = 64

UPSERT_SQL = """
    INSERT INTO document_chunks
        (source, chunk_index, text, pages, language, level, section, model_name, embedding)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (source, chunk_index, model_name)
    DO UPDATE SET text = EXCLUDED.text, pages = EXCLUDED.pages,
                  language = EXCLUDED.language, level = EXCLUDED.level,
                  section = EXCLUDED.section, embedding = EXCLUDED.embedding
"""


def load_chunks() -> list[dict]:
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def chunk_row(chunk: dict, vector) -> tuple:
    """One UPSERT_SQL row. level/section are read strictly: a chunks.jsonl
    written before they existed fails here instead of loading as "general"."""
    return (
        chunk["source"],
        chunk["chunk_index"],
        chunk["text"],
        chunk["pages"],
        chunk["language"],
        chunk["level"],
        chunk["section"],
        EMBEDDING_MODEL_NAME,
        Vector(vector),
    )


def store_chunks(chunks: list[dict]) -> None:
    conn = get_connection(register_vector_type=False)
    init_schema(conn)

    with conn.cursor() as cur:
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            vectors = embed_passages([c["text"] for c in batch])

            rows = [chunk_row(c, vector) for c, vector in zip(batch, vectors, strict=True)]
            cur.executemany(UPSERT_SQL, rows)
            print(f"stored {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks")

    conn.close()


if __name__ == "__main__":
    all_chunks = load_chunks()
    print(f"loaded {len(all_chunks)} chunks from {CHUNKS_PATH}")
    store_chunks(all_chunks)
    print("done")
