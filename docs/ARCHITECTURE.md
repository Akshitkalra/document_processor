# Architecture

This document explains how the Document Processor works end to end.

## Components

| Layer            | Technology                          | Responsibility |
| ---------------- | ----------------------------------- | -------------- |
| Frontend         | React + Vite                        | Upload, status polling, summary + chat UI |
| API              | FastAPI                             | REST endpoints, request validation |
| Extraction       | PyMuPDF, python-docx, Pillow, Tesseract | Text + OCR from PDF/DOCX/images |
| Chunking         | tiktoken                            | Token-aware overlapping windows |
| Embeddings       | Sentence-Transformers (MiniLM)      | Vectorise chunks + queries |
| Vector DB        | Pinecone (serverless)               | Similarity search, per-document namespaces |
| LLM              | Google Gemini (`google-genai` SDK)  | Summaries + grounded answers |

## Ingestion pipeline

When a file is uploaded (`POST /api/documents`):

1. The raw bytes are written to `data/files/<id>.<ext>` and a `DocumentMeta`
   record is created with status `pending`.
2. A **background task** (`services/ingestion.ingest_document`) runs off the
   request thread:
   - **Extract** (`status: extracting`). For PDFs, PyMuPDF reads each page's
     text layer. If a page has fewer than `OCR_MIN_TEXT_CHARS` characters, that
     single page is rasterised at `OCR_DPI` and run through Tesseract. This means
     OCR only happens where it's actually needed — a 400-page born-digital PDF
     does zero OCR; a scanned PDF OCRs every page.
   - **Chunk.** Each page's text is split into ~`CHUNK_TOKENS`-token windows with
     `CHUNK_OVERLAP_TOKENS` of overlap, preserving the page number for citations.
   - **Embed + upsert** (`status: embedding`). Chunks are embedded in batches and
     upserted into Pinecone under the namespace `<document id>`.
   - On success the document is marked `ready`; on any error it's marked `failed`
     with the message stored for display.
3. Progress (`0.0 → 1.0`) is written to the registry at each stage; the frontend
   polls `GET /api/documents` every 2s while anything is processing.

### Why page-by-page + per-page OCR?

A 300–400 page PDF can be hundreds of MB once rasterised. Streaming one page at
a time keeps memory flat, and the text-layer-first strategy avoids OCR-ing pages
that already have selectable text (the common case), which is dramatically
faster and more accurate.

## Summarisation (map-reduce)

A long document doesn't fit in one prompt, so `services/summarizer` does:

1. **Map** — ordered chunks are packed into ~`SUMMARY_MAP_CHUNK_CHARS`-character
   windows; each window is summarised independently using the cheaper
   `GEMINI_MAP_MODEL` (`gemini-2.5-flash-lite` by default).
2. **Reduce** — all section summaries are fed to the `GEMINI_MODEL`
   (`gemini-2.5-flash` by default) to produce one coherent summary with an
   executive overview, thematic sections, and key takeaways.

Summaries with no custom `focus` are cached to `data/summaries/<id>.json`.

## Retrieval-augmented chat

For each question (`POST /api/documents/{id}/chat`):

1. The question is embedded with the same model used at ingest time.
2. Pinecone returns the top-`RETRIEVAL_TOP_K` chunks **from that document's
   namespace only**.
3. The chunks (with page labels) plus the prior conversation are sent to Gemini
   with a system instruction that tells it to answer **only** from the context
   and cite page numbers.
4. The answer and the source chunks (as citations) are returned.

## Gemini usage

`services/llm.complete` is the single entry point. It:

- defaults to `gemini-2.5-flash` (override per call, e.g. the cheaper map model),
- maps our `(role, content)` turns to Gemini `contents` (assistant → `model`),
- passes the grounding instructions via Gemini's `system_instruction`.

## Data & state

- **Document registry:** `data/registry.json` (metadata + status).
- **Raw files:** `data/files/`.
- **Cached summaries:** `data/summaries/`.
- **Vectors:** Pinecone, namespace per document.

Deleting a document removes its Pinecone namespace, registry entry, stored file,
and cached summary.

## Scaling notes

- Replace the JSON registry with Postgres for multi-instance deployments.
- Move ingestion to a task queue (Celery/RQ/Arq) instead of FastAPI background
  tasks if you expect many concurrent large uploads.
- Consider a larger embedding model (`all-mpnet-base-v2`, 768 dims) for higher
  retrieval quality — remember to update `EMBEDDING_DIM` and recreate the index.
