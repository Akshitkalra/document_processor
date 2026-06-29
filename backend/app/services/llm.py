"""Thin wrapper around the Google Gemini API (``google-genai`` SDK).

Centralises client construction and a single ``complete`` helper used by both
the summariser and the chat service, so the rest of the code never talks to the
Gemini SDK directly.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from google import genai
from google.genai import errors as genai_errors
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("llm")


def _is_retryable(exc: BaseException) -> bool:
    """Retry on rate limits (429) and transient server errors (5xx)."""
    if isinstance(exc, genai_errors.ServerError):
        return True
    if isinstance(exc, genai_errors.ClientError):
        code = getattr(exc, "code", None)
        return code == 429 or "RESOURCE_EXHAUSTED" in str(exc)
    return False


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


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=2, min=4, max=90),
    stop=stop_after_attempt(6),
    reraise=True,
    before_sleep=lambda s: logger.warning(
        "Gemini rate-limited/transient error; retrying (attempt %d)…",
        s.attempt_number,
    ),
)
def _generate(model: str, contents: list[dict], system: str, max_tokens: int):
    client = get_client()
    return client.models.generate_content(
        model=model,
        contents=contents,
        config={
            "system_instruction": system,
            "max_output_tokens": max_tokens,
        },
    )


def complete(
    *,
    system: str,
    messages: list[dict],
    model: Optional[str] = None,
    max_tokens: int = 4096,
) -> str:
    """Run a single Gemini completion and return the response text.

    Automatically retries with exponential backoff on rate limits (429) and
    transient server errors — important when summarising large documents, which
    issue many calls in quick succession.
    """
    response = _generate(
        model=model or settings.gemini_model,
        contents=_to_contents(messages),
        system=system,
        max_tokens=max_tokens,
    )
    text = (response.text or "").strip()
    if not text:
        # Model returned no text (e.g. blocked or hit the token cap before
        # emitting any). Surface a clear hint rather than a silent empty string.
        logger.warning("Gemini returned empty text (model=%s).", model)
    return text
