"""Centralized configuration values shared across ingestion and (later) retrieval."""

# Multilingual (100 languages), retrieval-tuned embedding model. Requires
# "query: " / "passage: " prefixes on its inputs -- see app/embeddings.py.
# 512 token limit, chosen over paraphrase-multilingual-MiniLM-L12-v2 (128
# token limit) after discovering that limit was silently truncating ~99.8%
# of our real document chunks.
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIM = 384
