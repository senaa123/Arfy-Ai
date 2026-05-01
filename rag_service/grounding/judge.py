"""
Grounding judge for Phase 1 RAG.

This module answers:
"Do we have enough evidence to answer safely from these chunks?"
"""

from __future__ import annotations

from rag_service.config import settings
from rag_service.schemas import GroundingCheck, RetrievedChunk


def judge_grounding(chunks: list[RetrievedChunk]) -> GroundingCheck:
    """
    Basic grounding decision.

    Heuristics used in Phase 1:
    - at least one chunk exists
    - best score is above a minimum threshold
    - total available context is not too tiny

    This is intentionally modest and explainable.
    """
    if not chunks:
        return GroundingCheck(
            grounded=False,
            reason="No relevant chunks were retrieved.",
            best_score=0.0,
            context_chars=0,
        )

    best_score = max(float(chunk.score) for chunk in chunks)
    context_chars = sum(len(chunk.text or "") for chunk in chunks)

    if best_score < settings.MIN_GROUNDED_SCORE:
        return GroundingCheck(
            grounded=False,
            reason="Retrieved chunks were too weakly matched to the question.",
            best_score=best_score,
            context_chars=context_chars,
        )

    if context_chars < settings.MIN_CONTEXT_CHARS:
        return GroundingCheck(
            grounded=False,
            reason="Retrieved context was too small to support a grounded answer.",
            best_score=best_score,
            context_chars=context_chars,
        )

    return GroundingCheck(
        grounded=True,
        reason="Sufficient evidence was retrieved.",
        best_score=best_score,
        context_chars=context_chars,
    )