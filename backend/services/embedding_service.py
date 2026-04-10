"""
Embedding service for the RAG retrieval path.
Uses sentence-transformers (local model, no data leaves the environment).
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from backend.config import settings

_model = None  # lazy-loaded


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """Return (N, D) float32 embedding matrix."""
    model = _get_model()
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two unit-norm vectors."""
    return float(np.dot(a, b))


def retrieve_top_k(
    question: str,
    chunks: dict[str, str],
    k: int = 5,
) -> dict[str, str]:
    """Return the top-k chunks most similar to the question."""
    if not chunks:
        return {}
    names = list(chunks.keys())
    texts = list(chunks.values())
    q_emb = embed([question])[0]
    chunk_embs = embed(texts)
    scores = [(cosine_similarity(q_emb, chunk_embs[i]), names[i], texts[i]) for i in range(len(names))]
    scores.sort(reverse=True)
    return {name: text for _, name, text in scores[:k]}
