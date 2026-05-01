"""
Grounding judge for Phase 1 RAG.

This module answers:
"Do we have enough evidence to answer safely from these chunks?"
"""

from __future__ import annotations

import re

from rag_service.config import settings
from rag_service.schemas import GroundingCheck, RetrievedChunk


WORD_RE = re.compile(r"\b\w+\b", re.IGNORECASE)

_QUESTION_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "about",
    "after",
    "based",
    "can",
    "could",
    "describe",
    "document",
    "does",
    "explain",
    "file",
    "for",
    "from",
    "go",
    "goes",
    "going",
    "into",
    "mentioned",
    "pdf",
    "please",
    "say",
    "says",
    "summarize",
    "summary",
    "tell",
    "that",
    "the",
    "this",
    "those",
    "what",
    "where",
    "which",
    "who",
    "why",
    "with",
    "stuff",
}


def _meaningful_question_terms(question: str | None) -> set[str]:
    terms: set[str] = set()

    for match in WORD_RE.finditer(question or ""):
        word = match.group(0).lower()
        if len(word) < 3 or word in _QUESTION_STOPWORDS:
            continue
        terms.add(word)

    return terms


def _evidence_terms(chunks: list[RetrievedChunk]) -> set[str]:
    text = " ".join(chunk.text or "" for chunk in chunks)
    return {match.group(0).lower() for match in WORD_RE.finditer(text)}


def judge_grounding(chunks: list[RetrievedChunk], question: str | None = None) -> GroundingCheck:
    """
    Basic grounding decision.

    Heuristics used in Phase 1:
    - at least one chunk exists
    - best score is above a minimum threshold
    - total available context is not too tiny
    - when a question is supplied, at least one meaningful question term is
      visible in the selected evidence

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

    question_terms = _meaningful_question_terms(question)
    if question_terms and question_terms.isdisjoint(_evidence_terms(chunks)):
        return GroundingCheck(
            grounded=False,
            reason="Retrieved chunks were too weakly matched to the question terms.",
            best_score=best_score,
            context_chars=context_chars,
        )

    return GroundingCheck(
        grounded=True,
        reason="Sufficient evidence was retrieved.",
        best_score=best_score,
        context_chars=context_chars,
    )
