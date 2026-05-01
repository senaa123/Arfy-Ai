"""
Main answer workflow for rag_service.

Phase 2 adds a small self-healing repair loop:
1. validate input
2. retrieve candidate chunks from memory_service
3. rerank them
4. judge grounding quality
5. if weak, plan one bounded repair retry
6. retrieve again with repaired settings
7. rerank again
8. expand context with adjacent chunks from the retrieved pool
9. answer only if grounding is good enough

Important:
- exactly one retry
- no unbounded loop
- no hidden orchestration outside rag_service
"""

from __future__ import annotations

from rag_service.config import settings
from rag_service.generation import build_grounded_answer
from rag_service.grounding import judge_grounding
from rag_service.repair import plan_repair_retry
from rag_service.reranking import rerank_chunks
from rag_service.retrieval import (
    expand_context_with_neighbors,
    retrieve_candidate_chunks,
)
from rag_service.schemas import RagAskRequest, RagAskResponse


def _build_failure_response(
    *,
    used_chunks,
    grounding_reason: str,
    retrieved_count: int,
    reranked_count: int,
    used_repair: bool,
    repair_action: str | None,
    debug_pass: str,
    extra_debug: dict | None = None,
) -> RagAskResponse:
    """
    Build a stable insufficient-evidence response.

    Keeping this helper separate makes the main workflow easier to read.
    """
    debug = {
        "retrieved_count": retrieved_count,
        "reranked_count": reranked_count,
        "phase": "phase_3_citation_polish_rag",
        "pass": debug_pass,
    }
    if extra_debug:
        debug.update(extra_debug)

    return RagAskResponse(
        answer="I could not find enough grounded evidence to answer that reliably.",
        grounded=False,
        citations=[],
        used_chunks=used_chunks,
        grounding_reason=grounding_reason,
        used_repair=used_repair,
        repair_action=repair_action,
        debug=debug,
    )


def answer_question_workflow(req: RagAskRequest) -> RagAskResponse:
    """
    Run the full Phase 2 self-healing RAG flow.

    Phase 2 behavior:
    - first pass as before
    - if weak, exactly one bounded retry
    - retry may rewrite query, broaden retrieval, and expand neighbor context
    """
    question = (req.question or "").strip()
    if not question:
        raise ValueError("Question cannot be empty.")

    top_k = req.top_k or settings.DEFAULT_TOP_K
    final_k = req.final_k or settings.DEFAULT_FINAL_K

    # ----------------------------
    # Pass 1: initial retrieval
    # ----------------------------
    first_retrieved = retrieve_candidate_chunks(
        question=question,
        document_ids=req.document_ids,
        top_k=top_k,
        session_id=req.session_id,
    )

    first_reranked = rerank_chunks(
        question=question,
        chunks=first_retrieved,
        final_k=final_k,
    )

    first_grounding = judge_grounding(first_reranked)

    if first_grounding.grounded:
        answer, citations = build_grounded_answer(question, first_reranked)

        return RagAskResponse(
            answer=answer,
            grounded=True,
            citations=citations,
            used_chunks=first_reranked,
            grounding_reason=first_grounding.reason,
            used_repair=False,
            repair_action=None,
            debug={
                "retrieved_count": len(first_retrieved),
                "reranked_count": len(first_reranked),
                "best_score": first_grounding.best_score,
                "context_chars": first_grounding.context_chars,
                "citation_count": len(citations),
                "used_evidence_labels": [citation.label for citation in citations],
                "phase": "phase_3_citation_polish_rag",
                "pass": "initial",
            },
        )

    # ----------------------------
    # Pass 2: bounded repair retry
    # ----------------------------
    repair_plan = plan_repair_retry(
        question=question,
        grounding=first_grounding,
        top_k=top_k,
        final_k=final_k,
    )

    if not repair_plan.should_retry:
        return _build_failure_response(
            used_chunks=first_reranked,
            grounding_reason=first_grounding.reason,
            retrieved_count=len(first_retrieved),
            reranked_count=len(first_reranked),
            used_repair=False,
            repair_action=None,
            debug_pass="initial_failed",
            extra_debug={
                "best_score": first_grounding.best_score,
                "context_chars": first_grounding.context_chars,
            },
        )

    repaired_retrieved = retrieve_candidate_chunks(
        question=repair_plan.retry_query,
        document_ids=req.document_ids,
        top_k=repair_plan.retry_top_k,
        session_id=req.session_id,
    )

    repaired_reranked = rerank_chunks(
        question=question,
        chunks=repaired_retrieved,
        final_k=repair_plan.retry_final_k,
    )

    # Expand with adjacent chunks from the repaired candidate pool.
    expanded_evidence = expand_context_with_neighbors(
        seed_chunks=repaired_reranked,
        candidate_chunks=repaired_retrieved,
    )

    repaired_grounding = judge_grounding(expanded_evidence)

    if not repaired_grounding.grounded:
        return _build_failure_response(
            used_chunks=expanded_evidence,
            grounding_reason=repaired_grounding.reason,
            retrieved_count=len(repaired_retrieved),
            reranked_count=len(expanded_evidence),
            used_repair=True,
            repair_action=repair_plan.action,
            debug_pass="repair_failed",
            extra_debug={
                "initial_best_score": first_grounding.best_score,
                "initial_context_chars": first_grounding.context_chars,
                "repaired_best_score": repaired_grounding.best_score,
                "repaired_context_chars": repaired_grounding.context_chars,
                "repair_reason": repair_plan.reason,
                "retry_query": repair_plan.retry_query,
                "initial_retrieved_count": len(first_retrieved),
                "initial_reranked_count": len(first_reranked),
            },
        )

    answer, citations = build_grounded_answer(question, expanded_evidence)

    return RagAskResponse(
        answer=answer,
        grounded=True,
        citations=citations,
        used_chunks=expanded_evidence,
        grounding_reason=repaired_grounding.reason,
        used_repair=True,
        repair_action=repair_plan.action,
        debug={
            "retrieved_count": len(repaired_retrieved),
            "reranked_count": len(expanded_evidence),
            "best_score": repaired_grounding.best_score,
            "context_chars": repaired_grounding.context_chars,
            "citation_count": len(citations),
            "used_evidence_labels": [citation.label for citation in citations],
            "phase": "phase_3_citation_polish_rag",
            "pass": "repair_retry",
            "repair_reason": repair_plan.reason,
            "retry_query": repair_plan.retry_query,
            "initial_best_score": first_grounding.best_score,
            "initial_context_chars": first_grounding.context_chars,
            "initial_retrieved_count": len(first_retrieved),
            "initial_reranked_count": len(first_reranked),
        },
    )
