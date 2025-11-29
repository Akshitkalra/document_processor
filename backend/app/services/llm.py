"""Thin wrapper around the Google Gemini API (``google-genai`` SDK).

Centralises client construction and a single ``complete`` helper used by both
the summariser and the chat service, so the rest of the code never talks to the
Gemini SDK directly.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from google import genai

from app.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to backend/.env."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def _to_contents(messages: list[dict]) -> list[dict]:
    """Map our (role, content) turns to Gemini ``contents``.

    Gemini uses the role ``model`` for assistant turns; everything else is
    treated as a ``user`` turn.
    """
    contents: list[dict] = []
    for m in messages:
        role = "model" if m.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    return contents


def complete(
    *,
    system: str,
    messages: list[dict],
    model: Optional[str] = None,
    max_tokens: int = 4096,
) -> str:
    """Run a single Gemini completion and return the response text."""
    client = get_client()
    response = client.models.generate_content(
        model=model or settings.gemini_model,
        contents=_to_contents(messages),
        config={
            "system_instruction": system,
            "max_output_tokens": max_tokens,
        },
    )
    return (response.text or "").strip()
