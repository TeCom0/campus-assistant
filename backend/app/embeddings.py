"""Text embedding using a local multilingual sentence-transformers model.

Shared by both ingestion (embedding document chunks) and, later, retrieval
(embedding user questions) -- so this lives at the app root, not inside
app/ingestion/.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL_NAME


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it (loading takes a few seconds)."""
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed document chunks. e5 models expect a "passage: " prefix on document-side text."""
    model = get_model()
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single user question. e5 models expect a "query: " prefix on query-side text."""
    model = get_model()
    embeddings = model.encode(
        [f"query: {text}"], normalize_embeddings=True, show_progress_bar=False
    )
    return embeddings[0].tolist()


def count_tokens(texts: list[str]) -> list[int]:
    """Token count per text under the model's own tokenizer (matches what .encode() sees)."""
    tokenizer = get_model().tokenizer
    return [len(tokenizer.encode(t, add_special_tokens=True)) for t in texts]


if __name__ == "__main__":
    import numpy as np

    # e5 models compress cosine similarity into a narrow, high range (often
    # 0.7-0.95 even for unrelated pairs), so an absolute-score threshold is
    # meaningless. What matters is *relative ranking*: for a given query,
    # does the actually-related passage score higher than an unrelated one?
    query_en = "How many credits can I transfer to AUI?"
    query_fr = "Combien de crédits puis-je transférer à l'AUI ?"
    passage_related = (
        "For undergraduate programs, a maximum of 68 semester credits are transferable to AUI."
    )
    passage_unrelated = "Ifrane is known for its cold winters and heavy snowfall."

    query_vecs = np.array([embed_query(query_en), embed_query(query_fr)])
    passage_vecs = np.array(embed_passages([passage_related, passage_unrelated]))

    print(f"embedding dimension: {passage_vecs.shape[1]}")

    similarities = query_vecs @ passage_vecs.T
    for label, (sim_related, sim_unrelated) in zip(
        ["English query", "French query"], similarities, strict=True
    ):
        status = "PASS" if sim_related > sim_unrelated else "FAIL"
        print(f"{status}: {label} -> related={sim_related:.3f} unrelated={sim_unrelated:.3f}")
