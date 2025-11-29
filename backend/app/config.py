"""Centralised configuration, loaded from environment variables / .env file.

Every tunable knob lives here so the rest of the codebase never reads
``os.environ`` directly. See ``.env.example`` for documentation of each value.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Google Gemini ---
    gemini_api_key: str = ""
    # Model used for the final summary and chat answers; override via GEMINI_MODEL.
    gemini_model: str = "gemini-2.5-flash"
    # Cheaper/faster model used for the high-volume "map" step of summarisation.
    gemini_map_model: str = "gemini-2.5-flash-lite"

    # --- Pinecone ---
    pinecone_api_key: str = ""
    pinecone_index: str = "document-processor"
    # Pinecone serverless spec.
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # --- Embeddings ---
    # all-MiniLM-L6-v2 -> 384 dims, fast and good enough for retrieval.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    embedding_batch_size: int = 64

    # --- Chunking ---
    chunk_tokens: int = 500        # target tokens per chunk
    chunk_overlap_tokens: int = 75  # overlap between consecutive chunks

    # --- OCR ---
    # Run OCR on a page only when its embedded text layer is shorter than this
    # many characters (i.e. the page is effectively a scan / image).
    ocr_min_text_chars: int = 50
    ocr_dpi: int = 200             # rasterisation DPI for OCR
    tesseract_lang: str = "eng"
    # Optional explicit path to the tesseract binary (Windows installs often
    # need this, e.g. C:\\Program Files\\Tesseract-OCR\\tesseract.exe).
    tesseract_cmd: str = ""

    # --- Retrieval / chat ---
    retrieval_top_k: int = 8       # chunks pulled per chat question
    summary_map_chunk_chars: int = 12000  # chars per map-reduce window

    # --- Storage / runtime ---
    data_dir: Path = Path("./data")          # uploaded files + metadata
    max_upload_mb: int = 200
    ingest_concurrency: int = 1              # background ingest workers

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
