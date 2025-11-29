"""Pinecone vector store wrapper (Pinecone Python SDK v5, serverless).

Each document gets its own Pinecone *namespace* (the document id). That keeps
every document's vectors isolated, makes retrieval scoped to a single document,
and makes deletion a one-call operation.
"""
from __future__ import annotations

import time
from functools import lru_cache

from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.services.chunking import Chunk

settings = get_settings()


@lru_cache(maxsize=1)
def _client() -> Pinecone:
    if not settings.pinecone_api_key:
        raise RuntimeError(
            "PINECONE_API_KEY is not set. Add it to backend/.env."
        )
    return Pinecone(api_key=settings.pinecone_api_key)


@lru_cache(maxsize=1)
def _index():
    pc = _client()
    existing = set(pc.list_indexes().names())
    if settings.pinecone_index not in existing:
        pc.create_index(
            name=settings.pinecone_index,
            dimension=settings.embedding_dim,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=settings.pinecone_cloud,
                region=settings.pinecone_region,
            ),
        )
        # Wait until the index is ready before first use.
        while not pc.describe_index(settings.pinecone_index).status["ready"]:
            time.sleep(1)
    return pc.Index(settings.pinecone_index)


def upsert_chunks(
    doc_id: str, chunks: list[Chunk], vectors: list[list[float]]
) -> None:
    """Store chunk vectors + metadata under the document's namespace."""
    index = _index()
    payload = [
        {
            "id": chunk.id,
            "values": vector,
            "metadata": {
                "doc_id": doc_id,
                "index": chunk.index,
                "page": chunk.page,
                "text": chunk.text,
            },
        }
        for chunk, vector in zip(chunks, vectors)
    ]
    # Pinecone caps batch size; upsert in slices of 100.
    for start in range(0, len(payload), 100):
        index.upsert(vectors=payload[start : start + 100], namespace=doc_id)


def query(doc_id: str, vector: list[float], top_k: int) -> list[dict]:
    """Return the top-k most similar chunks for a document."""
    index = _index()
    result = index.query(
        vector=vector,
        top_k=top_k,
        namespace=doc_id,
        include_metadata=True,
    )
    matches = []
    for match in result.get("matches", []):
        meta = match.get("metadata", {}) or {}
        matches.append(
            {
                "chunk_id": match["id"],
                "score": float(match["score"]),
                "page": int(meta["page"]) if "page" in meta else None,
                "text": meta.get("text", ""),
            }
        )
    return matches


def delete_document(doc_id: str) -> None:
    """Remove all vectors for a document."""
    try:
        _index().delete(namespace=doc_id, delete_all=True)
    except Exception:
        # Namespace may not exist yet (ingestion never finished) — ignore.
        pass
