# API Reference

Base URL (local): `http://localhost:8000`

All document endpoints are under `/api`. Interactive docs are available at
`/docs` (Swagger UI) when the server is running.

---

## `GET /health`

Health + configuration probe.

```json
{
  "status": "ok",
  "version": "1.0.0",
  "model": "gemini-2.5-flash",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "pinecone_index": "document-processor"
}
```

---

## `POST /api/documents`

Upload a document. `multipart/form-data` with a single `file` field.

**Accepted types:** PDF, DOCX/DOC, PNG/JPG/JPEG/TIFF/BMP/WEBP.

**Response `200`:**

```json
{
  "document": {
    "id": "9f1c…",
    "filename": "report.pdf",
    "content_type": "application/pdf",
    "size_bytes": 5242880,
    "status": "pending",
    "page_count": 0,
    "chunk_count": 0,
    "ocr_pages": 0,
    "char_count": 0,
    "error": null,
    "created_at": "2026-06-30T12:00:00Z",
    "updated_at": "2026-06-30T12:00:00Z",
    "progress": 0.0
  },
  "message": "Upload accepted. Ingestion started in the background."
}
```

Errors: `400` (empty file), `413` (over `MAX_UPLOAD_MB`).

---

## `GET /api/documents`

List all documents (newest first). Returns an array of `DocumentMeta`.

## `GET /api/documents/{id}`

Fetch one document's metadata + ingestion status. Poll this (or the list
endpoint) to track `status` / `progress`.

`status` values: `pending → extracting → embedding → ready` (or `failed`).

## `DELETE /api/documents/{id}`

Delete a document, its vectors, file, and cached summary.

```json
{ "deleted": "9f1c…" }
```

---

## `POST /api/documents/{id}/summary`

Generate (or return a cached) summary. Requires `status: ready` (else `409`).

**Request:**

```json
{ "focus": "financial risks", "max_words": 600 }
```

- `focus` (optional) steers the summary; when provided the result is **not**
  cached.
- `max_words` (100–3000) sizes the final summary.

**Response:**

```json
{
  "document_id": "9f1c…",
  "summary": "## Executive overview\n…",
  "section_summaries": ["- point\n- point", "…"],
  "model": "gemini-2.5-flash",
  "cached": false
}
```

---

## `POST /api/documents/{id}/chat`

Ask a question about the document (RAG). Requires `status: ready` (else `409`).

**Request:**

```json
{
  "question": "What are the termination clauses?",
  "history": [
    { "role": "user", "content": "Who are the parties?" },
    { "role": "assistant", "content": "Acme Corp and …" }
  ],
  "top_k": 8
}
```

**Response:**

```json
{
  "document_id": "9f1c…",
  "answer": "The contract may be terminated … (p. 14).",
  "citations": [
    {
      "chunk_id": "9f1c…-42",
      "page": 14,
      "score": 0.83,
      "text": "Either party may terminate …"
    }
  ],
  "model": "gemini-2.5-flash"
}
```

---

## Error format

FastAPI returns errors as:

```json
{ "detail": "Document is not ready (status: embedding)." }
```

| Status | Meaning |
| ------ | ------- |
| `400`  | Bad request (e.g. empty file) |
| `404`  | Document not found |
| `409`  | Document not ready for summary/chat |
| `413`  | File too large |
