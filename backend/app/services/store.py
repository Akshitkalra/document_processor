"""Lightweight document registry persisted to disk as JSON.

This is intentionally simple — a real deployment would use a database. It
tracks document metadata + ingestion status, caches generated summaries, and
keeps the raw uploaded file on disk for re-processing.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.models.schemas import DocStatus, DocumentMeta

settings = get_settings()

_LOCK = threading.RLock()
_REGISTRY_PATH = settings.data_dir / "registry.json"
_FILES_DIR = settings.data_dir / "files"
_SUMMARY_DIR = settings.data_dir / "summaries"

for _d in (_FILES_DIR, _SUMMARY_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# In-memory cache of metadata; source of truth is the JSON file.
_docs: dict[str, DocumentMeta] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load() -> None:
    if not _REGISTRY_PATH.exists():
        return
    raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    for item in raw:
        meta = DocumentMeta.model_validate(item)
        _docs[meta.id] = meta


def _persist() -> None:
    data = [m.model_dump(mode="json") for m in _docs.values()]
    _REGISTRY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


_load()


def file_path(doc_id: str, filename: str) -> Path:
    suffix = Path(filename).suffix
    return _FILES_DIR / f"{doc_id}{suffix}"


def create(meta: DocumentMeta) -> DocumentMeta:
    with _LOCK:
        _docs[meta.id] = meta
        _persist()
    return meta


def update(doc_id: str, **fields) -> Optional[DocumentMeta]:
    with _LOCK:
        meta = _docs.get(doc_id)
        if meta is None:
            return None
        data = meta.model_dump()
        data.update(fields)
        data["updated_at"] = _now()
        meta = DocumentMeta.model_validate(data)
        _docs[doc_id] = meta
        _persist()
    return meta


def get(doc_id: str) -> Optional[DocumentMeta]:
    return _docs.get(doc_id)


def list_all() -> list[DocumentMeta]:
    return sorted(_docs.values(), key=lambda m: m.created_at, reverse=True)


def delete(doc_id: str) -> bool:
    with _LOCK:
        meta = _docs.pop(doc_id, None)
        if meta is None:
            return False
        _persist()
    # Best-effort cleanup of on-disk artefacts.
    fp = file_path(doc_id, meta.filename)
    fp.unlink(missing_ok=True)
    (_SUMMARY_DIR / f"{doc_id}.json").unlink(missing_ok=True)
    return True


def set_status(doc_id: str, status: DocStatus, **fields) -> None:
    update(doc_id, status=status, **fields)


# --- Summary cache ---

def save_summary(doc_id: str, payload: dict) -> None:
    (_SUMMARY_DIR / f"{doc_id}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def load_summary(doc_id: str) -> Optional[dict]:
    path = _SUMMARY_DIR / f"{doc_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
