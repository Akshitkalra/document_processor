"""HTTP API: upload, status, summary, chat, list, delete."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    DocStatus,
    DocumentMeta,
    SummaryRequest,
    SummaryResponse,
    UploadResponse,
)
from app.services import chat as chat_service
from app.services import store
from app.services import summarizer as summary_service
from app.services import vector_store
from app.services.chunking import chunk_pages
from app.services.extraction import extract
from app.services.ingestion import ingest_document

settings = get_settings()
router = APIRouter(prefix="/api", tags=["documents"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/documents", response_model=UploadResponse)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    """Accept a file, persist it, and kick off background ingestion."""
    doc_id = uuid.uuid4().hex
    path = store.file_path(doc_id, file.filename or "upload")

    # Stream to disk in 1 MB chunks so a large (e.g. 400-page scanned) PDF never
    # has to fit entirely in memory. Enforce the size limit incrementally.
    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0
    try:
        with path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds {settings.max_upload_mb} MB limit.",
                    )
                out.write(chunk)
    except HTTPException:
        path.unlink(missing_ok=True)
        raise

    if size == 0:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty file.")

    meta = DocumentMeta(
        id=doc_id,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        status=DocStatus.pending,
        created_at=_now(),
        updated_at=_now(),
    )
    store.create(meta)

    background.add_task(ingest_document, doc_id)
    return UploadResponse(document=meta)


@router.get("/documents", response_model=list[DocumentMeta])
async def list_documents() -> list[DocumentMeta]:
    return store.list_all()


@router.get("/documents/{doc_id}", response_model=DocumentMeta)
async def get_document(doc_id: str) -> DocumentMeta:
    meta = store.get(doc_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return meta


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    if store.get(doc_id) is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    vector_store.delete_document(doc_id)
    store.delete(doc_id)
    return {"deleted": doc_id}


def _require_ready(doc_id: str) -> DocumentMeta:
    meta = store.get(doc_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if meta.status != DocStatus.ready:
        raise HTTPException(
            status_code=409,
            detail=f"Document is not ready (status: {meta.status}).",
        )
    return meta


@router.post("/documents/{doc_id}/summary", response_model=SummaryResponse)
async def summarize_document(
    doc_id: str, request: SummaryRequest
) -> SummaryResponse:
    """Generate (or return cached) summary via map-reduce over the document."""
    meta = _require_ready(doc_id)

    # Serve cached summary unless the caller asked for a custom focus.
    if request.focus is None:
        cached = store.load_summary(doc_id)
        if cached:
            return SummaryResponse(**cached, cached=True)

    # Re-extract + chunk from the stored file (chunks aren't kept in memory).
    path = str(store.file_path(doc_id, meta.filename))
    result = extract(path, meta.content_type, meta.filename)
    chunks = chunk_pages(doc_id, result.pages)

    final, sections = summary_service.summarize(
        chunks, focus=request.focus, max_words=request.max_words
    )
    payload = {
        "document_id": doc_id,
        "summary": final,
        "section_summaries": sections,
        "model": settings.gemini_model,
    }
    if request.focus is None:
        store.save_summary(doc_id, payload)
    return SummaryResponse(**payload, cached=False)


@router.post("/documents/{doc_id}/chat", response_model=ChatResponse)
async def chat_with_document(
    doc_id: str, request: ChatRequest
) -> ChatResponse:
    """Answer a question about the document using RAG."""
    _require_ready(doc_id)
    answer, citations = chat_service.answer_question(
        doc_id=doc_id,
        question=request.question,
        history=request.history,
        top_k=request.top_k,
    )
    return ChatResponse(
        document_id=doc_id,
        answer=answer,
        citations=citations,
        model=settings.gemini_model,
    )
