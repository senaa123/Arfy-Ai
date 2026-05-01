"""
Lightweight reranking for retrieved chunks.

Phase 1 goal:
- improve ordering cheaply
- avoid introducing another heavy model too early

Current heuristic:
final_score = semantic score + keyword overlap boost
"""

from __future__ import annotations

import re

from rag_service.schemas import RetrievedChunk


WORD_RE = re.compile(r"\b\w+\b", re.IGNORECASE)


def _tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in WORD_RE.finditer(text or "")}


def _keyword_overlap_ratio(question: str, chunk_text: str) -> float:
    """
    Very small lexical signal to complement semantic retrieval.

    This is intentionally simple for Phase 1.
    """
    q_tokens = _tokenize(question)
    c_tokens = _tokenize(chunk_text)

    if not q_tokens or not c_tokens:
        return 0.0

    overlap = q_tokens.intersection(c_tokens)
    return len(overlap) / max(1, len(q_tokens))


def rerank_chunks(question: str, chunks: list[RetrievedChunk], final_k: int) -> list[RetrievedChunk]:
    """
    Rerank retrieved chunks using:
    - original semantic score from memory_service
    - keyword overlap boost

    Returns the top final_k chunks.
    """
    rescored: list[tuple[float, RetrievedChunk]] = []

    for chunk in chunks:
        lexical = _keyword_overlap_ratio(question, chunk.text)
        combined_score = (0.75 * float(chunk.score)) + (0.25 * lexical)
        chunk.score = combined_score
        rescored.append((combined_score, chunk))

    rescored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in rescored[:final_k]]