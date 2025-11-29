"""Token-aware chunking with overlap.

Large documents are split into overlapping windows of roughly ``chunk_tokens``
tokens. Overlap preserves context across boundaries so retrieval doesn't cut a
sentence in half between two chunks. Each chunk keeps the page number it came
from for citations.
"""
from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from app.config import get_settings
from app.services.extraction import Page

settings = get_settings()

# A generic tokenizer is fine here — we only need approximate token counts to
# size chunks, not exact model-specific counts.
_encoder = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    id: str          # "<doc_id>-<index>"
    index: int
    text: str
    page: int
    token_count: int


def _split_page_text(text: str, target: int, overlap: int) -> list[tuple[str, int]]:
    """Split one page's text into (text, token_count) windows."""
    tokens = _encoder.encode(text)
    if not tokens:
        return []
    windows: list[tuple[str, int]] = []
    step = max(1, target - overlap)
    for start in range(0, len(tokens), step):
        window = tokens[start : start + target]
        if not window:
            break
        windows.append((_encoder.decode(window), len(window)))
        if start + target >= len(tokens):
            break
    return windows


def chunk_pages(doc_id: str, pages: list[Page]) -> list[Chunk]:
    """Turn extracted pages into an ordered list of overlapping chunks."""
    chunks: list[Chunk] = []
    index = 0
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        for window_text, token_count in _split_page_text(
            text, settings.chunk_tokens, settings.chunk_overlap_tokens
        ):
            chunks.append(
                Chunk(
                    id=f"{doc_id}-{index}",
                    index=index,
                    text=window_text,
                    page=page.number,
                    token_count=token_count,
                )
            )
            index += 1
    return chunks
