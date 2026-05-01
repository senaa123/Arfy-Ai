"""
Neighbor expansion for Phase 2 self-healing RAG.

This module expands the final evidence set using already-retrieved candidate
chunks that sit next to strong seed chunks in the same document.

Why this is useful:
- a strong answer often spans multiple adjacent chunks
- this improves context without needing a new memory_service endpoint
- it keeps Phase 2 small and architecture-safe
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from rag_service.config import settings
from rag_service.schemas import RetrievedChunk


def _safe_chunk_index(chunk: RetrievedChunk) -> int | None:
    """
    Extract chunk_index from chunk metadata safely.

    We return None if the metadata is missing or malformed.
    """
    metadata = chunk.metadata or {}
    value = metadata.get("chunk_index")

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def expand_context_with_neighbors(
    *,
    seed_chunks: list[RetrievedChunk],
    candidate_chunks: list[RetrievedChunk],
    window: int | None = None,
    max_chunks: int | None = None,
) -> list[RetrievedChunk]:
    """
    Expand strong seed chunks using adjacent chunks from the same document.

    Strategy:
    - keep the seed chunks first
    - for each seed chunk, try to add chunk_index-1 and chunk_index+1
    - only use chunks that already exist in the candidate pool
    - deduplicate by chunk_id
    - stop when max_chunks is reached

    This keeps the method simple and bounded.
    """
    if not seed_chunks:
        return []

    effective_window = window if window is not None else settings.NEIGHBOR_EXPANSION_WINDOW
    effective_max = max_chunks if max_chunks is not None else settings.NEIGHBOR_EXPANSION_MAX_CHUNKS

    # Build a lookup by (document_id, chunk_index).
    candidate_index: Dict[Tuple[str, int], RetrievedChunk] = {}
    for chunk in candidate_chunks:
        chunk_index = _safe_chunk_index(chunk)
        if chunk_index is None:
            continue
        candidate_index[(chunk.document_id, chunk_index)] = chunk

    expanded: List[RetrievedChunk] = []
    seen_chunk_ids: set[str] = set()

    def add_chunk(chunk: RetrievedChunk) -> None:
        if chunk.chunk_id in seen_chunk_ids:
            return
        seen_chunk_ids.add(chunk.chunk_id)
        expanded.append(chunk)

    # Keep the main reranked evidence first.
    for chunk in seed_chunks:
        add_chunk(chunk)
        if len(expanded) >= effective_max:
            return expanded

    # Then add neighbors around those seed chunks.
    for chunk in seed_chunks:
        base_index = _safe_chunk_index(chunk)
        if base_index is None:
            continue

        for offset in range(1, effective_window + 1):
            for neighbor_index in (base_index - offset, base_index + offset):
                neighbor = candidate_index.get((chunk.document_id, neighbor_index))
                if neighbor is None:
                    continue

                add_chunk(neighbor)
                if len(expanded) >= effective_max:
                    return expanded

    return expanded