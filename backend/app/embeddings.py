"""Text embedding using a local multilingual sentence-transformers model.

Shared by both ingestion (embedding document chunks) and, later, retrieval
(embedding user questions) -- so this lives at the app root, not inside
app/ingestion/.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

# Multilingual (50+ languages, including English and French) and compact
# (384 dimensions) enough to run comfortably on CPU. Chosen over larger
# multilingual models (e.g. mpnet-base, e5-base) as a starting point for
# speed and simplicity: it needs no special query/passage prefixing on its
# inputs, unlike e5-style models. Can be swapped later if Phase 2's
# evaluation set shows it's not accurate enough.
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it (loading takes a few seconds)."""
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into unit-length vectors.

    Normalizing to unit length means cosine similarity between two embeddings
    equals their plain dot product, and ranking by cosine similarity equals
    ranking by L2 distance -- giving flexibility in how pgvector compares
    them later (`<->` or `<=>`).
    """
    model = get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


if __name__ == "__main__":
    import numpy as np

    examples = [
        "How many credits can I transfer to AUI?",  # English
        "Combien de crédits puis-je transférer à l'AUI ?",  # French paraphrase of the above
        "What is the weather like in Ifrane in winter?",  # unrelated topic
    ]
    vectors = np.array(embed_texts(examples))

    print(f"embedding dimension: {vectors.shape[1]}")
    similarities = vectors @ vectors.T
    print("\ncosine similarity matrix:")
    for i, row in enumerate(similarities):
        print(f"{i}: " + " ".join(f"{v:.3f}" for v in row))
