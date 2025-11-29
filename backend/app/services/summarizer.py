"""Hierarchical (map-reduce) summarisation for very large documents.

A 300-400 page document is far too large to summarise in one prompt. We:

  1. **Map** — group the document's chunks into windows of ~12k characters and
     summarise each window independently (cheap model, parallel-friendly).
  2. **Reduce** — feed all the section summaries to the flagship model to write
     one coherent, well-structured final summary.

Section summaries are returned too, so the UI can show an outline.
"""
from __future__ import annotations

from typing import Optional

from app.config import get_settings
from app.services.chunking import Chunk
from app.services.llm import complete

settings = get_settings()

_MAP_SYSTEM = (
    "You are a precise document analyst. Summarise the provided excerpt of a "
    "larger document. Capture key facts, figures, decisions, and arguments. "
    "Be faithful to the text and do not invent information. Output 4-8 concise "
    "bullet points."
)

_REDUCE_SYSTEM = (
    "You are an expert analyst writing the definitive summary of a long "
    "document. You are given ordered section summaries. Synthesise them into a "
    "single coherent summary with: a one-paragraph executive overview, then "
    "thematic sections with headings, then a short 'Key takeaways' list. "
    "Do not invent details that are not supported by the section summaries."
)


def _windows(chunks: list[Chunk], window_chars: int) -> list[str]:
    """Pack ordered chunks into ~window_chars-sized text windows."""
    windows: list[str] = []
    buf: list[str] = []
    size = 0
    for chunk in chunks:
        if size + len(chunk.text) > window_chars and buf:
            windows.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(chunk.text)
        size += len(chunk.text)
    if buf:
        windows.append("\n\n".join(buf))
    return windows


def summarize(
    chunks: list[Chunk],
    focus: Optional[str] = None,
    max_words: int = 600,
) -> tuple[str, list[str]]:
    """Return (final_summary, section_summaries)."""
    if not chunks:
        return "The document contains no extractable text.", []

    windows = _windows(chunks, settings.summary_map_chunk_chars)
    focus_hint = (
        f"\n\nPay special attention to: {focus}." if focus else ""
    )

    # --- Map ---
    section_summaries: list[str] = []
    for i, window in enumerate(windows, start=1):
        summary = complete(
            system=_MAP_SYSTEM,
            model=settings.gemini_map_model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Section {i} of {len(windows)}:{focus_hint}\n\n{window}"
                    ),
                }
            ],
        )
        section_summaries.append(summary)

    # Single-window documents need no reduce step.
    if len(section_summaries) == 1:
        return section_summaries[0], section_summaries

    # --- Reduce ---
    joined = "\n\n".join(
        f"## Section {i}\n{s}" for i, s in enumerate(section_summaries, start=1)
    )
    final = complete(
        system=_REDUCE_SYSTEM,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write the final summary in about {max_words} words."
                    f"{focus_hint}\n\nSection summaries:\n\n{joined}"
                ),
            }
        ],
    )
    return final, section_summaries
