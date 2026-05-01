"""
Repair planning for Phase 2 self-healing RAG.

This module does not perform retrieval itself.
It only decides whether a retry is worth doing and how that retry should look.

Phase 2 rules:
- one retry only
- deterministic repair only
- no multi-step agent loop
- no hidden repeated model calls
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag_service.config import settings
from rag_service.schemas import GroundingCheck


@dataclass(frozen=True)
class RepairPlan:
    """
    One bounded repair plan for a single retry attempt.
    """
    should_retry: bool
    action: str | None
    retry_query: str
    retry_top_k: int
    retry_final_k: int
    reason: str


_FILLER_PATTERNS = [
    r"^\s*can you\s+",
    r"^\s*could you\s+",
    r"^\s*please\s+",
    r"^\s*tell me\s+",
]

_DOCUMENT_WRAPPERS = [
    "the document",
    "this document",
    "the pdf",
    "this pdf",
    "the file",
    "this file",
    "the notes",
    "these notes",
]

_GENERIC_SUMMARY_QUERY = "main topics summary"


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _strip_leading_fillers(text: str) -> str:
    """
    Remove conversational prefixes while preserving the actual information need.

    We loop until stable so stacked phrases like "Can you please ..." get reduced
    in one deterministic pass.
    """
    current = _normalize_spaces(text)

    while True:
        updated = current
        for pattern in _FILLER_PATTERNS:
            updated = re.sub(pattern, "", updated, flags=re.IGNORECASE)
        updated = _normalize_spaces(updated)

        if updated == current:
            return current
        current = updated


def _remove_document_wrappers(text: str) -> str:
    reduced = text
    for wrapper in _DOCUMENT_WRAPPERS:
        reduced = re.sub(rf"\b{re.escape(wrapper)}\b", " ", reduced, flags=re.IGNORECASE)
    return _normalize_spaces(reduced)


def _rewrite_query_for_retrieval(question: str) -> str:
    """
    Produce a cleaner retrieval query without using another LLM call.

    This is intentionally simple and explainable:
    - strip filler phrases
    - reduce document wrappers
    - rewrite common 'what does X say about Y' patterns toward Y
    """
    q = _strip_leading_fillers(question)

    lower = q.lower()

    # Pattern: "what does the document say about pricing"
    # Also covers variants like "what the file says about deadlines".
    match = re.search(r"(?:say|says)\s+about\s+(.+)$", lower)
    if match:
        extracted = match.group(1).strip(" ?.!")
        if extracted:
            return _normalize_spaces(extracted)

    wrapper_reduced = _remove_document_wrappers(lower)

    # Pattern: "summarize this document" / "explain this pdf"
    if any(term in lower for term in ("summarize", "summary", "explain", "describe")):
        topic_only = re.sub(
            r"\b(?:summarize|summary|explain|describe)\b",
            " ",
            wrapper_reduced,
            flags=re.IGNORECASE,
        )
        topic_only = _normalize_spaces(topic_only.strip(" ?.! ,"))
        return topic_only or _GENERIC_SUMMARY_QUERY

    # Remove obvious document wrappers while keeping the meaningful content.
    cleaned = _normalize_spaces(wrapper_reduced.strip(" ?.! ,"))
    return cleaned or _normalize_spaces(question)


def plan_repair_retry(
    *,
    question: str,
    grounding: GroundingCheck,
    top_k: int,
    final_k: int,
) -> RepairPlan:
    """
    Decide whether to run one bounded retry.

    Repair decisions in Phase 2:
    - no chunks / weak match -> rewrite + broaden retrieval
    - too little context -> broaden retrieval + broaden final evidence
    """
    if not settings.ENABLE_REPAIR_RETRY:
        return RepairPlan(
            should_retry=False,
            action=None,
            retry_query=question,
            retry_top_k=top_k,
            retry_final_k=final_k,
            reason="Repair retry is disabled.",
        )

    if grounding.grounded:
        return RepairPlan(
            should_retry=False,
            action=None,
            retry_query=question,
            retry_top_k=top_k,
            retry_final_k=final_k,
            reason="Initial retrieval was already grounded.",
        )

    retry_top_k = min(
        max(top_k * settings.REPAIR_TOP_K_MULTIPLIER, top_k + 2),
        settings.REPAIR_MAX_TOP_K,
    )
    retry_final_k = min(
        final_k + settings.REPAIR_FINAL_K_EXTRA,
        settings.REPAIR_MAX_FINAL_K,
    )

    lower_reason = grounding.reason.lower()

    if "no relevant chunks" in lower_reason or "too weakly matched" in lower_reason:
        rewritten = _rewrite_query_for_retrieval(question)
        return RepairPlan(
            should_retry=True,
            action="rewrite_and_broaden",
            retry_query=rewritten,
            retry_top_k=retry_top_k,
            retry_final_k=retry_final_k,
            reason="Initial retrieval was weak, so broadening retrieval with a cleaner query.",
        )

    if "too small" in lower_reason:
        return RepairPlan(
            should_retry=True,
            action="broaden_and_expand",
            retry_query=question,
            retry_top_k=retry_top_k,
            retry_final_k=retry_final_k,
            reason="Initial context was too small, so broadening retrieval and context.",
        )

    # Conservative default repair.
    return RepairPlan(
        should_retry=True,
        action="broad_retry",
        retry_query=_rewrite_query_for_retrieval(question),
        retry_top_k=retry_top_k,
        retry_final_k=retry_final_k,
        reason="Initial retrieval was not grounded enough for a confident answer.",
    )
