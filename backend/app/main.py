"""FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = get_settings()

app = FastAPI(
    title="Document Processor API",
    description=(
        "Scan large PDFs / Word docs / images (with Tesseract OCR), index them "
        "with Sentence-Transformers + Pinecone, and summarise or chat with them "
        "using Google Gemini."
    ),
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "model": settings.gemini_model,
        "embedding_model": settings.embedding_model,
        "pinecone_index": settings.pinecone_index,
    }
