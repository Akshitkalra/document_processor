"""Retrieval-augmented chat over a single document.

Pipeline per question:
  1. Embed the question.
  2. Retrieve the top-k most relevant chunks from Pinecone (scoped to the doc).
  3. Build a grounded prompt with the retrieved context + prior turns.
  4. Ask Gemini to answer using only the context, citing page numbers.

Returns the answer plus the chunks that were used, so the UI can show
citations.
"""
from __future__ import annotations

from typing import Optional

from app.config import get_settings
from app.models.schemas import ChatTurn, Citation
from app.services import vector_store
from app.services.embeddings import embed_query
from app.services.llm import complete

settings = get_settings()

_SYSTEM = (
    "You are a helpful assistant answering questions about a specific "
    "document. Use ONLY the provided context excerpts to answer. Each excerpt "
    "is labelled with its page number. When you state a fact, cite the page "
    "like (p. 12). If the answer is not contained in the context, say you "
    "could not find it in the document rather than guessing."
)


def _format_context(matches: list[dict]) -> str:
    blocks = []
    for m in matches:
        page = m.get("page")
        label = f"[page {page}]" if page is not None else "[page ?]"
        blocks.append(f"{label}\n{m['text']}")
    return "\n\n---\n\n".join(blocks)


def answer_question(
    doc_id: str,
    question: str,
    history: list[ChatTurn],
    top_k: Optional[int] = None,
) -> tuple[str, list[Citation]]:
    k = top_k or settings.retrieval_top_k
    query_vector = embed_query(question)
    matches = vector_store.query(doc_id, query_vector, k)

    if not matches:
        return (
            "I couldn't find anything relevant in this document to answer "
            "that. The document may still be processing.",
            [],
        )

    context = _format_context(matches)

    # Replay prior conversation, then the grounded question.
    messages: list[dict] = [
        {"role": t.role, "content": t.content}
        for t in history
        if t.role in ("user", "assistant")
    ]
    messages.append(
        {
            "role": "user",
            "content": (
                f"Context excerpts from the document:\n\n{context}\n\n"
                f"Question: {question}"
            ),
        }
    )

    answer = complete(system=_SYSTEM, messages=messages, max_tokens=2048)

    citations = [
        Citation(
            chunk_id=m["chunk_id"],
            page=m.get("page"),
            score=m["score"],
            text=m["text"][:300],
        )
        for m in matches
    ]
    return answer, citations
