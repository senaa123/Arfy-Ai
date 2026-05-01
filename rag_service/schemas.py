"""
Shared request/response models for rag_service.

These schemas keep the route layer thin and make the workflow output stable.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RagAskRequest(BaseModel):
    """
    Input request for grounded RAG answering.

    document_ids is optional:
    - if provided, retrieval can be limited to specific documents
    - if omitted, retrieval can search all indexed document chunks
    """
    question: str
    document_ids: list[str] = Field(default_factory=list)
    top_k: int | None = None
    final_k: int | None = None
    session_id: str | None = None


class RetrievedChunk(BaseModel):
    """
    Normalized chunk structure returned from retrieval/reranking.

    This shape is intentionally explicit so downstream code does not depend on
    memory_service's raw JSON details everywhere.
    """
    chunk_id: str
    document_id: str
    text: str
    score: float = 0.0
    source_ref: str | None = None
    file_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagCitation(BaseModel):
    """
    Citation/evidence reference returned to agent_service.

    Phase 3 note:
    - label is the evidence id used inside the answer prompt, e.g. E1, E2
    - snippet is a short preview useful for UI/debug
    - chunk_index helps future evidence rendering without changing the response shape later
    """
    label: str
    document_id: str
    chunk_id: str
    file_name: str | None = None
    source_ref: str | None = None
    pages: list[int] = Field(default_factory=list)
    snippet: str | None = None
    chunk_index: int | None = None
    

class GroundingCheck(BaseModel):
    """
    Output of the grounding judge.

    grounded = whether the evidence is strong enough to answer from
    """
    grounded: bool
    reason: str
    best_score: float = 0.0
    context_chars: int = 0


class RagAskResponse(BaseModel):
    """
    Final response returned by rag_service.
    """
    answer: str
    grounded: bool
    citations: list[RagCitation] = Field(default_factory=list)
    used_chunks: list[RetrievedChunk] = Field(default_factory=list)
    grounding_reason: str = ""
    used_repair: bool = False
    repair_action: str | None = None
    debug: dict[str, Any] = Field(default_factory=dict)
    