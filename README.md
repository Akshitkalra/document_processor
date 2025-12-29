# 📄 Document Processor

Scan **large PDFs (300–400+ pages)**, Word documents, and scanned images, then
**summarise** them or **chat** with them using retrieval-augmented generation.

Built with **Python 3.11 + FastAPI** on the backend and **React (Vite)** on the
frontend. Uses **Tesseract** for OCR, **Sentence-Transformers** for embeddings,
**Pinecone** as the vector database, and **Google Gemini** for summaries and answers.

---

## ✨ Features

- **Handles huge documents.** PDFs are streamed page-by-page so a 400-page file
  doesn't blow up memory.
- **Smart OCR.** Each PDF page's embedded text layer is used when present;
  Tesseract OCR runs **only** on pages that are actually scans/images — so you
  don't pay the OCR cost on every page.
- **Semantic search.** Token-aware overlapping chunks are embedded with
  Sentence-Transformers and stored in Pinecone (one namespace per document).
- **Hierarchical summaries.** A map-reduce pipeline summarises each section with
  a fast model, then synthesises a final structured summary with Gemini — so
  document size is no longer a context-window problem.
- **Grounded chat (RAG).** Questions retrieve the most relevant chunks and Gemini
  answers using only that context, **citing page numbers**.
- **Background ingestion** with live progress in the UI.

---

## 🏗️ Architecture

```
                       ┌──────────────────────────── React (Vite) ───────────────────────────┐
                       │  Uploader · DocumentList · SummaryPanel · ChatPanel                  │
                       └───────────────────────────────┬──────────────────────────────────────┘
                                                        │ REST (/api/*)
                       ┌────────────────────────────────▼─────────────────────────────────────┐
                       │                       FastAPI backend                                 │
                       │                                                                        │
   upload ──▶ extraction ──▶ chunking ──▶ embeddings ──▶ Pinecone (vector DB, per-doc namespace)│
   (PyMuPDF + Tesseract OCR)  (token windows) (MiniLM)                                          │
                       │                                                                        │
   summary  ◀── map-reduce summariser ─────────────────────────────────▶ Gemini (Google)      │
   chat     ◀── retrieve top-k ──▶ grounded prompt ───────────────────▶ Gemini (Google)       │
                       └────────────────────────────────────────────────────────────────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a deeper walkthrough and
[`docs/API.md`](docs/API.md) for the full endpoint reference.

---

## 📋 Prerequisites

- **Python 3.11**
- **Node.js 18+**
- **Tesseract OCR** installed on the host (the engine, not just the Python lib):
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
  - Windows: install from
    [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki),
    then set `TESSERACT_CMD` in `backend/.env`.
- A **Pinecone** account + API key — https://www.pinecone.io
- A **Google Gemini** API key — https://aistudio.google.com/app/apikey

---

## 🚀 Quick start (local)

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then edit .env and add your keys
uvicorn app.main:app --reload --port 8000
```

The first request downloads the Sentence-Transformers model (~90 MB) and lazily
creates the Pinecone index — give it a moment.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the backend on
port 8000, so no extra config is needed.

---

## 🐳 Deploy with Docker (VPS-ready)

Tesseract OCR and all system deps are baked into the images — nothing to install
on the host but Docker.

```bash
cp backend/.env.example backend/.env   # add GEMINI_API_KEY + PINECONE_API_KEY
docker compose up -d --build
```

Open **http://&lt;server-ip&gt;/** — nginx serves the built frontend on port 80 and
proxies `/api` to the backend container (which stays internal). Data persists in
the `backend-data` volume.

For the full VPS guide (HTTPS, a non-Docker systemd/nginx install that
`apt`-installs Tesseract, sizing notes), see **[docs/DEPLOY.md](docs/DEPLOY.md)**.

### Local development

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Frontend (Vite, hot reload): http://localhost:5173
- Backend: http://localhost:8000

---

## 🔑 Configuration

All backend settings are environment variables — see
[`backend/.env.example`](backend/.env.example) for the annotated list. The most
important ones:

| Variable             | Purpose                                            |
| -------------------- | -------------------------------------------------- |
| `GEMINI_API_KEY`     | Required for summaries + chat                       |
| `PINECONE_API_KEY`   | Required for indexing + retrieval                   |
| `GEMINI_MODEL`       | Final summary + chat model (default `gemini-2.5-flash`) |
| `GEMINI_MAP_MODEL`   | Per-section summary model (default `gemini-2.5-flash-lite`) |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | Must agree; MiniLM = 384 dims        |
| `TESSERACT_CMD`      | Path to the tesseract binary (Windows)              |

---

## 📁 Project layout

```
document processor/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # env-driven settings
│   │   ├── api/routes.py      # REST endpoints
│   │   ├── models/schemas.py  # pydantic models
│   │   └── services/
│   │       ├── extraction.py  # PDF/DOCX/image + Tesseract OCR
│   │       ├── chunking.py    # token-aware overlapping chunks
│   │       ├── embeddings.py  # sentence-transformers
│   │       ├── vector_store.py# Pinecone
│   │       ├── summarizer.py  # map-reduce summary
│   │       ├── chat.py        # RAG chat
│   │       ├── llm.py         # Gemini client
│   │       ├── ingestion.py   # background pipeline
│   │       └── store.py       # document registry
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                  # React + Vite
├── docs/                      # architecture + API reference
└── docker-compose.yml
```

---

## ⚠️ Notes & limitations

- The document registry is a JSON file on disk — fine for a single instance, but
  swap in a database for production / horizontal scaling.
- OCR speed depends on the number of scanned pages and your `OCR_DPI`.
- Pinecone serverless indexes are created automatically on first use.
