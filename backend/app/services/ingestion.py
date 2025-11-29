"""Background ingestion pipeline: extract -> chunk -> embed -> upsert.

Runs off the request thread (FastAPI ``BackgroundTasks``) so a 400-page upload
doesn't block the HTTP response. Progress and status are written back to the
document registry as each stage completes.
"""
from __future__ import annotations

import logging

from app.config import get_settings
from app.models.schemas import DocStatus
from app.services import store, vector_store
from app.services.chunking import chunk_pages
from app.services.embeddings import embed_texts
from app.services.extraction import extract

settings = get_settings()
logger = logging.getLogger("ingestion")


def ingest_document(doc_id: str) -> None:
    meta = store.get(doc_id)
    if meta is None:
        logger.warning("ingest: unknown document %s", doc_id)
        return

    path = str(store.file_path(doc_id, meta.filename))
    try:
        # --- Extract (with OCR fallback) ---
        store.set_status(doc_id, DocStatus.extracting, progress=0.05)
        result = extract(path, meta.content_type, meta.filename)
        store.update(
            doc_id,
            page_count=result.page_count,
            ocr_pages=result.ocr_pages,
            char_count=result.char_count,
            progress=0.35,
        )

        # --- Chunk ---
        chunks = chunk_pages(doc_id, result.pages)
        if not chunks:
            store.set_status(
                doc_id,
                DocStatus.failed,
                error="No extractable text found in document.",
                progress=1.0,
            )
            return
        store.update(doc_id, chunk_count=len(chunks), progress=0.45)

        # --- Embed (batched) + upsert ---
        store.set_status(doc_id, DocStatus.embedding, progress=0.5)
        batch = max(1, settings.embedding_batch_size)
        total = len(chunks)
        for start in range(0, total, batch):
            window = chunks[start : start + batch]
            vectors = embed_texts([c.text for c in window])
            vector_store.upsert_chunks(doc_id, window, vectors)
            done = min(total, start + batch)
            store.update(doc_id, progress=0.5 + 0.45 * (done / total))

        store.set_status(doc_id, DocStatus.ready, progress=1.0, error=None)
        logger.info(
            "ingest complete: %s (%d pages, %d chunks, %d OCR pages)",
            doc_id,
            result.page_count,
            len(chunks),
            result.ocr_pages,
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the user
        logger.exception("ingest failed for %s", doc_id)
        store.set_status(
            doc_id, DocStatus.failed, error=str(exc), progress=1.0
        )
