"""
Citation building for Phase 3 RAG.

Why this file exists:
- keeps citation formatting out of generation/answer_builder.py
- gives the service a single place to normalize evidence references
- prepares cleaner citation objects for future UI display

This module does NOT do retrieval or answer generation.
It only turns already-selected chunks into stable citation objects.
"""

from __future__ import annotations

from rag_service.config import settings
from rag_service.schemas import RagCitation, RetrievedChunk


def _safe_pages(chunk: RetrievedChunk) -> list[int]:
    """
    Extract page numbers from chunk metadata safely.

    Returns an empty list when page metadata is missing or malformed.
    """
    metadata = chunk.metadata or {}
    value = metadata.get("pages", [])

    if not isinstance(value, list):
        return []

    pages: list[int] = []
    for item in value:
        try:
            pages.append(int(item))
        except (TypeError, ValueError):
            continue

    return sorted(set(pages))


def _safe_chunk_index(chunk: RetrievedChunk) -> int | None:
    """
    Extract chunk_index from metadata safely.
    """
    metadata = chunk.metadata or {}
    value = metadata.get("chunk_index")

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _make_snippet(text: str, max_chars: int) -> str:
    """
    Build a short readable text preview for citation display.
    """
    cleaned = " ".join((text or "").split()).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def build_citations(chunks: list[RetrievedChunk]) -> list[RagCitation]:
    """
    Build normalized citation objects from already-selected evidence chunks.

    Behavior:
    - preserves evidence order
    - deduplicates by chunk_id
    - assigns labels E1, E2, E3...
    - keeps the result bounded
    """
    citations: list[RagCitation] = []
    seen_chunk_ids: set[str] = set()

    for chunk in chunks:
        if chunk.chunk_id in seen_chunk_ids:
            continue

        seen_chunk_ids.add(chunk.chunk_id)

        citation = RagCitation(
            label=f"E{len(citations) + 1}",
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            file_name=chunk.file_name,
            source_ref=chunk.source_ref,
            pages=_safe_pages(chunk),
            snippet=_make_snippet(chunk.text, settings.CITATION_SNIPPET_CHARS),
            chunk_index=_safe_chunk_index(chunk),
        )
        citations.append(citation)

        if len(citations) >= settings.MAX_RETURNED_CITATIONS:
            break

    return citations