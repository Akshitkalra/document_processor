"""Pydantic request/response models shared across the API."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocStatus(str, Enum):
    pending = "pending"
    extracting = "extracting"
    embedding = "embedding"
    ready = "ready"
    failed = "failed"


class DocumentMeta(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    status: DocStatus = DocStatus.pending
    page_count: int = 0
    chunk_count: int = 0
    ocr_pages: int = 0          # pages that required OCR
    char_count: int = 0
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    progress: float = 0.0       # 0..1 ingestion progress


class UploadResponse(BaseModel):
    document: DocumentMeta
    message: str = "Upload accepted. Ingestion started in the background."


class SummaryRequest(BaseModel):
    # Optional steering for the summary (e.g. "focus on financial risks").
    focus: Optional[str] = Field(default=None, max_length=500)
    max_words: int = Field(default=600, ge=100, le=3000)


class SummaryResponse(BaseModel):
    document_id: str
    summary: str
    section_summaries: list[str] = []
    model: str
    cached: bool = False


class Citation(BaseModel):
    chunk_id: str
    page: Optional[int] = None
    score: float
    text: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    # Prior turns as (role, content) so the conversation stays stateless.
    history: list["ChatTurn"] = []
    top_k: Optional[int] = Field(default=None, ge=1, le=30)


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatResponse(BaseModel):
    document_id: str
    answer: str
    citations: list[Citation] = []
    model: str


ChatRequest.model_rebuild()
