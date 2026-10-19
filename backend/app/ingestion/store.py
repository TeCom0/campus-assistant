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
        (source, chunk_index, text, pages, language, level, section, sections, model_name,
         embedding)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (source, chunk_index, model_name)
    DO UPDATE SET text = EXCLUDED.text, pages = EXCLUDED.pages,
                  language = EXCLUDED.language, level = EXCLUDED.level,
                  section = EXCLUDED.section, sections = EXCLUDED.sections,
                  embedding = EXCLUDED.embedding
"""


def load_chunks() -> list[dict]:
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


DELETE_MODEL_SQL = "DELETE FROM document_chunks WHERE model_name = %s"
COUNT_MODEL_SQL = "SELECT count(*) FROM document_chunks WHERE model_name = %s"


def chunk_row(chunk: dict, vector, model_name: str = EMBEDDING_MODEL_NAME) -> tuple:
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
        chunk["sections"],
        model_name,
        Vector(vector),
    )


def replace_rows(conn, rows: list[tuple], model_name: str) -> int:
    """Delete every chunk of `model_name` and insert `rows`, in one transaction;
    returns how many rows were deleted.

    The upsert alone keys on (source, chunk_index, model_name), so after a
    re-chunk that produces fewer chunks, the old extra rows would stay and
    still be searched. One transaction: if an insert fails, the delete is
    undone too and the table is left as it was.
    """
    with conn.transaction():
        deleted = conn.execute(DELETE_MODEL_SQL, (model_name,)).rowcount
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, rows)
    return deleted


def update_sections(conn, chunks: list[dict], model_name: str = EMBEDDING_MODEL_NAME) -> int:
    """Set only the `sections` metadata of the loaded chunks, in one transaction.

    For changes that leave every chunk's text as it is, so nothing needs
    re-embedding. Refuses (changing nothing) unless each chunk is already
    loaded with exactly this text: otherwise the metadata would describe text
    that isn't there, and a full --replace is needed instead.
    """
    loaded = {
        (source, index): text
        for source, index, text in conn.execute(
            "SELECT source, chunk_index, text FROM document_chunks WHERE model_name = %s",
            (model_name,),
        ).fetchall()
    }
    differs = [
        (c["source"], c["chunk_index"])
        for c in chunks
        if loaded.get((c["source"], c["chunk_index"])) != c["text"]
    ]
    if differs or len(loaded) != len(chunks):
        raise SystemExit(
            f"{len(differs)} chunks differ from the loaded ones ({len(loaded)} loaded, "
            f"{len(chunks)} in chunks.jsonl): the text changed, so use --replace. "
            f"First differences: {differs[:5]}"
        )
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            "UPDATE document_chunks SET sections = %s "
            "WHERE source = %s AND chunk_index = %s AND model_name = %s",
            [(c["sections"], c["source"], c["chunk_index"], model_name) for c in chunks],
        )
    return len(chunks)


def _embed_all(chunks: list[dict]) -> list:
    vectors = []
    for i in range(0, len(chunks), BATCH_SIZE):
        vectors.extend(embed_passages([c["text"] for c in chunks[i : i + BATCH_SIZE]]))
        print(f"embedded {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks")
    return vectors


def store_chunks(chunks: list[dict], replace: bool = False) -> None:
    conn = get_connection(register_vector_type=False)
    init_schema(conn)

    if replace:
        # Embed first (CPU, ~1-2 min), so the transaction isn't held open meanwhile.
        vectors = _embed_all(chunks)
        rows = [chunk_row(c, v) for c, v in zip(chunks, vectors, strict=True)]
        deleted = replace_rows(conn, rows, EMBEDDING_MODEL_NAME)
        print(f"replaced: deleted {deleted} old chunks, inserted {len(rows)}")
    else:
        with conn.cursor() as cur:
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i : i + BATCH_SIZE]
                vectors = embed_passages([c["text"] for c in batch])
                rows = [chunk_row(c, vector) for c, vector in zip(batch, vectors, strict=True)]
                cur.executemany(UPSERT_SQL, rows)
                print(f"stored {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks")
        in_table = conn.execute(COUNT_MODEL_SQL, (EMBEDDING_MODEL_NAME,)).fetchone()[0]
        if in_table > len(chunks):
            print(
                f"WARNING: the table has {in_table} chunks for this model but chunks.jsonl has "
                f"{len(chunks)}: stale rows from an earlier chunking remain. Re-run with --replace."
            )

    conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete this model's chunks and insert chunks.jsonl, in one transaction "
        "(needed after re-chunking)",
    )
    parser.add_argument(
        "--sections-only",
        action="store_true",
        help="Only update the sections metadata of chunks already loaded with the same text "
        "(no re-embedding)",
    )
    args = parser.parse_args()
    all_chunks = load_chunks()
    print(f"loaded {len(all_chunks)} chunks from {CHUNKS_PATH}")
    if args.sections_only:
        connection = get_connection(register_vector_type=False)
        init_schema(connection)
        print(f"updated sections of {update_sections(connection, all_chunks)} chunks")
        connection.close()
    else:
        store_chunks(all_chunks, replace=args.replace)
    print("done")
